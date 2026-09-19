import json
import pathlib
import shutil
import subprocess
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


@unittest.skipUnless(shutil.which("git"), "本机未安装 git，跳过 run_commit 测试")
class TestRunCommit(unittest.TestCase):
    """run_commit 依据真实的 git 暂存区（index）决定校验范围，此处不做 mock，
    直接跑真实 git —— 这正是 REG001 是否在正确时机触发的关键。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True, capture_output=True)
        (self.root / "skills").mkdir()
        (self.root / "rules").mkdir()
        (self.root / "CLAUDE.md").write_text("# 路由表\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _stage(self, *rels):
        subprocess.run(
            ["git", "-C", str(self.root), "add", *rels],
            check=True, capture_output=True,
        )

    def test_staged_new_skill_triggers_reg001(self):
        # 新建未注册的 skill 且已 git add → 暂存集合触达 skills/，check_repo 应当运行
        skill_dir = self.root / "skills" / "demo"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: demo\ndescription: d\n---\n", encoding="utf-8")
        self._stage("skills/demo/SKILL.md")
        vs = runner.run_commit(self.root)
        self.assertIn("REG001", codes(vs))

    def test_unstaged_skill_does_not_trigger_reg001(self):
        # 未注册的 skill 存在于工作区，但没有被 git add；只暂存了一个无关的 rules/ 改动
        skill_dir = self.root / "skills" / "demo"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: demo\ndescription: d\n---\n", encoding="utf-8")
        (self.root / "rules" / "r.md").write_text("❌ 反例\n✅ 正例\n", encoding="utf-8")
        self._stage("rules/r.md")
        vs = runner.run_commit(self.root)
        self.assertNotIn("REG001", codes(vs))

    def test_staged_content_violation_reported(self):
        (self.root / "rules" / "r.md").write_text("✅ 只有正例\n", encoding="utf-8")
        self._stage("rules/r.md")
        vs = runner.run_commit(self.root)
        self.assertIn("STR003", codes(vs))

    def test_empty_staged_set_returns_empty(self):
        vs = runner.run_commit(self.root)
        self.assertEqual(codes(vs), [])

    def test_staged_path_missing_on_disk_does_not_raise(self):
        target = self.root / "rules" / "r.md"
        target.write_text("❌ 反例\n✅ 正例\n", encoding="utf-8")
        self._stage("rules/r.md")
        target.unlink()  # 暂存区里仍记录该文件，但工作区文件已被删掉
        vs = runner.run_commit(self.root)  # 不应抛异常
        self.assertEqual(codes(vs), [])


class TestRunAudit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        (self.root / "rules").mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_violating_file_reported_clean_file_not(self):
        (self.root / "rules" / "clean.md").write_text("❌ 反例\n✅ 正例\n", encoding="utf-8")
        (self.root / "rules" / "bad.md").write_text("✅ 只有正例\n", encoding="utf-8")
        vs = runner.run_audit(self.root)
        bad_codes = [v.code for v in vs if v.path == "rules/bad.md"]
        clean_codes = [v.code for v in vs if v.path == "rules/clean.md"]
        self.assertIn("STR003", bad_codes)
        self.assertEqual(clean_codes, [])

    def test_none_root_returns_empty(self):
        self.assertEqual(runner.run_audit(None), [])


if __name__ == "__main__":
    unittest.main()
