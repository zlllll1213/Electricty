from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ProviderPreset:
    key: str
    display_name: str
    endpoint: str
    default_model: str
    doc_url: str
    note: str


LLM_PROVIDER_PRESETS: tuple[ProviderPreset, ...] = (
    ProviderPreset(
        key="OpenAI",
        display_name="OpenAI",
        endpoint="https://api.openai.com/v1/chat/completions",
        default_model="gpt-5.2",
        doc_url="https://platform.openai.com/docs/api-reference/chat/create-chat-completion",
        note="官方 Chat Completions 端点，适合直接接入 OpenAI。",
    ),
    ProviderPreset(
        key="Google Gemini",
        display_name="Google Gemini",
        endpoint="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        default_model="gemini-3-flash-preview",
        doc_url="https://ai.google.dev/gemini-api/docs/openai",
        note="Google 提供 OpenAI 兼容模式，适合直接复用当前客户端。",
    ),
    ProviderPreset(
        key="DeepSeek",
        display_name="DeepSeek",
        endpoint="https://api.deepseek.com/chat/completions",
        default_model="deepseek-chat",
        doc_url="https://api-docs.deepseek.com/",
        note="DeepSeek 官方兼容 OpenAI 格式，支持直接调用聊天接口。",
    ),
    ProviderPreset(
        key="智谱 AI",
        display_name="智谱 AI",
        endpoint="https://open.bigmodel.cn/api/paas/v4/chat/completions",
        default_model="glm-5.1",
        doc_url="https://docs.bigmodel.cn/cn/guide/develop/openai/introduction",
        note="智谱官方提供 OpenAI 兼容接口，适合 GLM 系列模型。",
    ),
    ProviderPreset(
        key="通义千问",
        display_name="通义千问",
        endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        default_model="qwen-plus",
        doc_url="https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope",
        note="默认使用阿里云百炼北京地域兼容端点。",
    ),
)


LLM_PROVIDER_PRESET_MAP = {preset.key: preset for preset in LLM_PROVIDER_PRESETS}


@dataclass(frozen=True)
class AppConfig:
    date_col: str = "date"
    target_col: str = "consumption_billion_kwh"
    optional_cols: tuple[str, ...] = ("source", "source_url", "note")
    default_forecast_periods: int = 12
    min_forecast_periods: int = 6
    max_forecast_periods: int = 12
    min_train_points: int = 18
    season_length: int = 12
    official_data_path: Path = BASE_DIR / "data" / "official" / "national_electricity_consumption_monthly_nea.csv"
    report_output_dir: Path = BASE_DIR / "outputs" / "reports"


APP_CONFIG = AppConfig()
