from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests


class LLMClientError(RuntimeError):
    """Raised when the cloud LLM request fails."""


@dataclass(frozen=True)
class LLMConfig:
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    provider: str = "OpenAI-Compatible"
    timeout_seconds: int = 45


class LLMClient:
    """Cloud LLM client with an OpenAI-compatible API interface."""

    def __init__(self, enabled: bool = False, config: LLMConfig | None = None) -> None:
        self.enabled = enabled
        self.last_report_error: str | None = None
        self.last_answer_error: str | None = None
        self.last_report_used_cloud = False
        self.last_answer_used_cloud = False
        self.config = config or LLMConfig(
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", ""),
            model=os.getenv("LLM_MODEL", ""),
            provider=os.getenv("LLM_PROVIDER", "OpenAI-Compatible"),
        )

    @property
    def is_ready(self) -> bool:
        return bool(self.enabled and self.is_configured)

    @property
    def is_configured(self) -> bool:
        return bool(
            self.config.api_key.strip()
            and self.config.base_url.strip()
            and self.config.model.strip()
        )

    def masked_api_key(self) -> str:
        key = self.config.api_key.strip()
        if len(key) <= 6:
            return "*" * len(key)
        return f"{key[:3]}***{key[-3:]}"

    def polish_report(self, draft_report: str, context: dict[str, Any] | None = None) -> str:
        self.last_report_error = None
        self.last_report_used_cloud = False

        if not self.is_ready:
            return draft_report

        user_prompt = (
            "请你作为电力行业数据分析助手，在不改变事实和数值的前提下，"
            "将下面这份自动生成的分析报告润色为更自然、正式、适合课程实验展示的中文报告。"
            "输出纯文本，不要额外编造结论。\n\n"
            f"上下文：{context or {}}\n\n"
            f"草稿报告：\n{draft_report}"
        )

        try:
            result = self._chat(
                system_prompt="你是一名严谨的电力行业数据分析助手，擅长根据预测结果撰写中文分析报告。",
                user_prompt=user_prompt,
                temperature=0.3,
            )
            self.last_report_used_cloud = True
            return result
        except LLMClientError as exc:
            self.last_report_error = str(exc)
            return draft_report

    def answer_question(
        self,
        question: str,
        rule_based_answer: str,
        history_context: str,
        forecast_context: str,
    ) -> str:
        self.last_answer_error = None
        self.last_answer_used_cloud = False

        if not self.is_ready:
            return rule_based_answer

        user_prompt = (
            "请根据给定的历史数据摘要、未来预测结果和已有规则答案，"
            "回答用户关于全国全社会用电量趋势的问题。"
            "要求：1）中文回答；2）优先保留已有规则答案中的核心数值；"
            "3）如果上下文不足，不要编造。\n\n"
            f"用户问题：{question}\n\n"
            f"历史数据摘要：\n{history_context}\n\n"
            f"预测结果摘要：\n{forecast_context}\n\n"
            f"规则答案：\n{rule_based_answer}"
        )

        try:
            result = self._chat(
                system_prompt="你是一名严谨的电力行业问答助手，只能基于提供的上下文回答问题。",
                user_prompt=user_prompt,
                temperature=0.2,
            )
            self.last_answer_used_cloud = True
            return result
        except LLMClientError as exc:
            self.last_answer_error = str(exc)
            return rule_based_answer

    def test_connection(self) -> tuple[bool, str]:
        if not self.is_configured:
            return False, "请先填写完整的 API Endpoint、Model Name 和 API Key。"

        try:
            reply = self._chat(
                system_prompt="你是一个 API 连接测试助手。",
                user_prompt="请只返回“连接成功”四个字。",
                temperature=0.0,
            )
        except LLMClientError as exc:
            return False, str(exc)

        compact_reply = " ".join(reply.split())
        if compact_reply:
            return True, f"连接成功，模型已返回内容：{compact_reply[:80]}"
        return True, "连接成功，接口已返回响应。"

    def _chat(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        data = self._request_chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
        )

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMClientError("云端模型返回格式无法识别。") from exc

    def _request_chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
    ) -> dict[str, Any]:
        endpoint = self._build_chat_endpoint(self.config.base_url)
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.config.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise LLMClientError("云端模型调用超时，请检查网络、Endpoint 或服务状态。") from exc
        except requests.RequestException as exc:
            raise LLMClientError(f"云端模型调用失败：{exc}") from exc

        try:
            response_body = response.json()
        except ValueError as exc:
            body_preview = response.text.strip()[:300]
            raise LLMClientError(
                f"云端模型返回了非 JSON 响应，HTTP {response.status_code}，内容片段：{body_preview or '空响应'}"
            ) from exc

        if not response.ok:
            message = _extract_error_message(response_body)
            raise LLMClientError(
                f"云端模型调用失败，HTTP {response.status_code}：{message}"
            )

        return response_body

    @staticmethod
    def _build_chat_endpoint(base_url: str) -> str:
        normalized = base_url.strip().rstrip("/")
        if normalized.endswith("/chat/completions"):
            return normalized
        append_chat_suffixes = (
            "/v1",
            "/v4",
            "/openai",
            "/compatible-mode/v1",
            "/v1beta/openai",
            "/api/paas/v4",
        )
        if normalized.endswith(append_chat_suffixes):
            return f"{normalized}/chat/completions"
        if normalized == "https://api.openai.com":
            return f"{normalized}/v1/chat/completions"
        if normalized == "https://api.deepseek.com":
            return f"{normalized}/chat/completions"
        return f"{normalized}/v1/chat/completions"


def _extract_error_message(response_body: Any) -> str:
    if isinstance(response_body, dict):
        error = response_body.get("error")
        if isinstance(error, dict):
            message = error.get("message") or error.get("code")
            if message:
                return str(message)
        message = response_body.get("message")
        if message:
            return str(message)
    return "未返回明确错误信息，请检查 API Key、模型名称和接口地址。"
