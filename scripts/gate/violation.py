"""Violation 契约 —— gate 包内唯一跨模块数据结构。"""
from __future__ import annotations

import enum
from dataclasses import dataclass


class Severity(enum.IntEnum):
    WARN = 1
    ASK = 2
    BLOCK = 3


@dataclass(frozen=True)
class Violation:
    code: str
    severity: Severity
    path: str
    line: "int | None"
    message: str
    fix: str

    def render(self) -> str:
        loc = f"{self.path}:{self.line}" if self.line else self.path
        return f"[{self.code}] {loc} — {self.message}\n  修法：{self.fix}"
