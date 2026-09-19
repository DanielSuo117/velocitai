import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from gate import runner


def codes(vs):
    return sorted(v.code for v in vs)


class TestRunWrite(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / ".git").mkdir()
        (self.root / "skills" / "demo").mkdir(parents=True)
        (self.root / "rules").mkdir()

    def _payload(self, tool, path, **ti):
        ti["file_path"] = str(self.root / path)
        return {"tool_name": tool, "tool_input": ti, "cwd": str(self.root)}

    def test_irrelevant_file_skipped(self):
        p = self._payload("Write", "pages/base_page.py", content="x = 1")
        self.assertEqual(codes(runner.run_write(p)), [])

    def test_non_edit_tool_skipped(self):
        p = self._payload("Bash", "skills/demo/SKILL.md", content="x")
        self.assertEqual(codes(runner.run_write(p)), [])

    def test_mirror_write_blocked(self):
        p = self._payload("Write", "zh/skills/demo/SKILL.md", content="x")
        self.assertIn("REG003", codes(runner.run_write(p)))

    def test_new_skill_triggers_ask(self):
        p = self._payload("Write", "skills/demo/SKILL.md",
                          content="---\nname: demo\ndescription: d\n---\n")
        self.assertIn("EVI001", codes(runner.run_write(p)))

    def test_existing_skill_no_ask(self):
        target = self.root / "skills" / "demo" / "SKILL.md"
        target.write_text("---\nname: demo\ndescription: d\n---\n", encoding="utf-8")
        p = self._payload("Write", "skills/demo/SKILL.md",
                          content="---\nname: demo\ndescription: d\n---\n新增一行\n")
        self.assertNotIn("EVI001", codes(runner.run_write(p)))

    def test_edit_rebuilds_full_text(self):
        target = self.root / "rules" / "r.md"
        target.write_text("❌ 反例\n✅ 正例\n旧内容\n", encoding="utf-8")
        p = self._payload("Edit", "rules/r.md", old_string="旧内容", new_string="新内容")
        # 重建后仍含 ❌ 与 ✅ → 不应报 STR003
        self.assertNotIn("STR003", codes(runner.run_write(p)))

    def test_edit_removing_examples_blocks(self):
        target = self.root / "rules" / "r.md"
        target.write_text("❌ 反例\n✅ 正例\n", encoding="utf-8")
        p = self._payload("Edit", "rules/r.md", old_string="❌ 反例\n", new_string="")
        self.assertIn("STR003", codes(runner.run_write(p)))

    def test_edit_with_unmatched_old_string_fails_open(self):
        target = self.root / "rules" / "r.md"
        target.write_text("✅ 只有正例\n", encoding="utf-8")
        p = self._payload("Edit", "rules/r.md", old_string="不存在的串", new_string="x")
        self.assertEqual(codes(runner.run_write(p)), [])

    def test_malformed_payload_fails_open(self):
        self.assertEqual(codes(runner.run_write({})), [])


if __name__ == "__main__":
    unittest.main()
