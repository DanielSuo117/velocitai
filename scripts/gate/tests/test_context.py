import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from gate import context
from gate.violation import Severity, Violation


class TestClassify(unittest.TestCase):
    def _c(self, s):
        return context.classify(pathlib.PurePosixPath(s))

    def test_skill_md(self):
        self.assertEqual(self._c("skills/quick-debug/SKILL.md"), context.SKILL)

    def test_router_skill_is_skill(self):
        self.assertEqual(self._c("skills/SKILL.md"), context.SKILL)

    def test_rule_md(self):
        self.assertEqual(self._c("rules/playwright/locator-strategy.md"), context.RULE)

    def test_doc_md(self):
        self.assertEqual(self._c("docs/architecture.md"), context.DOC)

    def test_superpowers_is_irrelevant(self):
        # spec §6.1 豁免：spec 与 plan 是长篇流程文档，不受结构检查约束
        self.assertEqual(self._c("docs/superpowers/plans/x.md"), context.IRRELEVANT)

    def test_entry_files(self):
        self.assertEqual(self._c("CLAUDE.md"), context.ENTRY)
        self.assertEqual(self._c("AGENTS.md"), context.ENTRY)
        self.assertEqual(self._c("GEMINI.md"), context.ENTRY)

    def test_mirror_dirs(self):
        self.assertEqual(self._c("zh/skills/quick-debug/SKILL.md"), context.MIRROR)
        self.assertEqual(self._c("en/rules/rules-index.md"), context.MIRROR)

    def test_source_code_irrelevant(self):
        self.assertEqual(self._c("pages/base_page.py"), context.IRRELEVANT)
        self.assertEqual(self._c("conftest.py"), context.IRRELEVANT)

    def test_none_is_irrelevant(self):
        self.assertEqual(context.classify(None), context.IRRELEVANT)


class TestFindRepoRoot(unittest.TestCase):
    """find_repo_root 依据 .git 目录是否存在向上逐级查找仓库根。"""

    def test_finds_root_from_nested_subdir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / ".git").mkdir()
            nested = root / "a" / "b" / "c"
            nested.mkdir(parents=True)
            self.assertEqual(context.find_repo_root(nested), root.resolve())

    def test_root_itself_is_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / ".git").mkdir()
            self.assertEqual(context.find_repo_root(root), root.resolve())

    def test_no_git_anywhere_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            nested = root / "x" / "y"
            nested.mkdir(parents=True)
            # 这棵临时目录树里全程没有 .git，一路向上都找不到仓库根
            self.assertIsNone(context.find_repo_root(nested))


class TestRelativeToRoot(unittest.TestCase):
    """relative_to_root 计算相对路径，并统一转成 POSIX 风格。"""

    def test_path_inside_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            target = root / "skills" / "a" / "SKILL.md"
            target.parent.mkdir(parents=True)
            target.write_text("x", encoding="utf-8")
            rel = context.relative_to_root(target, root)
            self.assertEqual(rel, pathlib.PurePosixPath("skills/a/SKILL.md"))

    def test_path_outside_root_is_none(self):
        with tempfile.TemporaryDirectory() as tmp_root, tempfile.TemporaryDirectory() as tmp_other:
            root = pathlib.Path(tmp_root)
            outside = pathlib.Path(tmp_other) / "file.md"
            self.assertIsNone(context.relative_to_root(outside, root))


@unittest.skipUnless(shutil.which("git"), "本机未安装 git，跳过 git_ignored 测试")
class TestGitIgnored(unittest.TestCase):
    """git_ignored 实际调用 `git check-ignore -q`，此处不做 mock，直接跑真实 git。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        subprocess.run(
            ["git", "init", "-q"],
            cwd=self.root, check=True, capture_output=True,
        )
        self.root.joinpath(".gitignore").write_text("CLAUDE.local.md\n", encoding="utf-8")
        # 每个测试独立的 root 目录本身已让 lru_cache 的 key 天然不重叠，
        # 这里再显式清一次缓存，避免任何跨测试的缓存复用掩盖真实结果。
        context.git_ignored.cache_clear()

    def tearDown(self):
        self._tmp.cleanup()

    def test_ignored_path_absent_from_disk(self):
        # 真实用法：CLAUDE.local.md 被链接引用，但工作区里该文件本身并不存在
        self.assertTrue(context.git_ignored("CLAUDE.local.md", str(self.root)))

    def test_non_ignored_path(self):
        self.assertFalse(context.git_ignored("CLAUDE.md", str(self.root)))


class TestViolation(unittest.TestCase):
    def test_severity_ordering(self):
        self.assertTrue(Severity.BLOCK > Severity.ASK > Severity.WARN)

    def test_render_with_line(self):
        v = Violation("STR001", Severity.BLOCK, "skills/a/SKILL.md", 3, "缺 name", "补上 name")
        out = v.render()
        self.assertIn("STR001", out)
        self.assertIn("skills/a/SKILL.md:3", out)
        self.assertIn("补上 name", out)

    def test_render_without_line(self):
        v = Violation("STR003", Severity.BLOCK, "rules/x.md", None, "缺反例", "补反例")
        self.assertIn("rules/x.md —", v.render())


class TestGitIgnoredFailOpenDirection(unittest.TestCase):
    """git 答不出来时，git_ignored 必须返回 True。

    这是整套闸门里唯一一处 fail-open 方向会被搞反的函数。两个调用方
    （structure 的 STR004、registry 的 REG002）都把 False 读作「没被忽略 →
    这是死链 → BLOCK」。于是「git 查询失败」返回 False 等于「关掉
    CLAUDE.local.md 豁免并凭空造一条 BLOCK」，而 commit 模式的 BLOCK 会 deny
    `git commit` —— 一次 5 秒超时就能把人锁在无法提交的状态，正是 §3 / §9.4
    明令禁止的 fail-closed。

    退出码语义：0 = 确实被忽略；1 = 确实未被忽略；≥2 = git 自己出错（未知）。
    只有 1 才允许返回 False。
    """

    def setUp(self):
        context.git_ignored.cache_clear()
        self.addCleanup(context.git_ignored.cache_clear)

    def _with_run(self, fn):
        return mock.patch.object(context.subprocess, "run", fn)

    def _rc(self, code):
        return lambda *a, **k: subprocess.CompletedProcess([], code, b"", b"")

    def test_timeout_returns_true(self):
        def boom(*a, **k):
            raise subprocess.TimeoutExpired(cmd="git", timeout=5)

        with self._with_run(boom):
            self.assertTrue(context.git_ignored("a/b.md", "/nonexistent-root"))

    def test_git_missing_returns_true(self):
        def boom(*a, **k):
            raise FileNotFoundError("git")

        with self._with_run(boom):
            self.assertTrue(context.git_ignored("a/b.md", "/nonexistent-root"))

    def test_fatal_exit_code_returns_true(self):
        # 128 = not a git repository / index.lock 残留 / 仓库损坏
        with self._with_run(self._rc(128)):
            self.assertTrue(context.git_ignored("a/b.md", "/nonexistent-root"))

    def test_exit_code_zero_means_ignored(self):
        with self._with_run(self._rc(0)):
            self.assertTrue(context.git_ignored("a/b.md", "/nonexistent-root"))

    def test_exit_code_one_is_the_only_false(self):
        with self._with_run(self._rc(1)):
            self.assertFalse(context.git_ignored("a/b.md", "/nonexistent-root"))


if __name__ == "__main__":
    unittest.main()
