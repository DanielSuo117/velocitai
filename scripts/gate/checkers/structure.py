"""维度② 结构合规 —— STR001–STR006。"""
from __future__ import annotations

import re

from ..context import EXEMPT_PREFIXES, git_ignored
from ..violation import Severity, Violation

MAX_LINES_WARN = 300
MAX_LINES_BLOCK = 500

ROUTER_SKILL = "skills/SKILL.md"
INDEX_SUFFIXES = ("-index.md", "-overview.md")

_FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.S)
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _frontmatter(text):
    m = _FM_RE.match(text)
    return m.group(1) if m else None


def _fm_field(fm, key):
    prefix = key + ":"
    for line in fm.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return None


def check(rel, text, root):
    rel_s = str(rel)
    if any(rel_s.startswith(p) for p in EXEMPT_PREFIXES):
        return []

    out = []
    top = rel.parts[0]

    if top == "skills" and rel.name == "SKILL.md":
        out.extend(_check_skill_frontmatter(rel, rel_s, text))

    if top == "rules" and not rel_s.endswith(INDEX_SUFFIXES):
        if "❌" not in text or "✅" not in text:
            out.append(Violation(
                "STR003", Severity.BLOCK, rel_s, None,
                "规则文件必须同时含 ❌ 反例与 ✅ 正例",
                "为每条规则补一组 ❌ 反例 / ✅ 正例代码块",
            ))

    out.extend(_check_links(rel_s, text, root))
    out.extend(_check_size(rel_s, text))
    return out


def _check_skill_frontmatter(rel, rel_s, text):
    fm = _frontmatter(text)
    if fm is None:
        return [Violation(
            "STR001", Severity.BLOCK, rel_s, 1,
            "SKILL.md 缺少 YAML frontmatter",
            "在文件开头加 ---\\nname: <目录名>\\ndescription: <触发词>\\n---",
        )]
    name = _fm_field(fm, "name")
    if name is None or _fm_field(fm, "description") is None:
        return [Violation(
            "STR001", Severity.BLOCK, rel_s, 1,
            "frontmatter 缺少 name 或 description 字段",
            "补齐 name 与 description 两个字段",
        )]
    if rel_s == ROUTER_SKILL:
        return []
    expect = rel.parent.name
    if name != expect:
        return [Violation(
            "STR002", Severity.BLOCK, rel_s, 1,
            f"frontmatter name='{name}' 与目录名 '{expect}' 不一致",
            f"把 name 改为 {expect}",
        )]
    return []


def _check_links(rel_s, text, root):
    out = []
    base = (root / rel_s).parent
    root_s = str(root)
    for i, line in enumerate(text.splitlines(), 1):
        for m in _LINK_RE.finditer(line):
            target = m.group(1).split("#")[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = base / target
            if resolved.exists():
                continue
            if git_ignored(str(resolved), root_s):
                continue
            out.append(Violation(
                "STR004", Severity.BLOCK, rel_s, i,
                f"链接指向不存在的路径：{target}",
                "修正相对路径层级，或补上缺失的目标文件",
            ))
    return out


def _check_size(rel_s, text):
    n = len(text.splitlines())
    if n > MAX_LINES_BLOCK:
        return [Violation(
            "STR006", Severity.BLOCK, rel_s, None,
            f"文件 {n} 行，超过上限 {MAX_LINES_BLOCK}",
            "拆分为多个按主题聚焦的文件，并在索引文件中互相引用",
        )]
    if n > MAX_LINES_WARN:
        return [Violation(
            "STR005", Severity.WARN, rel_s, None,
            f"文件 {n} 行，超过建议值 {MAX_LINES_WARN}",
            "考虑拆分；单文件过长会挤占 agent 上下文",
        )]
    return []
