from __future__ import annotations

import pandas as pd
import pytest

from src.data_loader import DataValidationError, validate_columns
from src.preprocess import DataProcessingError, clean_monthly_data


def build_monthly_frame(length: int = 18) -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", periods=length, freq="MS")
    return pd.DataFrame(
        {
            "date": dates.strftime("%Y-%m"),
            "consumption_billion_kwh": [7000 + index * 10 for index in range(length)],
        }
    )


def test_validate_columns_raises_on_missing_required_field() -> None:
    frame = pd.DataFrame({"date": ["2024-01"]})
    with pytest.raises(DataValidationError):
        validate_columns(frame)


def test_clean_monthly_data_normalizes_and_imputes_missing_months() -> None:
    frame = pd.DataFrame(
        {
            "date": [
                "2023-01",
                "2023-02",
                "2023-04",
                "2023-05",
                "2023-06",
                "2023-07",
                "2023-08",
                "2023-09",
                "2023-10",
                "2023-11",
                "2023-12",
                "2024-01",
                "2024-02",
                "2024-03",
                "2024-04",
                "2024-05",
                "2024-06",
                "2024-07",
            ],
            "consumption_billion_kwh": [
                "7,000",
                "7050",
                "7150",
                "7200",
                "7250",
                "7300",
                "7350",
                "7400",
                "7450",
                "7500",
                "7550",
                "7600",
                "7650",
                "7700",
                "7750",
                "7800",
                "7850",
                "7900",
            ],
        }
    )

    cleaned = clean_monthly_data(frame)

    assert len(cleaned) == 19
    assert "is_imputed" in cleaned.columns
    assert cleaned.loc[cleaned["date"] == pd.Timestamp("2023-03-01"), "is_imputed"].iloc[0]


def test_clean_monthly_data_rejects_short_samples() -> None:
    frame = build_monthly_frame(length=5)
    with pytest.raises(DataProcessingError):
        clean_monthly_data(frame)
