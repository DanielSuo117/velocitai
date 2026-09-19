import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from gate import context
from gate.checkers import structure
from gate.violation import Severity

P = pathlib.PurePosixPath
GOOD_FM = "---\nname: quick-debug\ndescription: 排查测试失败\n---\n\n# 正文\n"


def codes(vs):
    return sorted(v.code for v in vs)


class TestSkillFrontmatter(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())

    def test_valid_skill_passes(self):
        vs = structure.check(P("skills/quick-debug/SKILL.md"), GOOD_FM, self.root)
        self.assertEqual(codes(vs), [])

    def test_missing_frontmatter(self):
        vs = structure.check(P("skills/quick-debug/SKILL.md"), "# 只有正文\n", self.root)
        self.assertIn("STR001", codes(vs))

    def test_missing_description(self):
        text = "---\nname: quick-debug\n---\n\n# 正文\n"
        vs = structure.check(P("skills/quick-debug/SKILL.md"), text, self.root)
        self.assertIn("STR001", codes(vs))

    def test_name_mismatch(self):
        text = "---\nname: wrong-name\ndescription: x\n---\n\n# 正文\n"
        vs = structure.check(P("skills/quick-debug/SKILL.md"), text, self.root)
        self.assertIn("STR002", codes(vs))

    def test_router_skill_exempt_from_name_check(self):
        # skills/SKILL.md 的 name 是 ui-automation-harness，目录名是 skills，唯一例外
        text = "---\nname: ui-automation-harness\ndescription: 路由入口\n---\n\n# 正文\n"
        vs = structure.check(P("skills/SKILL.md"), text, self.root)
        self.assertNotIn("STR002", codes(vs))


class TestRuleExamples(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())

    def test_rule_with_both_examples_passes(self):
        vs = structure.check(P("rules/x/y.md"), "❌ 反例\n✅ 正例\n", self.root)
        self.assertNotIn("STR003", codes(vs))

    def test_rule_missing_counter_example(self):
        vs = structure.check(P("rules/x/y.md"), "✅ 正例\n", self.root)
        self.assertIn("STR003", codes(vs))

    def test_index_file_exempt(self):
        vs = structure.check(P("rules/rules-index.md"), "只有链接\n", self.root)
        self.assertNotIn("STR003", codes(vs))

    def test_overview_file_exempt(self):
        vs = structure.check(P("rules/playwright/playwright-overview.md"), "只有链接\n", self.root)
        self.assertNotIn("STR003", codes(vs))


