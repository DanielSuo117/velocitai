import pathlib
import sys
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

    def test_mirror_dirs(self):
        self.assertEqual(self._c("zh/skills/quick-debug/SKILL.md"), context.MIRROR)
        self.assertEqual(self._c("en/rules/rules-index.md"), context.MIRROR)

    def test_source_code_irrelevant(self):
        self.assertEqual(self._c("pages/base_page.py"), context.IRRELEVANT)
        self.assertEqual(self._c("conftest.py"), context.IRRELEVANT)

    def test_none_is_irrelevant(self):
        self.assertEqual(context.classify(None), context.IRRELEVANT)


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
