"""维度④ 注册闭环 + 镜像弃用守卫 —— REG001–REG003。"""
from __future__ import annotations

import pathlib
import re

from ..context import MIRROR_ROOTS, git_ignored
from ..violation import Severity, Violation

_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def check_write(rel):
    """写入时机：仅镜像弃用守卫。"""
    if rel is not None and rel.parts and rel.parts[0] in MIRROR_ROOTS:
        return [Violation(
            "REG003", Severity.BLOCK, str(rel), None,
            f"{rel.parts[0]}/ 是 i18n 合并前的历史副本，已弃用，不得新增内容",
            "改为写入仓库根的对应路径；该目录待删除",
        )]
    return []


def _registered_skills(text):
    """从 CLAUDE.md 的真实 Markdown 链接目标中提取已注册的 skill 名。

    不做全文子串匹配 —— 正文里顺带提到 ./skills/foo/ 不构成注册（否则 REG001
    会被一句无关说明满足而失效）；同时容忍 ./skills/foo 与 ./skills/foo/ 两种
    等价写法（否则合法的无尾斜杠写法会被误判为未注册）。
    """
    names = set()
    for m in _LINK_RE.finditer(text):
        target = m.group(1).split("#")[0].strip().rstrip("/")
        if target.startswith("./"):
            target = target[2:]
        parts = pathlib.PurePosixPath(target).parts
        if len(parts) >= 2 and parts[0] == "skills":
            names.add(parts[1])
    return names


def check_repo(root):
    """commit / audit 时机：全局注册闭环。"""
    claude_md = root / "CLAUDE.md"
    if not claude_md.exists():
        return []
    try:
        text = claude_md.read_text(encoding="utf-8")
    except Exception:
        return []

    registered = _registered_skills(text)
    out = []
    for skill_md in sorted(root.glob("skills/*/SKILL.md")):
        name = skill_md.parent.name
        if name not in registered:
            out.append(Violation(
                "REG001", Severity.BLOCK, f"skills/{name}/SKILL.md", None,
                f"skill '{name}' 未在 CLAUDE.md 路由表注册",
                f"在 CLAUDE.md 路由表新增一行，链接指向 ./skills/{name}/",
            ))

    root_s = str(root)
    for i, line in enumerate(text.splitlines(), 1):
        for m in _LINK_RE.finditer(line):
            target = m.group(1).split("#")[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = root / target
            if resolved.exists() or git_ignored(str(resolved), root_s):
                continue
            out.append(Violation(
                "REG002", Severity.BLOCK, "CLAUDE.md", i,
                f"路由表链接指向不存在的路径：{target}",
                "修正链接，或补上缺失的目标文件",
            ))
    return out
