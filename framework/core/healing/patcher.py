"""把自愈结果写回 PageObject 源码 —— 只改定位符常量的字符串字面量。

刻意做得很窄：只认「类顶部常量 = 字符串字面量」这一种形态，且必须同时匹配
常量名与旧值才动手。宽一点的实现（正则全文替换、AST 重写）在测试进程里跑
意味着一次跑飞的回归可以改乱整个 PageObject 层，而改动淹没在测试输出里。

注释一律原样保留。注释是下次自愈的意图来源，改掉等于自断依据。
"""
from __future__ import annotations

import os
import re
import shutil

# CONSTANT = "value"   # 可选注释
_LINE_RE = re.compile(
    r'^(?P<indent>\s*)(?P<name>[A-Z][A-Z0-9_]*)'
    r'(?P<mid>\s*=\s*)(?P<q>["\'])(?P<val>.*?)(?P=q)'
    r'(?P<tail>\s*(?:#.*)?)$'
)


def _quote(value: str) -> tuple[str, str]:
    """选一种不需要转义的引号；两种都出现时用双引号并转义。"""
    if '"' not in value:
        return '"', value
    if "'" not in value:
        return "'", value
    return '"', value.replace('"', '\\"')


def patch_source(text: str, constant: str, old: str, new: str) -> tuple[str, bool]:
    """在源码文本里改写一个常量。返回 (新文本, 是否改动)。

    常量名与旧值必须同时对上才改 —— 只对一个就动手，等于在猜。
    """
    if not constant or constant == "<unknown>" or old == new:
        return text, False
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        stripped = line.rstrip("\r\n")
        m = _LINE_RE.match(stripped)
        if not m or m.group("name") != constant or m.group("val") != old:
            continue
        q, val = _quote(new)
        ending = line[len(stripped):]
        lines[i] = (f"{m.group('indent')}{m.group('name')}{m.group('mid')}"
                    f"{q}{val}{q}{m.group('tail')}{ending}")
        return "".join(lines), True
    return text, False


def patch_file(path: str, constant: str, old: str, new: str,
               backup: bool = True) -> bool:
    """改写文件里的常量。改前留 .heal-bak 备份，任何异常都返回 False 不抛。

    备份只在第一次写回时创建：.heal-bak 的语义是「自愈动这个文件之前的样子」。
    每次都覆盖的话，同一个文件被连续愈两次后原始版本就永久丢了（实测
    #v1 → #v2 → #v3 之后备份里躺着的是 #v2），想还原只能靠 git。
    """
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        patched, changed = patch_source(text, constant, old, new)
        if not changed:
            return False
        if backup and not os.path.exists(path + ".heal-bak"):
            shutil.copy2(path, path + ".heal-bak")
        with open(path, "w", encoding="utf-8") as f:
            f.write(patched)
        return True
    except Exception:
        return False
