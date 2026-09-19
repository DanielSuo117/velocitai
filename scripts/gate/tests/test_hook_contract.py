import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

CLI = pathlib.Path(__file__).resolve().parents[2] / "gate_cli.py"


def run_cli(mode, payload):
    return subprocess.run(
        [sys.executable, str(CLI), "--mode", mode],
        input=json.dumps(payload), capture_output=True, text=True, timeout=30,
    )


class TestHookContract(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        (self.root / ".git").mkdir()
        (self.root / "skills" / "demo").mkdir(parents=True)
        (self.root / "rules").mkdir()

    def _payload(self, tool, path, **ti):
        ti["file_path"] = str(self.root / path)
        return {"tool_name": tool, "tool_input": ti, "cwd": str(self.root)}

    def test_clean_write_exits_zero_silently(self):
        p = self._payload("Write", "docs/architecture.md", content="# 架构\n")
        (self.root / "docs").mkdir(exist_ok=True)
        r = run_cli("write", p)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "")

    def test_block_exits_two_with_deny(self):
        target = self.root / "skills" / "demo" / "SKILL.md"
        target.write_text("---\nname: demo\ndescription: d\n---\n", encoding="utf-8")
        p = self._payload("Write", "skills/demo/SKILL.md",
                          content='---\nname: wrong\ndescription: d\n---\n')
        r = run_cli("write", p)
        self.assertEqual(r.returncode, 2)
        out = json.loads(r.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("STR002", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_new_file_exits_zero_with_ask(self):
        p = self._payload("Write", "skills/demo/SKILL.md",
                          content="---\nname: demo\ndescription: d\n---\n")
        r = run_cli("write", p)
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")
        self.assertIn("触发条件", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_garbage_stdin_fails_open(self):
        r = subprocess.run(
            [sys.executable, str(CLI), "--mode", "write"],
            input="not json at all", capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
