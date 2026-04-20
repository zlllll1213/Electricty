from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.config import APP_CONFIG


class DataValidationError(ValueError):
    """Raised when input data does not match the expected schema."""


def load_dataset(source: Any) -> pd.DataFrame:
    if isinstance(source, (str, Path)):
        data_frame = pd.read_csv(source)
    else:
        data_frame = pd.read_csv(source)

    validate_columns(data_frame)
    return data_frame


def validate_columns(data_frame: pd.DataFrame) -> None:
    columns = {column.strip() for column in data_frame.columns}
    required = {APP_CONFIG.date_col, APP_CONFIG.target_col}
    missing = required - columns

    if missing:
        missing_columns = ", ".join(sorted(missing))
        raise DataValidationError(f"缺少必填字段：{missing_columns}")

