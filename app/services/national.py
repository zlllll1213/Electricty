from __future__ import annotations

import io
from typing import Any

import pandas as pd

from app.schemas import (
    LLMConfigUpsertRequest,
    LLMTestRequest,
    NationalDatasetValidateRequest,
    NationalForecastRunRequest,
    NationalPolishReportRequest,
    NationalQARequest,
)
from app.state import AppRuntimeState
from src.analysis.qa_engine import RuleBasedQAEngine
from src.analysis.report_generator import generate_report
from src.config import APP_CONFIG
from src.data_loader import DataValidationError, load_dataset
from src.forecast.sarima_model import ForecastingError, SarimaForecaster
from src.llm.client import LLMClient, LLMConfig
from src.preprocess import DataProcessingError, clean_monthly_data, compute_basic_statistics


class NationalServiceError(ValueError):
    """Raised when national forecasting workflows fail."""


class NationalService:
    def __init__(self, runtime: AppRuntimeState) -> None:
        self.runtime = runtime

    def get_default_dataset_payload(self) -> dict[str, Any]:
        raw_df = load_dataset(APP_CONFIG.official_data_path)
        clean_df = clean_monthly_data(raw_df)
        return {
            "source": "default",
            "label": "国家能源局真实公开数据",
            "raw_records": self._serialize_raw_records(raw_df),
            "cleaned_records": self._serialize_history(clean_df),
            "summary": self._build_validation_summary(clean_df, raw_df),
        }

    def validate_dataset(self, payload: NationalDatasetValidateRequest) -> dict[str, Any]:
        raw_df = self._read_uploaded_csv(payload.csv_content)
        clean_df = clean_monthly_data(raw_df)
        return {
            "filename": payload.filename,
            "validation_status": "ok",
            "summary": self._build_validation_summary(clean_df, raw_df),
            "cleaned_preview": self._serialize_history(clean_df.tail(12)),
            "raw_preview": self._serialize_raw_records(raw_df.head(12)),
        }

    def run_forecast(self, payload: NationalForecastRunRequest) -> dict[str, Any]:
        raw_df, source_label = self._resolve_source(payload)
        clean_df = clean_monthly_data(raw_df)
        stats = compute_basic_statistics(clean_df)
        forecaster = SarimaForecaster(date_col=APP_CONFIG.date_col, target_col=APP_CONFIG.target_col)
        forecast_result = forecaster.fit_predict(clean_df, periods=payload.forecast_periods)
        forecast_df = forecast_result.forecast

        llm_client = self._build_llm_client(payload.llm_config)
        report_text = generate_report(
            history_df=clean_df,
            forecast_df=forecast_df,
            stats=stats,
            llm_client=None,
        )

        return {
            "dataset_source": payload.dataset_source,
            "source_label": source_label,
            "history": self._serialize_history(clean_df),
            "forecast": self._serialize_forecast(forecast_df),
            "stats": self._round_floats(stats),
            "diagnostics": self._round_floats(forecast_result.diagnostics),
            "report": {
                "draft": report_text,
                "status": "local",
                "status_message": "当前显示的是本地规则报告。",
            },
            "charts": self._build_chart_payload(clean_df, forecast_df),
            "llm": self._describe_llm_ready_state(llm_client),
            "raw_records": self._serialize_raw_records(raw_df),
        }

    def polish_report(self, payload: NationalPolishReportRequest) -> dict[str, Any]:
        llm_client = self._build_llm_client(payload.llm_config)
        polished = llm_client.polish_report(payload.draft_report, context=payload.context)

        if llm_client.last_report_used_cloud:
            status = "cloud"
            message = "本次报告已由云端大模型润色。"
        elif llm_client.last_report_error:
            status = "fallback_local"
            message = f"云端润色失败，已回退到本地规则报告：{llm_client.last_report_error}"
        else:
            status = "fallback_local"
            message = "云端模型未就绪，当前使用本地规则报告。"

        return {
            "report_text": polished,
            "status": status,
            "status_message": message,
        }

    def answer_question(self, payload: NationalQARequest) -> dict[str, Any]:
        history_df = self._history_points_to_df(payload.history)
        forecast_df = self._forecast_points_to_df(payload.forecast)
        stats = payload.stats.model_dump()

        llm_client = self._build_llm_client(payload.llm_config)
        engine = RuleBasedQAEngine()
        answer = engine.answer(
            question=payload.question,
            history_df=history_df,
            forecast_df=forecast_df,
            stats=stats,
            llm_client=llm_client,
        )

        if llm_client.last_answer_used_cloud:
            status = "cloud"
            message = "本次问答由云端大模型生成。"
        elif llm_client.last_answer_error:
            status = "fallback_local"
            message = f"云端问答失败，已回退到本地规则回答：{llm_client.last_answer_error}"
        else:
            status = "local"
            message = "当前使用的是本地规则回答。"

        return {
            "answer": answer,
            "status": status,
            "status_message": message,
        }

    def test_llm(self, payload: LLMTestRequest) -> dict[str, Any]:
        llm_client = self._build_llm_client(payload.llm_config)
        success, message = llm_client.test_connection()
        return {
            "success": success,
            "message": message,
            "provider": llm_client.config.provider,
            "model": llm_client.config.model,
        }

    def upsert_llm_config(self, payload: LLMConfigUpsertRequest) -> dict[str, Any]:
        self.runtime.llm_config = payload
        return {"config": self._serialize_llm_config(payload)}

    def get_llm_config(self) -> dict[str, Any]:
        config = self.runtime.llm_config
        if not config.base_url and not config.model and not config.api_key and not config.enabled:
            raise NationalServiceError("LLM config not found")
        return {"config": self._serialize_llm_config(config)}

    def delete_llm_config(self) -> dict[str, Any]:
        self.runtime.llm_config = self.runtime.llm_config.__class__()
        return {"deleted": True}

    def get_meta(self) -> dict[str, Any]:
        data_schema = (self.runtime.base_dir / "docs" / "data_schema.md").read_text(encoding="utf-8")
        sources_doc = (self.runtime.base_dir / "docs" / "official_data_sources.md").read_text(encoding="utf-8")
        return {
            "defaults": {
                "forecast_periods": APP_CONFIG.default_forecast_periods,
                "forecast_min": APP_CONFIG.min_forecast_periods,
                "forecast_max": APP_CONFIG.max_forecast_periods,
                "dataset_label": "国家能源局真实公开数据",
            },
            "fields": {
                "required": [APP_CONFIG.date_col, APP_CONFIG.target_col],
                "optional": list(APP_CONFIG.optional_cols),
            },
            "supported_questions": [
                "未来一年用电量趋势如何",
                "哪几个月可能出现高峰",
                "哪几个月可能出现低谷",
                "预测区间大概是多少",
                "最近一个月同比如何",
            ],
            "documents": {
                "data_schema_markdown": data_schema,
                "official_sources_markdown": sources_doc,
            },
        }

    def _resolve_source(self, payload: NationalForecastRunRequest) -> tuple[pd.DataFrame, str]:
        if payload.dataset_source == "uploaded":
            return self._read_uploaded_csv(payload.csv_content or ""), "上传 CSV"
        return load_dataset(APP_CONFIG.official_data_path), "国家能源局真实公开数据"

    def _read_uploaded_csv(self, csv_content: str) -> pd.DataFrame:
        if not csv_content.strip():
            raise NationalServiceError("上传内容为空，请提供有效的 CSV 数据。")
        return load_dataset(io.StringIO(csv_content))

    def _build_llm_client(self, payload) -> LLMClient:
        if payload is None:
            payload = self.runtime.llm_config

        config = LLMConfig(
            api_key=payload.api_key,
            base_url=payload.base_url,
            model=payload.model,
            provider=payload.provider,
        )
        return LLMClient(enabled=payload.enabled, config=config)

    def _build_validation_summary(self, clean_df: pd.DataFrame, raw_df: pd.DataFrame) -> dict[str, Any]:
        return {
            "raw_record_count": int(len(raw_df)),
            "clean_record_count": int(len(clean_df)),
            "history_start": clean_df[APP_CONFIG.date_col].min().strftime("%Y-%m"),
            "history_end": clean_df[APP_CONFIG.date_col].max().strftime("%Y-%m"),
            "imputed_count": int(clean_df["is_imputed"].sum()) if "is_imputed" in clean_df.columns else 0,
        }

    def _serialize_history(self, data_frame: pd.DataFrame) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for _, row in data_frame.iterrows():
            record = {
                "date": pd.to_datetime(row[APP_CONFIG.date_col]).strftime("%Y-%m"),
                "value": round(float(row[APP_CONFIG.target_col]), 3),
                "is_imputed": bool(row.get("is_imputed", False)),
            }
            for optional_col in APP_CONFIG.optional_cols:
                if optional_col in data_frame.columns:
                    value = row.get(optional_col)
                    record[optional_col] = None if pd.isna(value) else str(value)
            records.append(record)
        return records

    def _serialize_forecast(self, data_frame: pd.DataFrame) -> list[dict[str, Any]]:
        return [
            {
                "date": row[APP_CONFIG.date_col].strftime("%Y-%m"),
                "forecast": round(float(row["forecast"]), 3),
                "lower_bound": round(float(row["lower_bound"]), 3),
                "upper_bound": round(float(row["upper_bound"]), 3),
            }
            for _, row in data_frame.iterrows()
        ]

    def _serialize_raw_records(self, data_frame: pd.DataFrame) -> list[dict[str, Any]]:
        records = data_frame.replace({pd.NA: None}).to_dict(orient="records")
        normalized: list[dict[str, Any]] = []
        for record in records:
            cooked = {}
            for key, value in record.items():
                if isinstance(value, pd.Timestamp):
                    cooked[key] = value.strftime("%Y-%m-%d")
                elif pd.isna(value) if value is not None else False:
                    cooked[key] = None
                else:
                    cooked[key] = value
            normalized.append(cooked)
        return normalized

    def _build_chart_payload(self, history_df: pd.DataFrame, forecast_df: pd.DataFrame) -> dict[str, Any]:
        rolling_mean = history_df[APP_CONFIG.target_col].rolling(window=3, min_periods=1).mean()
        monthly_avg = (
            history_df.assign(month=history_df[APP_CONFIG.date_col].dt.month)
            .groupby("month")[APP_CONFIG.target_col]
            .mean()
            .reset_index()
        )

        return {
            "history": [
                {
                    "name": "历史用电量",
                    "chart_type": "area",
                    "color": "#0f766e",
                    "x": history_df[APP_CONFIG.date_col].dt.strftime("%Y-%m").tolist(),
                    "y": self._round_list(history_df[APP_CONFIG.target_col].tolist()),
                },
                {
                    "name": "3个月移动均值",
                    "chart_type": "line",
                    "color": "#f97316",
                    "x": history_df[APP_CONFIG.date_col].dt.strftime("%Y-%m").tolist(),
                    "y": self._round_list(rolling_mean.tolist()),
                },
            ],
            "forecast": [
                {
                    "name": "历史",
                    "chart_type": "line",
                    "color": "#1d4ed8",
                    "x": history_df[APP_CONFIG.date_col].dt.strftime("%Y-%m").tolist(),
                    "y": self._round_list(history_df[APP_CONFIG.target_col].tolist()),
                },
                {
                    "name": "预测",
                    "chart_type": "line",
                    "color": "#c2410c",
                    "x": forecast_df[APP_CONFIG.date_col].dt.strftime("%Y-%m").tolist(),
                    "y": self._round_list(forecast_df["forecast"].tolist()),
                },
                {
                    "name": "预测下界",
                    "chart_type": "line",
                    "color": "#fdba74",
                    "x": forecast_df[APP_CONFIG.date_col].dt.strftime("%Y-%m").tolist(),
                    "y": self._round_list(forecast_df["lower_bound"].tolist()),
                },
                {
                    "name": "预测上界",
                    "chart_type": "line",
                    "color": "#fb923c",
                    "x": forecast_df[APP_CONFIG.date_col].dt.strftime("%Y-%m").tolist(),
                    "y": self._round_list(forecast_df["upper_bound"].tolist()),
                },
            ],
            "seasonality": [
                {
                    "name": "月均用电量",
                    "chart_type": "bar",
                    "color": "#0f766e",
                    "x": [f"{int(month)}月" for month in monthly_avg["month"].tolist()],
                    "y": self._round_list(monthly_avg[APP_CONFIG.target_col].tolist()),
                }
            ],
        }

    def _describe_llm_ready_state(self, client: LLMClient) -> dict[str, Any]:
        return {
            "enabled": client.enabled,
            "configured": client.is_configured,
            "ready": client.is_ready,
            "provider": client.config.provider,
            "model": client.config.model,
            "masked_api_key": client.masked_api_key() if client.config.api_key else "",
        }

    def _serialize_llm_config(self, payload) -> dict[str, Any]:
        masked_api_key = ""
        if payload.api_key:
            key = payload.api_key.strip()
            masked_api_key = "*" * len(key) if len(key) <= 6 else f"{key[:3]}***{key[-3:]}"

        return {
            "provider": payload.provider,
            "base_url": payload.base_url,
            "model": payload.model,
            "enabled": payload.enabled,
            "has_api_key": bool(payload.api_key),
            "masked_api_key": masked_api_key or None,
        }

    def _history_points_to_df(self, points: list[Any]) -> pd.DataFrame:
        rows = []
        for point in points:
            rows.append(
                {
                    APP_CONFIG.date_col: pd.to_datetime(point.date),
                    APP_CONFIG.target_col: point.value,
                    "is_imputed": point.is_imputed,
                    "source": point.source,
                    "source_url": point.source_url,
                    "note": point.note,
                }
            )
        return pd.DataFrame(rows)

    def _forecast_points_to_df(self, points: list[Any]) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    APP_CONFIG.date_col: pd.to_datetime(point.date),
                    "forecast": point.forecast,
                    "lower_bound": point.lower_bound,
                    "upper_bound": point.upper_bound,
                }
                for point in points
            ]
        )

    def _round_list(self, values: list[float]) -> list[float]:
        return [round(float(value), 3) for value in values]

    def _round_floats(self, data: dict[str, Any]) -> dict[str, Any]:
        rounded: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, float):
                rounded[key] = round(value, 4)
            elif isinstance(value, list):
                rounded[key] = [round(item, 4) if isinstance(item, float) else item for item in value]
            else:
                rounded[key] = value
        return rounded
