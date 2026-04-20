from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class ForecastResult:
    history: pd.DataFrame
    forecast: pd.DataFrame
    model_name: str
    diagnostics: dict[str, Any] = field(default_factory=dict)


class BaseForecaster(ABC):
    model_name: str = "base"

    def __init__(self, date_col: str, target_col: str) -> None:
        self.date_col = date_col
        self.target_col = target_col
        self.diagnostics: dict[str, Any] = {}

    @abstractmethod
    def fit(self, data_frame: pd.DataFrame) -> None:
        """Train the forecasting model."""

    @abstractmethod
    def predict(self, periods: int) -> pd.DataFrame:
        """Return the next N months of forecast values."""

    def fit_predict(self, data_frame: pd.DataFrame, periods: int) -> ForecastResult:
        self.fit(data_frame)
        forecast_df = self.predict(periods)
        return ForecastResult(
            history=data_frame.copy(),
            forecast=forecast_df,
            model_name=self.model_name,
            diagnostics=self.diagnostics.copy(),
        )

