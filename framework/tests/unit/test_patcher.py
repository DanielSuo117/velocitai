"""源码写回单测。

写回是测试进程里唯一不可逆的副作用，判定必须严到宁可不改：
常量名与旧值只要有一个对不上就拒绝动手，否则就是在猜。
"""
import os
import tempfile
import unittest

from core.healing.patcher import patch_file, patch_source

SRC = '''class OrderPage(BasePage):
    SUBMIT_BTN = "#submit-order"   # P0: 提交订单
    CANCEL_BTN = "#cancel"         # P2: 取消
    OTHER = "#submit-order"        # 同值不同名
    NO_COMMENT = "#plain"
'''


class TestPatchSource(unittest.TestCase):
    def test_patches_matching_constant(self):
        out, ok = patch_source(SRC, "SUBMIT_BTN", "#submit-order", '[data-testid="s"]')
        self.assertTrue(ok)
        self.assertIn("""SUBMIT_BTN = '[data-testid="s"]'""", out)

    def test_preserves_comment(self):
        # 注释是下次自愈还原意图的依据，改掉等于自断依据
        out, _ = patch_source(SRC, "SUBMIT_BTN", "#submit-order", "#new")
        self.assertIn("# P0: 提交订单", out)

    def test_does_not_touch_same_value_different_name(self):
        out, _ = patch_source(SRC, "SUBMIT_BTN", "#submit-order", "#new")
        self.assertIn('OTHER = "#submit-order"', out)

    def test_leaves_other_constants_alone(self):
        out, _ = patch_source(SRC, "SUBMIT_BTN", "#submit-order", "#new")
        self.assertIn('CANCEL_BTN = "#cancel"', out)

    def test_constant_name_mismatch_refuses(self):
        self.assertFalse(patch_source(SRC, "NOPE", "#submit-order", "#x")[1])

    def test_old_value_mismatch_refuses(self):
        self.assertFalse(patch_source(SRC, "SUBMIT_BTN", "#stale", "#x")[1])

    def test_noop_when_unchanged(self):
        self.assertFalse(patch_source(SRC, "SUBMIT_BTN", "#submit-order", "#submit-order")[1])

    def test_unknown_constant_refuses(self):
        self.assertFalse(patch_source(SRC, "<unknown>", "#submit-order", "#x")[1])

    def test_switches_quote_when_value_has_double_quote(self):
        out, ok = patch_source(SRC, "CANCEL_BTN", "#cancel", 'role=button[name="取消"]')
        self.assertTrue(ok)
        self.assertIn("""CANCEL_BTN = 'role=button[name="取消"]'""", out)

    def test_handles_constant_without_comment(self):
        out, ok = patch_source(SRC, "NO_COMMENT", "#plain", "#other")
        self.assertTrue(ok)
        self.assertIn('NO_COMMENT = "#other"', out)


class TestPatchFile(unittest.TestCase):
    def test_writes_and_backs_up(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "order_page.py")
            with open(p, "w", encoding="utf-8") as f:
                f.write(SRC)
            self.assertTrue(patch_file(p, "SUBMIT_BTN", "#submit-order", "#new"))
            with open(p, encoding="utf-8") as f:
                self.assertIn('SUBMIT_BTN = "#new"', f.read())
            with open(p + ".heal-bak", encoding="utf-8") as f:
                self.assertIn('SUBMIT_BTN = "#submit-order"', f.read())

    def test_backup_keeps_the_pristine_original(self):
        """连续写回时备份不得被覆盖。

        实测：#v1 → #v2 → #v3 之后 .heal-bak 里躺着的是 #v2，最初那份永久丢了。
        .heal-bak 的语义是「自愈动这个文件之前的样子」，只该在第一次写回时建。
        """
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "order_page.py")
            with open(p, "w", encoding="utf-8") as f:
                f.write(SRC)
            self.assertTrue(patch_file(p, "SUBMIT_BTN", "#submit-order", "#v2"))
            self.assertTrue(patch_file(p, "SUBMIT_BTN", "#v2", "#v3"))
            with open(p, encoding="utf-8") as f:
                self.assertIn('SUBMIT_BTN = "#v3"', f.read())
            with open(p + ".heal-bak", encoding="utf-8") as f:
                self.assertIn('SUBMIT_BTN = "#submit-order"', f.read(),
                              "备份被第二次写回覆盖，原始定位符已不可还原")

    def test_missing_file_never_raises(self):
        self.assertFalse(patch_file("/nope/x/y.py", "A", "#a", "#b"))

    def test_no_match_leaves_file_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.py")
            with open(p, "w", encoding="utf-8") as f:
                f.write(SRC)
            self.assertFalse(patch_file(p, "SUBMIT_BTN", "#stale", "#b"))
            with open(p, encoding="utf-8") as f:
                self.assertEqual(f.read(), SRC)
            self.assertFalse(os.path.exists(p + ".heal-bak"))


if __name__ == "__main__":
    unittest.main()
