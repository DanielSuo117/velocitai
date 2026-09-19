"""维度① 证据门槛与去重 —— EVI001–EVI004。"""
from __future__ import annotations

import re

from ..violation import Severity, Violation

_CLAUSE_RE = re.compile(r"^##\s+.*\bP\d")
_HEADING_RE = re.compile(r"^##\s+(.*)$")
_TRIGGER = "**触发**"
_NOISE_RE = re.compile(r"[·:：、，。()（）\[\]`*#\-—\s]|🔴|🟡|🟢|⚠️|P[\d.]+")

DUP_THRESHOLD = 0.6

PROPOSAL_CHECKLIST = (
    "在 skills/ 或 rules/ 下新建文件需先提案。请先向用户说明：\n"
    "  1. 触发条件 —— 什么情况下会再次遇到\n"
    "  2. 失败现象 —— 这次实际踩了什么坑\n"
    "  3. 拟写入位置 —— 为什么是新建文件而非并入已有文件\n"
    "  4. 检索结果 —— 与哪条既有规则相关，为何不能合并"
)


def check(rel, text, root, is_new: bool = False):
    rel_s = str(rel)
    top = rel.parts[0]
    out = []

    if is_new and top in ("skills", "rules"):
        out.append(Violation(
            "EVI001", Severity.ASK, rel_s, None,
            "在 skills/ 或 rules/ 下新建文件，需用户确认",
            PROPOSAL_CHECKLIST,
        ))

    if top != "rules":
        return out

    lines = text.splitlines()
    clause_idx = [i for i, l in enumerate(lines) if _CLAUSE_RE.match(l)]

    if clause_idx and _TRIGGER not in text:
        out.append(Violation(
            "EVI002", Severity.BLOCK, rel_s, clause_idx[0] + 1,
            "含 P 级条款但全文没有 **触发**： 行 —— 没有触发条件的规则等于没有证据",
            "为规则补 **触发**：<什么情况下适用>；文件级触发行亦可覆盖全文",
        ))

    for pos, start in enumerate(clause_idx):
        end = clause_idx[pos + 1] if pos + 1 < len(clause_idx) else len(lines)
        if not any(l.startswith(_TRIGGER) for l in lines[start:end]):
            title = lines[start].lstrip("# ").strip()
            out.append(Violation(
                "EVI003", Severity.WARN, rel_s, start + 1,
                f"条款「{title}」内部没有 **触发**： 行",
                "补条款级 **触发**：行；若已有文件级触发行覆盖，可忽略",
            ))

    out.extend(_dup_headings(rel_s, lines, root))
    return out


def _bigrams(title: str):
    """中文无空格分词，用字符二元组做相似度，避免整句比对失效。"""
    s = _NOISE_RE.sub("", title)
    if len(s) < 2:
        return {s} if s else set()
    return {s[i:i + 2] for i in range(len(s) - 1)}


def _dup_headings(rel_s, lines, root):
    existing = []
    try:
        candidates = sorted(root.glob("rules/**/*.md"))
    except Exception:
        return []
    for p in candidates:
        try:
            rel_other = p.relative_to(root).as_posix()
        except ValueError:
            continue
        if rel_other == rel_s:
            continue
        try:
            body = p.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, l in enumerate(body.splitlines(), 1):
            m = _HEADING_RE.match(l)
            if m:
                existing.append((_bigrams(m.group(1)), f"{rel_other}:{i}", m.group(1)))

    out = []
    for i, l in enumerate(lines, 1):
        m = _HEADING_RE.match(l)
        if not m:
            continue
        a = _bigrams(m.group(1))
        if not a:
            continue
        for b, loc, raw in existing:
            if not b:
                continue
            j = len(a & b) / len(a | b)
            if j >= DUP_THRESHOLD:
                out.append(Violation(
                    "EVI004", Severity.WARN, rel_s, i,
                    f"标题与 {loc}「{raw}」重叠 {j:.0%}，疑似重复",
                    "先检索既有规则；重复内容应合并进原文件，而非新增条款",
                ))
                break
    return out
