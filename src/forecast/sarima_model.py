from __future__ import annotations

import warnings

import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

from src.config import APP_CONFIG
from src.forecast.base import BaseForecaster


class ForecastingError(RuntimeError):
    """Raised when model fitting or prediction fails."""


class SarimaForecaster(BaseForecaster):
    model_name = "SARIMA"

    def __init__(self, date_col: str, target_col: str) -> None:
        super().__init__(date_col=date_col, target_col=target_col)
        self._fitted_model = None
        self._result = None
        self._history_index: pd.DatetimeIndex | None = None

    def fit(self, data_frame: pd.DataFrame) -> None:
        series = (
            data_frame.set_index(self.date_col)[self.target_col]
            .astype(float)
            .asfreq("MS")
        )
        self._history_index = series.index

        candidate_orders = self._build_candidate_orders(len(series))
        fit_error: Exception | None = None

        for order, seasonal_order in candidate_orders:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    model = SARIMAX(
                        series,
                        order=order,
                        seasonal_order=seasonal_order,
                        enforce_stationarity=False,
                        enforce_invertibility=False,
                    )
                    result = model.fit(disp=False)

                self._fitted_model = model
                self._result = result
                self.diagnostics = {
                    "order": order,
                    "seasonal_order": seasonal_order,
                    "aic": float(result.aic),
                }
                return
            except Exception as exc:
                fit_error = exc

        raise ForecastingError(f"SARIMA 模型拟合失败：{fit_error}")

    def predict(self, periods: int) -> pd.DataFrame:
        if self._result is None or self._history_index is None:
            raise ForecastingError("模型尚未训练，无法预测。")

        try:
            prediction = self._result.get_forecast(steps=periods)
            conf_int = prediction.conf_int(alpha=0.2)
        except Exception as exc:
            raise ForecastingError(f"生成预测结果失败：{exc}") from exc

        future_index = pd.date_range(
            self._history_index[-1] + pd.offsets.MonthBegin(1),
            periods=periods,
            freq="MS",
        )

        forecast_df = pd.DataFrame(
            {
                self.date_col: future_index,
                "forecast": prediction.predicted_mean.to_numpy(),
                "lower_bound": conf_int.iloc[:, 0].to_numpy(),
                "upper_bound": conf_int.iloc[:, 1].to_numpy(),
            }
        )
        # Some short or highly regular series can yield NaN confidence intervals.
        # Fall back to the point forecast so downstream APIs always receive numeric bounds.
        forecast_df["lower_bound"] = forecast_df["lower_bound"].fillna(forecast_df["forecast"])
        forecast_df["upper_bound"] = forecast_df["upper_bound"].fillna(forecast_df["forecast"])
        forecast_df["forecast"] = forecast_df["forecast"].clip(lower=0.0)
        forecast_df["lower_bound"] = forecast_df["lower_bound"].clip(lower=0.0)
        forecast_df["upper_bound"] = forecast_df["upper_bound"].clip(lower=0.0)
        return forecast_df

    def _build_candidate_orders(self, sample_size: int) -> list[tuple[tuple[int, int, int], tuple[int, int, int, int]]]:
        if sample_size >= 36:
            return [
                ((1, 1, 1), (1, 1, 1, APP_CONFIG.season_length)),
                ((1, 1, 0), (0, 1, 1, APP_CONFIG.season_length)),
                ((2, 1, 1), (1, 1, 0, APP_CONFIG.season_length)),
                ((1, 1, 1), (0, 1, 1, APP_CONFIG.season_length)),
                ((1, 1, 0), (0, 0, 0, 0)),
            ]
        return [
            ((1, 1, 1), (0, 1, 1, APP_CONFIG.season_length)),
            ((1, 1, 0), (0, 1, 1, APP_CONFIG.season_length)),
            ((1, 1, 0), (0, 0, 0, 0)),
        ]
