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
    # replace_all 必须如实模拟：一次 replace_all 把某个 rules 文件里的 ❌ 全删掉，
    # 若只替换第一处，重建出来的全文仍留着其余 ❌，STR003 不触发 —— 主执行路径上
    # 的静默假阴性。
    expected = cur.replace(old, new) if ti.get("replace_all") else cur.replace(old, new, 1)
    return _content_checks(rel, expected, root, is_new=False)


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


def _staged_text(root, name):
    """读暂存区（index）里的内容，而不是工作区。

    要提交进去的是 index 中的 blob。读工作区会两头都错：暂存了坏版本、随后在工作区
    改好 → 坏 blob 被放行；暂存了好版本、工作区正写到一半 → 凭空 BLOCK。
    任何失败（文件已从 index 删除 / 非 UTF-8 / git 不可用）都返回 None 跳过该文件，
    绝不抛出 —— fail-open。
    """
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "show", f":{name}"],
            capture_output=True, timeout=10,
        )
    except Exception:
        return None
    if r.returncode != 0:
        return None
    try:
        return r.stdout.decode("utf-8")
    except Exception:
        return None


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
        text = _staged_text(root, n)
        if text is None:
            continue
        try:
            out.extend(_content_checks(rel, text, root))
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
