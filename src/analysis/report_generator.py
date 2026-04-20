from __future__ import annotations

from typing import Any

import pandas as pd

from src.config import APP_CONFIG
from src.llm.client import LLMClient


def generate_report(
    history_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    stats: dict[str, Any],
    llm_client: LLMClient | None = None,
) -> str:
    recent_history = history_df.tail(12)[APP_CONFIG.target_col].mean()
    future_average = forecast_df["forecast"].mean()
    forecast_growth_pct = ((future_average - recent_history) / recent_history * 100) if recent_history else 0.0

    top_forecast = forecast_df.nlargest(3, "forecast")
    low_forecast = forecast_df.nsmallest(3, "forecast")

    trend_judgement = "整体稳中有升" if forecast_growth_pct >= 0 else "短期存在回落压力"
    last_yoy = _format_percentage(stats.get("last_yoy_pct"))
    last_mom = _format_percentage(stats.get("last_mom_pct"))
    recent_avg_growth = _format_percentage(stats.get("recent_avg_growth_pct"))

    report = f"""
一、数据概览
- 历史样本区间：{stats["history_start"]} 至 {stats["history_end"]}
- 最新月份用电量：{stats["latest_value"]:.1f} 亿千瓦时
- 历史月均用电量：{stats["average_value"]:.1f} 亿千瓦时
- 历史峰值月份：{stats["max_month"]}（{stats["max_value"]:.1f} 亿千瓦时）
- 历史低谷月份：{stats["min_month"]}（{stats["min_value"]:.1f} 亿千瓦时）

二、历史趋势判断
- 最新月份环比：{last_mom}
- 最新月份同比：{last_yoy}
- 最近 12 个月相对前一阶段均值变化：{recent_avg_growth}
- 从历史月度分布看，季节性高峰主要集中在：{_join_months(stats["seasonal_peak_months"])}

三、未来预测结论
- 预测期内月均用电量预计为 {future_average:.1f} 亿千瓦时，较最近一年均值变化 {forecast_growth_pct:.2f}%
- 综合判断未来 {len(forecast_df)} 个月用电量趋势：{trend_judgement}
- 预测高峰月份可能出现在：{_format_forecast_months(top_forecast)}
- 预测低谷月份可能出现在：{_format_forecast_months(low_forecast)}

四、实验说明
- 当前报告先由本地规则分析器生成，适合课程实验中的结果展示与方法说明
- 如果已配置云端大模型接口，系统会在本地规则草稿的基础上做润色，但不会修改原始统计口径
    """.strip()

    if llm_client and llm_client.is_ready:
        return llm_client.polish_report(
            draft_report=report,
            context={
                "latest_value": stats["latest_value"],
                "forecast_average": future_average,
                "forecast_periods": len(forecast_df),
            },
        )

    return report


def _join_months(months: list[int]) -> str:
    return "、".join(f"{month}月" for month in months)


def _format_percentage(value: float | None) -> str:
    if value is None:
        return "样本不足"
    return f"{value:.2f}%"


def _format_forecast_months(data_frame: pd.DataFrame) -> str:
    parts = []
    for _, row in data_frame.iterrows():
        date_label = row[APP_CONFIG.date_col].strftime("%Y-%m")
        parts.append(f"{date_label}（{row['forecast']:.1f}）")
    return "、".join(parts)
