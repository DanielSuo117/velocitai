import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

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


if __name__ == "__main__":
    unittest.main()
