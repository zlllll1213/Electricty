from __future__ import annotations

from typing import Any

import pandas as pd

from src.config import APP_CONFIG
from src.llm.client import LLMClient


class RuleBasedQAEngine:
    """A lightweight QA engine for fixed demo questions."""

    def answer(
        self,
        question: str,
        history_df: pd.DataFrame,
        forecast_df: pd.DataFrame,
        stats: dict[str, Any],
        llm_client: LLMClient | None = None,
    ) -> str:
        normalized = question.strip()
        if not normalized:
            return "请输入一个具体问题，例如“未来一年用电量趋势如何”。"

        rule_answer = self._build_rule_answer(normalized, history_df, forecast_df, stats)

        if llm_client and llm_client.is_ready:
            history_context = history_df.tail(12).to_csv(index=False)
            forecast_context = forecast_df.to_csv(index=False)
            return llm_client.answer_question(
                question=normalized,
                rule_based_answer=rule_answer,
                history_context=history_context,
                forecast_context=forecast_context,
            )

        return rule_answer

    def _build_rule_answer(
        self,
        normalized: str,
        history_df: pd.DataFrame,
        forecast_df: pd.DataFrame,
        stats: dict[str, Any],
    ) -> str:
        if not normalized:
            return "请输入一个具体问题，例如“未来一年用电量趋势如何”。"

        if "趋势" in normalized or "未来一年" in normalized:
            recent_history = history_df.tail(12)[APP_CONFIG.target_col].mean()
            future_average = forecast_df["forecast"].mean()
            growth_pct = ((future_average - recent_history) / recent_history * 100) if recent_history else 0.0
            direction = "稳步上行" if growth_pct >= 0 else "小幅回落"
            return (
                f"根据当前 SARIMA 预测，未来 {len(forecast_df)} 个月月均用电量约为 "
                f"{future_average:.1f} 亿千瓦时，相比最近一年变化 {growth_pct:.2f}%，整体趋势偏{direction}。"
            )

        if "高峰" in normalized or "峰值" in normalized or "最高" in normalized:
            top_months = forecast_df.nlargest(3, "forecast")
            parts = [
                f"{row[APP_CONFIG.date_col].strftime('%Y-%m')}（{row['forecast']:.1f} 亿千瓦时）"
                for _, row in top_months.iterrows()
            ]
            return "预测高峰月份大概率出现在：" + "、".join(parts) + "。"

        if "低谷" in normalized or "最低" in normalized:
            low_months = forecast_df.nsmallest(3, "forecast")
            parts = [
                f"{row[APP_CONFIG.date_col].strftime('%Y-%m')}（{row['forecast']:.1f} 亿千瓦时）"
                for _, row in low_months.iterrows()
            ]
            return "预测低谷月份大概率出现在：" + "、".join(parts) + "。"

        if "区间" in normalized or "范围" in normalized:
            min_value = forecast_df["forecast"].min()
            max_value = forecast_df["forecast"].max()
            return (
                f"未来 {len(forecast_df)} 个月预测值大致分布在 {min_value:.1f} 到 "
                f"{max_value:.1f} 亿千瓦时之间。"
            )

        if "同比" in normalized:
            yoy = stats.get("last_yoy_pct")
            if yoy is None:
                return "当前历史样本不足 13 个月，暂时无法给出最近月份同比判断。"
            return f"最近一个月相对去年同期的同比变化约为 {yoy:.2f}%。"

        return (
            "当前支持的问题包括：未来趋势、高峰月份、低谷月份、预测区间、同比变化。"
            " 例如可以输入“未来一年用电量趋势如何”或“哪几个月可能出现高峰”。"
        )
