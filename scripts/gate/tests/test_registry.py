import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

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


if __name__ == "__main__":
    unittest.main()
