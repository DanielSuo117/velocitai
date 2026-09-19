"""定位拦截器单测 —— 用假 page 对象，不需要浏览器。

运行：python3 -m unittest discover -s tests/unit -t .
"""
import os
import tempfile
import unittest

from core.exceptions import ElementLocationError, HealingError, VelocitaiError
from core.healing import runtime
from core.healing.interceptor import LocatorInterceptor, is_location_failure


class FakeLoc:
    def __init__(self, n, visible=True):
        self._n, self._v = n, visible
        self.first = self

    def count(self):
        return self._n

    def is_visible(self):
        return self._v

    def evaluate(self, js):
        return {"tag": "button", "role": "button", "name": "登录",
                "text": "登录", "classes": ["btn"]}


class FakePage:
    def __init__(self, hits=None, elements=None):
        self.hits = hits or {}
        self.elements = elements or []
        self.url = "http://t/"
        self.evaluated = 0

    def locator(self, sel):
        return FakeLoc(self.hits.get(sel, 0))

    def evaluate(self, js, arg=None):
        self.evaluated += 1
        if "querySelectorAll" in js:
            return self.elements
        return {"tag": "button", "role": "button", "name": "登录"}


class OwnerPage:
    LOGIN_BTN = "#login-btn"     # P0: 登录按钮


class TestLocationFailureClassification(unittest.TestCase):
    """自愈只允许介入元素定位失败。断言失败被误判为定位失败，
    就意味着自愈会去替业务掩盖真实缺陷。"""

    def test_own_exception_is_location_failure(self):
        self.assertTrue(is_location_failure(ElementLocationError("#x", "P", "C")))

    def test_timeout_is_location_failure(self):
        TE = type("TimeoutError", (Exception,), {})
        self.assertTrue(is_location_failure(TE("waiting for locator")))

    def test_strict_mode_violation_is_location_failure(self):
        self.assertTrue(is_location_failure(Exception("Error: strict mode violation: 2 elements")))

    def test_assertion_error_is_not_location_failure(self):
        self.assertFalse(is_location_failure(AssertionError("expected 3 got 4")))

    def test_value_error_is_not_location_failure(self):
        self.assertFalse(is_location_failure(ValueError("bad env")))

    def test_handle_failure_ignores_non_location_errors(self):
        itc = LocatorInterceptor(FakePage(), OwnerPage)
        self.assertIsNone(itc.handle_failure(AssertionError("nope"), "#x"))


class TestExceptionHierarchy(unittest.TestCase):
    def test_all_inherit_framework_base(self):
        # 调用方应当能一次性捕获本框架抛出的所有异常
        self.assertTrue(issubclass(ElementLocationError, VelocitaiError))
        self.assertTrue(issubclass(HealingError, VelocitaiError))

    def test_message_names_the_location(self):
        e = ElementLocationError("#login", "LoginPage", "LOGIN_BTN")
        self.assertIn("#login", str(e))
        self.assertIn("LoginPage.LOGIN_BTN", str(e))


class TestResolve(unittest.TestCase):
    def setUp(self):
        runtime.HEALED.clear()
        runtime.PATCHED.clear()

    def test_hit_returns_selector_unchanged(self):
        page = FakePage(hits={"#login-btn": 1})
        itc = LocatorInterceptor(page, OwnerPage)
        self.assertEqual(itc.resolve("#login-btn"), "#login-btn")

    def test_unhealable_returns_original_selector(self):
        # 找不到可靠替代时必须按原样失败，绝不放宽标准硬凑一个
        page = FakePage(hits={}, elements=[])
        itc = LocatorInterceptor(page, OwnerPage)
        self.assertEqual(itc.resolve("#login-btn"), "#login-btn")
        self.assertEqual(runtime.HEALED, [])

    def test_heals_and_caches(self):
        el = {"tag": "button", "attrs": {"data-testid": "login"}, "role": "button",
              "name": "登录", "text": "登录", "classes": []}
        page = FakePage(hits={'[data-testid="login"]': 1}, elements=[el])
        with tempfile.TemporaryDirectory() as d:
            itc = LocatorInterceptor(page, OwnerPage,
                                     artifact=os.path.join(d, "p.jsonl"),
                                     fingerprints=os.path.join(d, "fp.json"))
            itc._store.put("OwnerPage.#login-btn",
                           {"tag": "button", "role": "button", "name": "登录"})
            got = itc.resolve("#login-btn")
            self.assertEqual(got, '[data-testid="login"]')
            before = page.evaluated
            self.assertEqual(itc.resolve("#login-btn"), '[data-testid="login"]')
            self.assertEqual(page.evaluated, before)   # 命中缓存，不再重复推断

    def test_locator_exception_is_not_healed(self):
        # 定位器本身报错不归自愈管，原样交还调用方
        class Boom(FakePage):
            def locator(self, sel):
                raise RuntimeError("browser closed")
        itc = LocatorInterceptor(Boom(), OwnerPage)
        self.assertEqual(itc.resolve("#x"), "#x")


class TestWriteBackDisabledByDefault(unittest.TestCase):
    def test_patch_flag_defaults_false(self):
        itc = LocatorInterceptor(FakePage(), OwnerPage)
        self.assertFalse(itc.patch)
        self.assertFalse(itc.use_llm)


if __name__ == "__main__":
    unittest.main()