class TestLinks(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / "docs").mkdir()
        (self.root / "docs" / "real.md").write_text("x", encoding="utf-8")
        (self.root / "skills" / "s").mkdir(parents=True)
        # 这些用例验证的是链接可达性，不是 gitignore。临时目录不是 git 仓库，
        # 真实的 git_ignored 在那里只会答「不知道」（见 TestLinkChecksFailOpen），
        # 所以这里把它钉成「git 明确回答：未被忽略」。gitignore 本身由
        # test_context.py 用真实 git 覆盖。
        patcher = mock.patch.object(structure, "git_ignored", lambda *a, **k: False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_reachable_link_passes(self):
        text = "见 [doc](../../docs/real.md)\n"
        vs = structure.check(P("skills/s/SKILL.md"), text, self.root)
        self.assertNotIn("STR004", codes(vs))

    def test_dead_link_blocks(self):
        text = "见 [doc](../../../docs/real.md)\n"
        vs = structure.check(P("skills/s/SKILL.md"), text, self.root)
        self.assertIn("STR004", codes(vs))

    def test_external_url_ignored(self):
        text = "见 [x](https://example.com/a)\n"
        vs = structure.check(P("skills/s/SKILL.md"), text, self.root)
        self.assertNotIn("STR004", codes(vs))


class TestSize(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())

    def test_warn_over_300(self):
        vs = structure.check(P("rules/x/y.md"), "❌\n✅\n" + "行\n" * 320, self.root)
        self.assertIn("STR005", codes(vs))
        self.assertNotIn("STR006", codes(vs))

    def test_block_over_500(self):
        vs = structure.check(P("rules/x/y.md"), "❌\n✅\n" + "行\n" * 520, self.root)
        self.assertIn("STR006", codes(vs))
        self.assertNotIn("STR005", codes(vs))

    def test_superpowers_exempt(self):
        vs = structure.check(P("docs/superpowers/plans/p.md"), "行\n" * 800, self.root)
        self.assertEqual(codes(vs), [])


class TestFrontmatterValueParsing(unittest.TestCase):
    """_fm_field 取的必须是**值**，不是 `name:` 后面的原始文本。

    `name: "quick-debug"` 若原样返回带引号的串，STR002 会报「name='"quick-debug"'
    与目录名 'quick-debug' 不一致，修法：把 name 改为 quick-debug」—— 一条要求把值
    改成它已经是的样子的、无法满足的指令。
    """

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())

    def _check(self, text, rel="skills/quick-debug/SKILL.md"):
        return codes(structure.check(P(rel), text, self.root))

    def test_double_quoted_name_matches_dir(self):
        self.assertEqual(self._check('---\nname: "quick-debug"\ndescription: "x"\n---\n'), [])

    def test_single_quoted_name_matches_dir(self):
        self.assertEqual(self._check("---\nname: 'quick-debug'\ndescription: 'x'\n---\n"), [])

    def test_trailing_comment_stripped(self):
        text = "---\nname: quick-debug  # 必须与目录名一致\ndescription: x\n---\n"
        self.assertEqual(self._check(text), [])

    def test_quoted_value_then_comment(self):
        text = '---\nname: "quick-debug"  # 与目录名一致\ndescription: x\n---\n'
        self.assertEqual(self._check(text), [])

    def test_leading_blank_line_is_still_frontmatter(self):
        self.assertEqual(self._check("\n---\nname: quick-debug\ndescription: x\n---\n"), [])

    def test_utf8_bom_is_still_frontmatter(self):
        self.assertEqual(
            self._check("\ufeff---\nname: quick-debug\ndescription: x\n---\n"), [])

    def test_bom_plus_blank_lines(self):
        self.assertEqual(
            self._check("\ufeff\n\n---\nname: quick-debug\ndescription: x\n---\n"), [])

    # ---- 真阳性方向：剥引号不得把真正的不一致也剥没了 ----
    def test_quoted_wrong_name_still_blocks(self):
        vs = structure.check(
            P("skills/quick-debug/SKILL.md"),
            '---\nname: "wrong-name"\ndescription: x\n---\n', self.root)
        self.assertIn("STR002", codes(vs))
        # 报出来的值是剥过引号的裸值，修法才是可执行的
        self.assertIn("name='wrong-name'", vs[0].message)

    def test_still_detects_missing_frontmatter(self):
        self.assertIn("STR001", self._check("# 只有正文，没有 frontmatter\n"))

    def test_bom_without_frontmatter_still_blocks(self):
        self.assertIn("STR001", self._check("\ufeff# 只有正文\n"))


class TestLinkChecksFailOpen(unittest.TestCase):
    """git 问不出答案时，STR004 绝不能凭空产生。

    git_ignored 的返回值被 _check_links 读成「False = 没被忽略 = 死链」。git 超时
    或 index.lock 残留时若返回 False，闸门就会对一个本来合法的链接报 BLOCK。
    """

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / "skills" / "s").mkdir(parents=True)
        context.git_ignored.cache_clear()
        self.addCleanup(context.git_ignored.cache_clear)

    def test_git_timeout_produces_no_str004(self):
        def boom(*a, **k):
            raise subprocess.TimeoutExpired(cmd="git", timeout=5)

        with mock.patch.object(context.subprocess, "run", boom):
            vs = structure.check(P("skills/s/SKILL.md"), "见 [x](./nowhere.md)\n", self.root)
        self.assertNotIn("STR004", codes(vs))

    def test_git_says_not_ignored_produces_str004(self):
        # 反方向：git 正常回答「未被忽略」(退出码 1) 时，死链仍须拦下
        with mock.patch.object(
            context.subprocess, "run",
            lambda *a, **k: subprocess.CompletedProcess(a[0] if a else [], 1, b"", b""),
        ):
            vs = structure.check(P("skills/s/SKILL.md"), "见 [x](./nowhere.md)\n", self.root)
        self.assertIn("STR004", codes(vs))


if __name__ == "__main__":
    unittest.main()
