from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.schemas import LLMConfigPayload


@dataclass
class AppRuntimeState:
    base_dir: Path
    llm_config: LLMConfigPayload = field(default_factory=LLMConfigPayload)


app_state = AppRuntimeState(base_dir=Path(__file__).resolve().parent.parent)
