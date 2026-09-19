"""自愈运行时层单测 —— 用假 page 对象，不需要浏览器。

运行：python3 -m unittest discover -s tests/unit -t .
"""
import json
import os
import tempfile
import unittest

from core.healing import runtime as heal_runtime
from core.healing.runtime import FingerprintStore, attempt, capture_fingerprint, snapshot
from core.healing.engine import Intent, intent_from_source

SRC = '''class LoginPage(BasePage):
    LOGIN_BUTTON = "#login-btn"    # P0: 登录按钮
    USER_INPUT = "#user"           # 用户名输入框
    BARE = "#bare"
'''


class FakeLocator:
    def __init__(self, n, visible=True):
        self._n, self._v = n, visible
        self.first = self

    def count(self):
        return self._n

    def is_visible(self):
        return self._v


class FakePage:
    """按选择器返回预设命中数，用来驱动唯一性判定。"""

    def __init__(self, elements=None, hits=None, url="http://t/"):
        self.elements = elements or []
        self.hits = hits or {}
        self.url = url

    def evaluate(self, js, arg=None):
        if "querySelectorAll" in js:
            return self.elements
        return self.hits.get(arg or "", None)

    def locator(self, sel):
        return FakeLocator(self.hits.get(sel, 0) if isinstance(self.hits.get(sel), int) else 0)


def el(tag="button", **kw):
    base = {"tag": tag, "attrs": {}, "role": None, "name": None, "text": "", "classes": []}
    attrs = kw.pop("attrs", {})
    base.update(kw)
    base["attrs"] = attrs
    return base


class TestIntentFromSource(unittest.TestCase):
    def test_extracts_constant_and_strips_priority_prefix(self):
        i = intent_from_source(SRC, "#login-btn", "LoginPage")
        self.assertEqual(i.constant, "LOGIN_BUTTON")
        self.assertEqual(i.description, "登录按钮")     # P0: 前缀已剥离
        self.assertEqual(i.page_object, "LoginPage")

    def test_comment_without_priority_prefix(self):
        self.assertEqual(intent_from_source(SRC, "#user").description, "用户名输入框")

    def test_constant_without_comment(self):
        i = intent_from_source(SRC, "#bare")
        self.assertEqual(i.constant, "BARE")
        self.assertEqual(i.description, "")

    def test_unknown_selector_degrades_gracefully(self):
        i = intent_from_source(SRC, "#nope")
        self.assertEqual(i.constant, "<unknown>")
        self.assertFalse(i.has_fingerprint())

    def test_fingerprint_is_merged_in(self):
        i = intent_from_source(SRC, "#login-btn", "LoginPage",
                               {"tag": "button", "role": "button", "name": "登录"})
        self.assertTrue(i.has_fingerprint())
        self.assertEqual(i.role, "button")


class TestFingerprintStore(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "nested", "fp.json")
            s = FingerprintStore(p)
            s.put("LoginPage.#a", {"tag": "button", "role": "button", "name": "登录"})
            self.assertEqual(FingerprintStore(p).get("LoginPage.#a")["name"], "登录")

    def test_corrupt_file_does_not_raise(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("{not json")
            path = f.name
        self.assertIsNone(FingerprintStore(path).get("x"))
        os.unlink(path)

    def test_none_fingerprint_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "fp.json")
            s = FingerprintStore(p)
            s.put("k", None)
            self.assertIsNone(s.get("k"))

    def test_unwritable_path_never_raises(self):
        s = FingerprintStore("/proc/nope/x/fp.json")
        s.put("k", {"tag": "a"})     # 不抛异常即通过


class TestCaptureAndSnapshot(unittest.TestCase):
    def test_snapshot_returns_list(self):
        self.assertEqual(snapshot(FakePage(elements=[el()])), [el()])

    def test_snapshot_swallows_errors(self):
        class Boom:
            def evaluate(self, *a, **k):
                raise RuntimeError("no page")
        self.assertEqual(snapshot(Boom()), [])

    def test_capture_fingerprint_swallows_errors(self):
        class Boom:
            def evaluate(self, *a, **k):
                raise RuntimeError("detached")
        self.assertIsNone(capture_fingerprint(Boom(), "#x"))


class TestAttempt(unittest.TestCase):
    def setUp(self):
        heal_runtime.HEALED.clear()
        self.intent = Intent(constant="LOGIN_BUTTON", selector="#old",
                             description="登录按钮", page_object="LoginPage",
                             tag="button", role="button", name="登录")

    def test_picks_unique_candidate_and_records_healed(self):
        e = el(attrs={"data-testid": "login-submit"}, role="button",
               name="登录", text="登录")
        page = FakePage(elements=[e], hits={'[data-testid="login-submit"]': 1})
        with tempfile.TemporaryDirectory() as d:
            art = os.path.join(d, "p.jsonl")
            got = attempt(page, self.intent, art)
            self.assertEqual(got, '[data-testid="login-submit"]')
            with open(art, encoding="utf-8") as f:
                row = json.loads(f.read().strip())
            self.assertEqual(row["chosen"]["strategy"], "testid")
        self.assertEqual(len(heal_runtime.HEALED), 1)
        self.assertEqual(heal_runtime.HEALED[0]["new"], '[data-testid="login-submit"]')

    def test_candidate_matching_multiple_elements_is_refused(self):
        # 快照看着可用，但真实页面命中 2 个 —— 必须放弃，否则可能顶替错元素
        e = el(attrs={"data-testid": "dup"}, role="button", name="登录", text="登录")
        page = FakePage(elements=[e], hits={'[data-testid="dup"]': 2})
        self.assertIsNone(attempt(page, self.intent))
        self.assertEqual(heal_runtime.HEALED, [])

    def test_no_match_returns_none_and_still_records_proposal(self):
        page = FakePage(elements=[el(tag="a", role="link", name="登录")], hits={})
        with tempfile.TemporaryDirectory() as d:
            art = os.path.join(d, "p.jsonl")
            self.assertIsNone(attempt(page, self.intent, art))
            with open(art, encoding="utf-8") as f:
                row = json.loads(f.read().strip())
            self.assertIsNone(row["chosen"])      # 失败也留痕，便于人工排查
        self.assertEqual(heal_runtime.HEALED, [])

    def test_artifact_optional(self):
        page = FakePage(elements=[], hits={})
        self.assertIsNone(attempt(page, self.intent, ""))


if __name__ == "__main__":
    unittest.main()
