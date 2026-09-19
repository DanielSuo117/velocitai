"""选择器自愈引擎单测 —— 纯逻辑，不需要浏览器。

运行：python3 -m unittest discover -s tests/unit -t .
（用 unittest 而非 pytest：根 conftest.py 的 --env 为 required，
  且它 import 了 gitignored 的 config/settings.py，pytest 无法裸跑。）

这些用例里最重要的一组是 TestNeverFalsePass —— 自愈唯一不可逾越的边界是
「绝不能把真失败变成假通过」。若那组变红，整个机制必须停用。
"""
import json
import os
import tempfile
import unittest

from core.healing.engine import (
    Candidate,
    HealProposal,
    Intent,
    MIN_CONFIDENCE,
    _is_hashy,
    rank,
    record,
)


def el(tag="button", *, eid=None, testid=None, role=None, name=None,
       text="", classes=None, **attrs):
    a = dict(attrs)
    if eid:
        a["id"] = eid
    if testid:
        a["data-testid"] = testid
    return {"tag": tag, "attrs": a, "role": role, "name": name,
            "text": text, "classes": classes or []}


class TestHashDetection(unittest.TestCase):
    def test_build_tool_hashes_rejected(self):
        for t in ("sc-bdVaJa", "css-1a2b3c", "Button_a1b2c3", "a3f9c21b7e44"):
            self.assertTrue(_is_hashy(t), t)

    def test_ordinary_identifiers_kept(self):
        # 误判为哈希只会少一个候选，但这类 id 恰恰是最好的锚点，不能丢
        for t in ("login-btn", "step2", "tab1", "submit", "user-name", "form_input"):
            self.assertFalse(_is_hashy(t), t)


class TestRanking(unittest.TestCase):
    def setUp(self):
        self.intent = Intent(constant="LOGIN_BUTTON", selector="#old-login",
                             description="登录按钮", page_object="LoginPage",
                             tag="button", role="button", name="登录")

    def test_testid_outranks_everything(self):
        e = el(testid="login-submit", eid="login-btn", role="button",
               name="登录", text="登录", classes=["btn", "primary"])
        best = rank(self.intent, [e])[0]
        self.assertEqual(best.strategy, "testid")
        self.assertEqual(best.selector, '[data-testid="login-submit"]')

    def test_hashy_id_not_used_as_anchor(self):
        e = el(eid="css-1a2b3c", role="button", name="登录", text="登录")
        sels = [c.selector for c in rank(self.intent, [e])]
        self.assertNotIn("#css-1a2b3c", sels)

    def test_hashy_classes_excluded_from_class_candidate(self):
        e = el(role="button", name="登录", text="登录",
               classes=["sc-bdVaJa", "btn", "css-9xk2lm"])
        cls = [c for c in rank(self.intent, [e], min_confidence=0)
               if c.strategy == "stable-class"]
        self.assertTrue(cls)
        self.assertEqual(cls[0].selector, "button.btn")

    def test_role_name_uses_playwright_role_engine(self):
        # 不能拼 CSS 属性选择器：tag[role="button"] 只匹配显式标注了 role 的元素，
        # 原生 <button> 几乎从不标注，实测真实页面命中 0 个；且那种写法丢掉了 name。
        e = el(role="button", name="登录", text="登录")
        rn = [c for c in rank(self.intent, [e]) if c.strategy == "role-name"]
        self.assertEqual(rn[0].selector, 'role=button[name="登录"]')

    def test_role_name_escapes_quotes_in_name(self):
        e = el(role="button", name='说"是"', text="x")
        intent = Intent(constant="C", selector="#c", tag="button",
                        role="button", name='说"是"')
        rn = [c for c in rank(intent, [e]) if c.strategy == "role-name"]
        self.assertEqual(rn[0].selector, 'role=button[name="说\\"是\\""]')

    def test_ordered_by_confidence_desc(self):
        e = el(testid="t", eid="login-btn", role="button", name="登录", text="登录")
        conf = [c.confidence for c in rank(self.intent, [e])]
        self.assertEqual(conf, sorted(conf, reverse=True))


