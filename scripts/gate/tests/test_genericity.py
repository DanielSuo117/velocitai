import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from gate.checkers import genericity

P = pathlib.PurePosixPath
SKILL = P("skills/demo/SKILL.md")


def codes(vs):
    return sorted(v.code for v in vs)


class TestScope(unittest.TestCase):
    def test_only_applies_to_skills(self):
        vs = genericity.check(P("rules/x/y.md"), "见 https://intranet.corp.example/a\n")
        self.assertEqual(codes(vs), [])


class TestUrl(unittest.TestCase):
    def test_concrete_url_blocks(self):
        vs = genericity.check(SKILL, "打开 https://portal.acme-internal.net/home\n")
        self.assertIn("GEN001", codes(vs))

    def test_example_com_whitelisted(self):
        vs = genericity.check(SKILL, "打开 https://example.com/xxx\n")
        self.assertNotIn("GEN001", codes(vs))

    def test_ellipsis_placeholder_whitelisted(self):
        # 现有 gen-page-test/SKILL.md:11 的真实写法，末尾紧跟全角括号
        vs = genericity.check(SKILL, "给定页面（https://...）生成页面对象和测试\n")
        self.assertNotIn("GEN001", codes(vs))

    def test_doc_domains_whitelisted(self):
        vs = genericity.check(SKILL, "见 https://playwright.dev/docs/locators\n")
        self.assertNotIn("GEN001", codes(vs))


class TestAbsPath(unittest.TestCase):
    def test_mac_user_path_blocks(self):
        vs = genericity.check(SKILL, "打开 /Users/alice/repo/pages/x.py\n")
        self.assertIn("GEN002", codes(vs))

    def test_relative_path_passes(self):
        vs = genericity.check(SKILL, "打开 pages/base_page.py\n")
        self.assertNotIn("GEN002", codes(vs))


class TestHashClass(unittest.TestCase):
    def test_real_assignment_blocks(self):
        vs = genericity.check(SKILL, 'LOGIN_BTN = "css=.sc-bdVaJa"\n')
        self.assertIn("GEN003", codes(vs))

    def test_bad_comment_exempt(self):
        # locator-replacer/SKILL.md:71 的真实写法
        vs = genericity.check(SKILL, '# BAD: "css=.sc-bdVaJa.bVjGWg"         (styled-components 哈希)\n')
        self.assertNotIn("GEN003", codes(vs))

    def test_table_row_exempt(self):
        # locator-replacer/SKILL.md:84 的真实写法
        vs = genericity.check(SKILL, "| Emotion | 前缀 css- | `.css-1a2b3c` |\n")
        self.assertNotIn("GEN003", codes(vs))

    def test_checklist_exempt(self):
        # locator-replacer/SKILL.md:186 的真实写法
        vs = genericity.check(SKILL, "- [ ] 没有使用哈希类名（`sc-xxx`, `css-xxx`, `_module_xxx`）\n")
        self.assertNotIn("GEN003", codes(vs))

    def test_cross_mark_line_exempt(self):
        vs = genericity.check(SKILL, '❌ 反例：LOGIN = "css=.css-1a2b3c"\n')
        self.assertNotIn("GEN003", codes(vs))


if __name__ == "__main__":
    unittest.main()
