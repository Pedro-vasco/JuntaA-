from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ItemType = Literal["image", "pdf", "docx"]


@dataclass(slots=True)
class MergeItem:
    path: Path
    item_type: ItemType
    description: str

    @property
    def display_name(self) -> str:
        return f"{self.path.name} • {self.description}"
