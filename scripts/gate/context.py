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
    """目标路径是否被 .gitignore 忽略。「查不出来」一律返回 True（fail-open）。

    两处调用方（structure 的 STR004、registry 的 REG002）都把 False 读成「没被
    忽略 → 这是死链 → BLOCK」。所以本函数的 fail-open 方向是 **True** 而非
    False：git 超时、index.lock 残留、退出码 128 这类「问不出答案」的情形若返回
    False，闸门就会凭空造出一条 BLOCK 去 deny `git commit` —— 违背 §3 / §9.4
    「宁可漏判也绝不阻塞」的铁律。

    退出码语义（git check-ignore）：
      0  → 确实被忽略        → True
      1  → 确实未被忽略      → False（唯一返回 False 的分支）
      ≥2 → git 自身出错      → 未知 → True
    """
    try:
        r = subprocess.run(
            ["git", "-C", root_str, "check-ignore", "-q", path_str],
            capture_output=True, timeout=5,
        )
    except Exception:
        return True
    return r.returncode != 1
