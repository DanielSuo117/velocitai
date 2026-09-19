import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
