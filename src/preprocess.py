from __future__ import annotations

from typing import Any

import pandas as pd

from src.config import APP_CONFIG


class DataProcessingError(ValueError):
    """Raised when the input data cannot be cleaned into a monthly time series."""


def clean_monthly_data(data_frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = data_frame.copy()
    cleaned.columns = [column.strip() for column in cleaned.columns]

    cleaned[APP_CONFIG.date_col] = pd.to_datetime(cleaned[APP_CONFIG.date_col], errors="coerce")
    cleaned[APP_CONFIG.target_col] = pd.to_numeric(
        cleaned[APP_CONFIG.target_col].astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    )

    cleaned = cleaned.dropna(subset=[APP_CONFIG.date_col, APP_CONFIG.target_col])
    if cleaned.empty:
        raise DataProcessingError("清洗后无有效数据，请检查日期和数值格式。")

    cleaned[APP_CONFIG.date_col] = cleaned[APP_CONFIG.date_col].dt.to_period("M").dt.to_timestamp()

    aggregations: dict[str, Any] = {APP_CONFIG.target_col: "mean"}
    for optional_col in APP_CONFIG.optional_cols:
        if optional_col in cleaned.columns:
            aggregations[optional_col] = "last"

    cleaned = (
        cleaned.groupby(APP_CONFIG.date_col, as_index=False)
        .agg(aggregations)
        .sort_values(APP_CONFIG.date_col)
        .reset_index(drop=True)
    )

    cleaned = cleaned.set_index(APP_CONFIG.date_col).asfreq("MS")
    cleaned["is_imputed"] = cleaned[APP_CONFIG.target_col].isna()
    cleaned[APP_CONFIG.target_col] = cleaned[APP_CONFIG.target_col].interpolate(method="linear", limit_direction="both")

    for optional_col in APP_CONFIG.optional_cols:
        if optional_col in cleaned.columns:
            cleaned[optional_col] = cleaned[optional_col].ffill().bfill()

    cleaned = cleaned.reset_index()

    if len(cleaned) < APP_CONFIG.min_train_points:
        raise DataProcessingError(
            f"有效月度样本数不足，至少需要 {APP_CONFIG.min_train_points} 条，当前为 {len(cleaned)} 条。"
        )

    return cleaned


def compute_basic_statistics(cleaned: pd.DataFrame) -> dict[str, Any]:
    series = cleaned[APP_CONFIG.target_col]
    latest_value = float(series.iloc[-1])
    average_value = float(series.mean())
    latest_month = cleaned[APP_CONFIG.date_col].iloc[-1].strftime("%Y-%m")

    stats: dict[str, Any] = {
        "record_count": len(cleaned),
        "history_start": cleaned[APP_CONFIG.date_col].iloc[0].strftime("%Y-%m"),
        "history_end": latest_month,
        "latest_month": latest_month,
        "latest_value": latest_value,
        "average_value": average_value,
        "max_value": float(series.max()),
        "min_value": float(series.min()),
        "max_month": cleaned.loc[series.idxmax(), APP_CONFIG.date_col].strftime("%Y-%m"),
        "min_month": cleaned.loc[series.idxmin(), APP_CONFIG.date_col].strftime("%Y-%m"),
    }

    if len(cleaned) >= 2:
        prev_value = float(series.iloc[-2])
        stats["last_mom_pct"] = (latest_value - prev_value) / prev_value * 100 if prev_value else None
    else:
        stats["last_mom_pct"] = None

    if len(cleaned) >= 13:
        last_year_value = float(series.iloc[-13])
        stats["last_yoy_pct"] = (latest_value - last_year_value) / last_year_value * 100 if last_year_value else None
    else:
        stats["last_yoy_pct"] = None

    recent_12 = cleaned.tail(12)[APP_CONFIG.target_col].mean()
    previous_12_slice = cleaned.iloc[-24:-12] if len(cleaned) >= 24 else cleaned.iloc[:-12]
    if not previous_12_slice.empty:
        previous_12 = previous_12_slice[APP_CONFIG.target_col].mean()
        stats["recent_avg_growth_pct"] = (recent_12 - previous_12) / previous_12 * 100 if previous_12 else None
    else:
        stats["recent_avg_growth_pct"] = None

    monthly_avg = (
        cleaned.assign(month=cleaned[APP_CONFIG.date_col].dt.month)
        .groupby("month")[APP_CONFIG.target_col]
        .mean()
        .sort_values(ascending=False)
    )
    stats["seasonal_peak_months"] = [int(month) for month in monthly_avg.head(3).index.tolist()]
    stats["seasonal_low_months"] = [int(month) for month in monthly_avg.tail(3).index.tolist()]

    return stats