class TestUniqueness(unittest.TestCase):
    """唯一命中是防假通过的第二道闸，必须在排序阶段就强制。"""

    def test_candidate_matching_two_elements_is_dropped(self):
        intent = Intent(constant="ROW", selector=".row", tag="button",
                        role="button", name="删除")
        twins = [el(role="button", name="删除", text="删除", classes=["btn"]),
                 el(role="button", name="删除", text="删除", classes=["btn"])]
        for c in rank(intent, twins, min_confidence=0):
            self.assertNotEqual(c.selector, "button.btn")

    def test_unique_testid_survives_among_twins(self):
        intent = Intent(constant="ROW", selector=".row", tag="button",
                        role="button", name="删除")
        els = [el(testid="del-1", role="button", name="删除", text="删除"),
               el(testid="del-2", role="button", name="删除", text="删除")]
        sels = [c.selector for c in rank(intent, els)]
        self.assertIn('[data-testid="del-1"]', sels)
        self.assertIn('[data-testid="del-2"]', sels)


class TestNeverFalsePass(unittest.TestCase):
    """自愈唯一不可逾越的边界：绝不能把真失败变成假通过。

    若这组用例变红，说明自愈可能顶替到无关元素让用例假绿 —— 必须停用机制。
    """

    def test_wrong_role_yields_no_candidate(self):
        intent = Intent(constant="SUBMIT", selector="#s", tag="button",
                        role="button", name="提交")
        # 页面上只剩一个链接，角色不符 —— 宁可失败也不能拿它顶替
        self.assertEqual(rank(intent, [el(tag="a", role="link", name="提交",
                                          text="提交", eid="go")]), [])

    def test_wrong_name_yields_no_candidate(self):
        intent = Intent(constant="SUBMIT", selector="#s", tag="button",
                        role="button", name="提交")
        self.assertEqual(rank(intent, [el(role="button", name="取消",
                                          text="取消", eid="cancel")]), [])

    def test_empty_page_yields_no_candidate(self):
        intent = Intent(constant="SUBMIT", selector="#s", tag="button",
                        role="button", name="提交")
        self.assertEqual(rank(intent, []), [])

    def test_without_fingerprint_weak_anchors_refused(self):
        # 无指纹时只认强锚点，且说明必须对得上，否则毫无依据认定是同一个元素
        intent = Intent(constant="SUBMIT", selector="#s", description="提交订单")
        weak = el(text="提交订单", classes=["btn"])
        self.assertEqual(rank(intent, [weak]), [])

    def test_without_fingerprint_strong_anchor_with_matching_description(self):
        intent = Intent(constant="SUBMIT", selector="#s", description="提交订单")
        strong = el(testid="order-submit", text="提交订单")
        self.assertEqual(rank(intent, [strong])[0].strategy, "testid")

    def test_without_fingerprint_mismatched_description_refused(self):
        intent = Intent(constant="SUBMIT", selector="#s", description="提交订单")
        self.assertEqual(rank(intent, [el(testid="x", text="删除账户")]), [])


class TestConfidenceFloor(unittest.TestCase):
    def test_below_floor_excluded(self):
        intent = Intent(constant="C", selector="#c", tag="span",
                        role=None, name=None)
        # 只留类名一种可能：stable-class 置信 60，低于默认下限 70。
        # 元素不能带文本，否则会额外触发置信 75 的文本策略，测不到下限。
        out = rank(intent, [el(tag="span", classes=["label"], text="")],
                   min_confidence=MIN_CONFIDENCE)
        self.assertEqual(out, [])
        # 反向：把下限降到 60 以下，同一个元素就应当产出类名候选
        self.assertEqual(rank(intent, [el(tag="span", classes=["label"], text="")],
                              min_confidence=0)[0].strategy, "stable-class")


class TestRecord(unittest.TestCase):
    def test_writes_jsonl(self):
        p = HealProposal(intent=Intent(constant="A", selector="#a"),
                         candidates=[Candidate("#b", "id", 90, "why")],
                         chosen=Candidate("#b", "id", 90, "why"),
                         url="http://x/", test_id="t::c")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "nested", "heal.jsonl")
            self.assertTrue(record(p, path))
            with open(path, encoding="utf-8") as f:
                row = json.loads(f.read().strip())
            self.assertEqual(row["intent"]["constant"], "A")
            self.assertEqual(row["chosen"]["selector"], "#b")

    def test_unwritable_path_never_raises(self):
        # 记录失败绝不能影响测试结论
        p = HealProposal(intent=Intent(constant="A", selector="#a"),
                         candidates=[], chosen=None)
        self.assertFalse(record(p, "/proc/nonexistent/x/heal.jsonl"))


if __name__ == "__main__":
    unittest.main()
