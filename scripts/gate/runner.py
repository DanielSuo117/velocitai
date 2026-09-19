"""三种运行模式的编排。"""
from __future__ import annotations

import os
import pathlib
import subprocess

from . import context
from .checkers import evidence, genericity, registry, structure


def _content_checks(rel, text, root, is_new=False):
    out = []
    out.extend(structure.check(rel, text, root))
    out.extend(genericity.check(rel, text, root))
    out.extend(evidence.check(rel, text, root, is_new=is_new))
    return out


def run_write(payload):
    tool = (payload or {}).get("tool_name")
    if tool not in ("Write", "Edit"):
        return []
    ti = payload.get("tool_input") or {}
    fp = ti.get("file_path")
    if not fp:
        return []

    root = context.find_repo_root(pathlib.Path(payload.get("cwd") or os.getcwd()))
    if root is None:
        return []
    rel = context.relative_to_root(fp, root)
    kind = context.classify(rel)

    if kind == context.MIRROR:
        return registry.check_write(rel)
    if kind not in (context.SKILL, context.RULE, context.DOC):
        return []

    disk = pathlib.Path(fp)
    if tool == "Write":
        text = ti.get("content")
        if text is None:
            return []
        return _content_checks(rel, text, root, is_new=not disk.exists())

    # Edit：hook 只给 old_string / new_string，须读盘重建全文
    if not disk.exists():
        return []
    try:
        cur = disk.read_text(encoding="utf-8")
    except Exception:
        return []
    old, new = ti.get("old_string"), ti.get("new_string")
    if old is None or new is None or old not in cur:
        return []  # fail-open：匹配不上就不猜
    return _content_checks(rel, cur.replace(old, new, 1), root, is_new=False)


def _staged(root):
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "diff", "--cached", "--name-only"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return []
    if r.returncode != 0:
        return []
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


def run_commit(root):
    if root is None:
        return []
    names = _staged(root)
    if not names:
        return []

    out = []
    for n in names:
        rel = pathlib.PurePosixPath(n)
        kind = context.classify(rel)
        if kind == context.MIRROR:
            out.extend(registry.check_write(rel))
            continue
        if kind not in (context.SKILL, context.RULE, context.DOC):
            continue
        p = root / n
        if not p.exists():
            continue
        try:
            out.extend(_content_checks(rel, p.read_text(encoding="utf-8"), root))
        except Exception:
            continue

    if any(n.startswith("skills/") or n == "CLAUDE.md" for n in names):
        out.extend(registry.check_repo(root))
    return out


def run_audit(root):
    if root is None:
        return []
    out = []
    # 三个 glob 模式分别根植于互不重叠的顶级目录（skills/rules/docs），
    # 同一文件不可能同时匹配两个模式，故此处无需去重守卫。
    for pattern in ("skills/**/*.md", "rules/**/*.md", "docs/*.md"):
        for p in sorted(root.glob(pattern)):
            rel = pathlib.PurePosixPath(p.relative_to(root).as_posix())
            if context.classify(rel) not in (context.SKILL, context.RULE, context.DOC):
                continue
            try:
                out.extend(_content_checks(rel, p.read_text(encoding="utf-8"), root))
            except Exception:
                continue
    out.extend(registry.check_repo(root))
    return out
