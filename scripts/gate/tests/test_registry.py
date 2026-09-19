import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from gate import context
from gate.checkers import registry

P = pathlib.PurePosixPath


def codes(vs):
    return sorted(v.code for v in vs)


class TestMirrorGuard(unittest.TestCase):
    def test_zh_write_blocked(self):
        self.assertIn("REG003", codes(registry.check_write(P("zh/skills/a/SKILL.md"))))

    def test_en_write_blocked(self):
        self.assertIn("REG003", codes(registry.check_write(P("en/rules/x.md"))))

    def test_root_write_allowed(self):
        self.assertEqual(codes(registry.check_write(P("skills/a/SKILL.md"))), [])


class TestRepoChecks(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / "skills" / "alpha").mkdir(parents=True)
        (self.root / "skills" / "alpha" / "SKILL.md").write_text("x", encoding="utf-8")
        (self.root / "docs").mkdir()
        (self.root / "docs" / "real.md").write_text("x", encoding="utf-8")
        # 这些用例验证路由表闭环，不验证 gitignore。临时目录不是 git 仓库，真实的
        # git_ignored 在那里只会答「不知道」（见 TestRouteChecksFailOpen），故钉成
        # 「git 明确回答：未被忽略」。
        patcher = mock.patch.object(registry, "git_ignored", lambda *a, **k: False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _write_claude(self, body):
        (self.root / "CLAUDE.md").write_text(body, encoding="utf-8")

    def test_registered_skill_passes(self):
        self._write_claude("| 建 | [alpha](./skills/alpha/) |\n")
        self.assertNotIn("REG001", codes(registry.check_repo(self.root)))

    def test_unregistered_skill_blocks(self):
        self._write_claude("# 没有路由表\n")
        self.assertIn("REG001", codes(registry.check_repo(self.root)))

    def test_dead_route_link_blocks(self):
        self._write_claude("| 建 | [alpha](./skills/alpha/) |\n| 文档 | [d](./docs/missing.md) |\n")
        self.assertIn("REG002", codes(registry.check_repo(self.root)))

    def test_live_route_link_passes(self):
        self._write_claude("| 建 | [alpha](./skills/alpha/) |\n| 文档 | [d](./docs/real.md) |\n")
        self.assertNotIn("REG002", codes(registry.check_repo(self.root)))

    def test_missing_claude_md_is_noop(self):
        self.assertEqual(codes(registry.check_repo(self.root)), [])

    def test_prose_mention_is_not_registration(self):
        # 正文顺带提及不构成注册；早期实现用全文子串匹配，被这种句子直接架空
        self._write_claude("# 说明\n历史上 ./skills/alpha/ 曾经存在，但这不是路由表条目。\n")
        self.assertIn("REG001", codes(registry.check_repo(self.root)))

    def test_link_without_trailing_slash_counts_as_registered(self):
        # ./skills/alpha 与 ./skills/alpha/ 是等价写法，都应视为已注册
        self._write_claude("| 建 | [alpha](./skills/alpha) |\n")
        self.assertNotIn("REG001", codes(registry.check_repo(self.root)))

    def test_non_skill_links_ignored(self):
        # rules/ 与 docs/ 链接不得被误当成 skill 注册
        self._write_claude("[规范](./rules/x/y.md) [文档](./docs/architecture.md)\n")
        self.assertIn("REG001", codes(registry.check_repo(self.root)))


class TestRouteChecksFailOpen(unittest.TestCase):
    """git 问不出答案时，REG002 绝不能凭空产生。

    这是 C1 最要命的下游：REG002 是 BLOCK，而 commit 模式的 BLOCK 直接 deny
    `git commit`。git 一次超时（仓库放在 iCloud Drive 上完全可能）就把
    CLAUDE.md → CLAUDE.local.md 这条设计内的可选链接判成死链，把人卡在无法提交。
    """

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / "CLAUDE.md").write_text(
            "私有备忘：[CLAUDE.local.md](./CLAUDE.local.md)\n", encoding="utf-8")
        context.git_ignored.cache_clear()
        self.addCleanup(context.git_ignored.cache_clear)

    def test_git_timeout_produces_no_reg002(self):
        def boom(*a, **k):
            raise subprocess.TimeoutExpired(cmd="git", timeout=5)

        with mock.patch.object(context.subprocess, "run", boom):
            self.assertEqual(codes(registry.check_repo(self.root)), [])

    def test_git_fatal_exit_code_produces_no_reg002(self):
        # 128 = git 自身报错（index.lock 残留、仓库损坏），不是「未被忽略」
        with mock.patch.object(
            context.subprocess, "run",
            lambda *a, **k: subprocess.CompletedProcess([], 128, b"", b"fatal"),
        ):
            self.assertEqual(codes(registry.check_repo(self.root)), [])

    def test_git_says_not_ignored_produces_reg002(self):
        # 反方向：git 正常回答「未被忽略」(退出码 1) 时，死链仍须拦下
        with mock.patch.object(
            context.subprocess, "run",
            lambda *a, **k: subprocess.CompletedProcess([], 1, b"", b""),
        ):
            self.assertIn("REG002", codes(registry.check_repo(self.root)))


if __name__ == "__main__":
    unittest.main()
