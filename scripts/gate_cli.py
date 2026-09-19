#!/usr/bin/env python3
"""VelocitAI 落库校验闸门 —— 唯一入口。

用法：
    gate_cli.py --mode write     # PreToolUse(Write|Edit)，从 stdin 读 hook JSON
    gate_cli.py --mode commit    # PreToolUse(Bash git commit)，校验暂存区
    gate_cli.py --mode audit     # 全仓库扫描，供测试与 commit 模式内部使用

退出码：0 = 放行（可能带 ask 决策）；2 = 拦截。
任何异常一律 fail-open 返回 0。
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gate import context, runner            # noqa: E402
from gate.violation import Severity         # noqa: E402


def _root():
    return context.find_repo_root(pathlib.Path(os.getcwd()))


def _emit(violations) -> int:
    if not violations:
        return 0

    out = {}

    # WARN 必须始终能被看到：无论最高档位是什么，只要出现过 WARN 就单独渲染一份
    # —— 否则一旦同批里混进 ASK/BLOCK，WARN 就会被下面按最高档位过滤的 JSON
    # 悄悄吞掉。
    #   · stderr 一份：退出码 2（BLOCK）时宿主把 stderr 回传给 agent。
    #   · stdout 的 systemMessage 一份：退出码 0 时宿主只从 **stdout** 组装要展示
    #     的 hook 消息，只写 stderr 等于没写。STR005/GEN004/EVI003/EVI004 这四个
    #     纯 WARN 码全部走退出码 0，不补这一份就是完全不可见（spec §13 遗留问题）。
    #     systemMessage 是宿主文档中「对所有 hook 展示给用户」的通用字段。
    warns = [v for v in violations if v.severity == Severity.WARN]
    if warns:
        text = "落库校验提示：\n" + "\n".join(v.render() for v in warns)
        print(text, file=sys.stderr)
        out["systemMessage"] = text

    top = max(v.severity for v in violations)
    rc = 0

    if top == Severity.BLOCK:
        body = "\n".join(v.render() for v in violations if v.severity == Severity.BLOCK)
        out["hookSpecificOutput"] = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "落库校验闸门拦截：\n" + body,
        }
        rc = 2
    elif top == Severity.ASK:
        body = "\n".join(v.render() for v in violations if v.severity == Severity.ASK)
        out["hookSpecificOutput"] = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": body,
        }

    if out:
        print(json.dumps(out, ensure_ascii=False))
    return rc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("write", "commit", "audit"), required=True)
    try:
        args = ap.parse_args()
    except SystemExit as exc:
        # argparse 用法错误抛的是 SystemExit(2)，而 PreToolUse 里的 2 意思是 deny。
        # 不接住的话，一个写错的 --mode 会拿 argparse 的 usage 文本当理由拒掉这次
        # 工具调用 —— fail-open 之外最后一处 fail-closed 缺口。
        if exc.code:
            print("[gate] 参数解析失败，已放行", file=sys.stderr)
        return 0

    if args.mode == "write":
        payload = json.load(sys.stdin)
        return _emit(runner.run_write(payload))

    if args.mode == "commit":
        return _emit(runner.run_commit(_root()))

    return _emit(runner.run_audit(_root()))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # fail-open：宁可漏判，绝不阻塞
        print(f"[gate] 校验器异常，已放行：{exc}", file=sys.stderr)
        sys.exit(0)
