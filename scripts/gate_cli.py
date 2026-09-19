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

    # WARN 必须始终能被看到：无论最高档位是什么，只要出现过 WARN 就先落到
    # stderr —— 否则一旦同批里混进 ASK/BLOCK，WARN 就会被下面按最高档位过滤
    # 的 JSON 悄悄吞掉，既不在 stdout 也不在 stderr。
    warns = [v for v in violations if v.severity == Severity.WARN]
    if warns:
        print("落库校验提示：\n" + "\n".join(v.render() for v in warns), file=sys.stderr)

    top = max(v.severity for v in violations)

    if top == Severity.BLOCK:
        body = "\n".join(v.render() for v in violations if v.severity == Severity.BLOCK)
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "落库校验闸门拦截：\n" + body,
        }}, ensure_ascii=False))
        return 2

    if top == Severity.ASK:
        body = "\n".join(v.render() for v in violations if v.severity == Severity.ASK)
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": body,
        }}, ensure_ascii=False))
        return 0

    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("write", "commit", "audit"), required=True)
    args = ap.parse_args()

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
