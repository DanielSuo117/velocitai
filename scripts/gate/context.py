"""路径归类、仓库根定位、gitignore 查询。"""
from __future__ import annotations

import functools
import pathlib
import subprocess

SKILL = "skill"
RULE = "rule"
DOC = "doc"
ENTRY = "entry"
MIRROR = "mirror"
IRRELEVANT = "irrelevant"

ENTRY_FILES = {"CLAUDE.md", "AGENTS.md", "GEMINI.md"}
MIRROR_ROOTS = ("zh", "en")
# spec §6.1 豁免：spec / plan 是长篇流程文档，不是 harness 知识
EXEMPT_PREFIXES = ("docs/superpowers/",)


def find_repo_root(start: pathlib.Path):
    start = pathlib.Path(start).resolve()
    for d in [start, *start.parents]:
        if (d / ".git").exists():
            return d
    return None


def relative_to_root(path, root):
    try:
        rel = pathlib.Path(path).resolve().relative_to(pathlib.Path(root).resolve())
    except (ValueError, OSError):
        return None
    return pathlib.PurePosixPath(rel.as_posix())


def classify(rel) -> str:
    if rel is None:
        return IRRELEVANT
    rel_s = str(rel)
    parts = rel.parts
    if not parts:
        return IRRELEVANT
    if parts[0] in MIRROR_ROOTS:
        return MIRROR
    if any(rel_s.startswith(p) for p in EXEMPT_PREFIXES):
        return IRRELEVANT
    if len(parts) == 1 and parts[0] in ENTRY_FILES:
        return ENTRY
    if rel.suffix != ".md":
        return IRRELEVANT
    if parts[0] == "skills":
        return SKILL
    if parts[0] == "rules":
        return RULE
    if parts[0] == "docs":
        return DOC
    return IRRELEVANT


@functools.lru_cache(maxsize=None)
def git_ignored(path_str: str, root_str: str) -> bool:
    """目标路径是否被 .gitignore 忽略。git 不可用时返回 False（fail-open）。"""
    try:
        r = subprocess.run(
            ["git", "-C", root_str, "check-ignore", "-q", path_str],
            capture_output=True, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False
