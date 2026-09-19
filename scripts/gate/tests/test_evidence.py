import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from gate.checkers import evidence
from gate.violation import Severity

P = pathlib.PurePosixPath


def codes(vs):
    return sorted(v.code for v in vs)


class TestNewFileAsk(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())

    def test_new_skill_asks(self):
        vs = evidence.check(P("skills/new/SKILL.md"), "正文", self.root, is_new=True)
        self.assertIn("EVI001", codes(vs))
        ask = [v for v in vs if v.code == "EVI001"][0]
        self.assertEqual(ask.severity, Severity.ASK)

    def test_new_rule_asks(self):
        vs = evidence.check(P("rules/x/new.md"), "❌\n✅\n", self.root, is_new=True)
        self.assertIn("EVI001", codes(vs))

    def test_existing_file_does_not_ask(self):
        vs = evidence.check(P("rules/x/new.md"), "❌\n✅\n", self.root, is_new=False)
        self.assertNotIn("EVI001", codes(vs))

    def test_new_doc_does_not_ask(self):
        # docs/ 是项目事实清单，追加事实不需确认
        vs = evidence.check(P("docs/pages-catalog.md"), "正文", self.root, is_new=True)
        self.assertNotIn("EVI001", codes(vs))


class TestTriggerEvidence(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / "rules").mkdir()

    def test_clause_without_any_trigger_blocks(self):
        text = "## 🔴 P0.1 · 某规则\n\n规则内容\n"
        vs = evidence.check(P("rules/x.md"), text, self.root)
        self.assertIn("EVI002", codes(vs))

    def test_file_level_trigger_satisfies_block(self):
        # skill-authoring.md 的真实形态：文件级触发行覆盖三个条款
        text = "**触发**：新建 / 修改 skills/**\n\n## P0.5 · A\n\n## P0.6 · B\n"
        vs = evidence.check(P("rules/x.md"), text, self.root)
        self.assertNotIn("EVI002", codes(vs))

    def test_clause_level_missing_trigger_warns(self):
        text = "**触发**：文件级\n\n## P0.5 · A\n\n内容\n"
        vs = evidence.check(P("rules/x.md"), text, self.root)
        warns = [v for v in vs if v.code == "EVI003"]
        self.assertEqual(len(warns), 1)
        self.assertEqual(warns[0].severity, Severity.WARN)

    def test_clause_with_own_trigger_no_warn(self):
        text = "## 🔴 P0.1 · A\n\n**触发**：某情况\n\n内容\n"
        vs = evidence.check(P("rules/x.md"), text, self.root)
        self.assertNotIn("EVI003", codes(vs))

    def test_non_clause_file_not_checked(self):
        text = "## 普通小节\n\n内容\n"
        vs = evidence.check(P("rules/x.md"), text, self.root)
        self.assertNotIn("EVI002", codes(vs))


class TestDuplicateHeading(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / "rules").mkdir()
        (self.root / "rules" / "existing.md").write_text(
            "## 状态类 selector 必须配 text 锁定\n", encoding="utf-8"
        )

    def test_near_duplicate_warns(self):
        text = "## 状态类 selector 必须配 text 锁定\n"
        vs = evidence.check(P("rules/new.md"), text, self.root)
        self.assertIn("EVI004", codes(vs))

    def test_distinct_heading_passes(self):
        text = "## 浏览器 context 复用策略\n"
        vs = evidence.check(P("rules/new.md"), text, self.root)
        self.assertNotIn("EVI004", codes(vs))

    def test_self_not_compared(self):
        text = "## 状态类 selector 必须配 text 锁定\n"
        vs = evidence.check(P("rules/existing.md"), text, self.root)
        self.assertNotIn("EVI004", codes(vs))


if __name__ == "__main__":
    unittest.main()
