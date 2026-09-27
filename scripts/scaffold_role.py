#!/usr/bin/env python3
"""按项目约定生成一个角色的测试目录骨架。

用法：
    python scripts/scaffold_role.py <role> [--label <中文名>]

例如 ``python scripts/scaffold_role.py teacher --label 教师`` 会生成：

    framework/tests/teacher/
    ├── __init__.py
    ├── teacher_base_test.py     # TeacherBaseTest：class 级一次登录，共享 self.teacher_page
    └── test_teacher_flow.py     # TestTeacherFlow：gen-page-test 往类末尾追加用例

已存在的文件一律跳过，不覆盖。生成后请在 docs/architecture.md 的「角色与
context 共享」表里登记该角色。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TESTS_DIR = REPO_ROOT / "framework" / "tests"

_ROLE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _pascal(snake: str) -> str:
    return "".join(part.capitalize() for part in snake.split("_"))


def _templates(role: str, label: str) -> dict[str, str]:
    cls = _pascal(role)
    base_test = f'''# 文件用途：{label}角色基类 —— class 级一次登录，用例共享 self.{role}_page
from __future__ import annotations

import pytest

from core.base.base_test import BaseTest


class {cls}BaseTest(BaseTest):
    """{label}端所有用例的基类。

    class 级完成一次登录，用例通过 ``self.{role}_page`` 使用已登录页面。
    需要进入具体页面时，在子类再加一个 class-scope fixture 导航；不要在
    用例里重复登录，也不要覆盖本 fixture（见 rules/coding-conventions）。
    """

    # 登录入口。默认走 URL token 直登，按项目实际登录方式调整这一行即可。
    LOGIN_PATH = "/entry?token={{token}}"

    @pytest.fixture(scope="class", autouse=True)
    def _{role}_login(self, class_page, base_url, token, request):
        class_page.goto(base_url.rstrip("/") + self.LOGIN_PATH.format(token=token))
        request.cls.{role}_page = class_page
        yield
'''
    flow_test = f'''# 文件用途：{label}端主流程回归 —— 新用例由 gen-page-test 追加到类末尾
import allure
import pytest

from tests.{role}.{role}_base_test import {cls}BaseTest


@allure.feature("{label}端主流程")
class Test{cls}Flow({cls}BaseTest):
    """新增用例一律追加到类末尾，禁止插到已有方法之间（rules/coding-conventions）。"""

    @allure.story("登录 → 起点页面")
    @pytest.mark.smoke
    def test_{role}_login(self):
        assert not self.{role}_page.url.startswith("about:blank"), "登录后未离开空白页"
'''
    return {
        "__init__.py": "",
        f"{role}_base_test.py": base_test,
        f"test_{role}_flow.py": flow_test,
    }


def scaffold(role: str, label: str, tests_dir: Path) -> tuple[list[Path], list[Path]]:
    """生成骨架；返回 (新建的文件, 跳过的已有文件)。"""
    target = tests_dir / role
    target.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    skipped: list[Path] = []
    for name, body in _templates(role, label).items():
        path = target / name
        if path.exists():
            skipped.append(path)
            continue
        path.write_text(body, encoding="utf-8", newline="\n")
        created.append(path)
    return created, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成角色测试目录骨架")
    parser.add_argument("role", help="角色名，snake_case，例如 teacher / admin / student")
    parser.add_argument("--label", default=None, help="角色中文名，用于注释与 allure 标签；默认同 role")
    parser.add_argument(
        "--tests-dir",
        type=Path,
        default=DEFAULT_TESTS_DIR,
        help=argparse.SUPPRESS,  # 仅供自检：把骨架生成到别的目录
    )
    args = parser.parse_args(argv)

    if not _ROLE_RE.match(args.role):
        print(f"角色名必须是 snake_case 标识符：{args.role!r}", file=sys.stderr)
        return 2
    label = args.label or args.role

    created, skipped = scaffold(args.role, label, args.tests_dir)
    for p in created:
        print(f"新建  {p.relative_to(args.tests_dir.parent.parent) if args.tests_dir == DEFAULT_TESTS_DIR else p}")
    for p in skipped:
        print(f"跳过  {p}（已存在）")
    if not created:
        print("没有新建任何文件。")
        return 0

    cls = _pascal(args.role)
    print(
        "\n下一步：\n"
        f"  1. 在 docs/architecture.md 的「角色与 context 共享」表登记 {args.role}（基类 {cls}BaseTest，context scope=class）\n"
        f"  2. 按项目登录方式调整 {args.role}_base_test.py 里的 LOGIN_PATH\n"
        f"  3. pytest framework/tests/{args.role} --env=<pre|prod> -v"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
