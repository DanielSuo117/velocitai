"""测试数据读取 —— 统一从 framework/data/ 取文件，用例里不写路径。

约定：``data/<role>/<feature>.json``，例如 ``data/teacher/course.json``。
用例只写 ``load_json("teacher/course")``，换目录或换格式只改这里。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def data_path(name: str, suffix: str = ".json") -> Path:
    """把 ``teacher/course`` 解析为 ``framework/data/teacher/course.json``。"""
    p = DATA_DIR / name
    return p if p.suffix else p.with_suffix(suffix)


def load_json(name: str) -> Any:
    """读取 JSON 测试数据；文件不存在时报出完整路径，便于定位。"""
    p = data_path(name)
    if not p.is_file():
        raise FileNotFoundError(f"测试数据不存在：{p}")
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def load_text(name: str, suffix: str = ".txt") -> str:
    """读取文本类数据（如长文案、SQL）。"""
    p = data_path(name, suffix)
    if not p.is_file():
        raise FileNotFoundError(f"测试数据不存在：{p}")
    return p.read_text(encoding="utf-8")
