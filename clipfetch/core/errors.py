from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class AppError:
    title: str
    message: str
    technical_details: str = ""
    code: str = ""
