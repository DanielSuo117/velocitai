"""LLM 推理后端单测 —— 不发真实网络请求。

重点是失败路径：没有 key、网络挂了、模型返回垃圾，这些都必须静默退回
纯规则模式。推理层坏掉不该让任何用例失败。
"""
import unittest

from core.healing import llm
from core.healing.engine import Intent

INTENT = Intent(constant="SUBMIT_BTN", selector="#old", description="提交订单",
                page_object="OrderPage", tag="button", role="button", name="提交订单")
ELS = [{"tag": "button", "attrs": {"data-testid": "order-submit"},
        "role": "button", "name": "确认下单", "text": "确认下单",
        "classes": ["btn", "css-1a2b3c"]}]


class TestPrompt(unittest.TestCase):
    def test_carries_intent_and_elements(self):
        p = llm.build_prompt(INTENT, ELS, ["#tried"])
        for needle in ("#old", "SUBMIT_BTN", "提交订单", "OrderPage",
                       "order-submit", "#tried"):
            self.assertIn(needle, p)

    def test_instructs_model_to_refuse_when_unsure(self):
        # 宁可交白卷也不要勉强给一个像的 —— 顶替错元素比失败更糟
        self.assertIn('{"candidates": []}', llm.build_prompt(INTENT, ELS, []))

    def test_warns_against_hash_class_names(self):
        self.assertIn("css-1a2b3c", llm.build_prompt(INTENT, ELS, []))

    def test_truncates_element_list(self):
        many = ELS * (llm.MAX_ELEMENTS + 20)
        self.assertEqual(len(llm._compact(many)), llm.MAX_ELEMENTS)


class TestParseResponse(unittest.TestCase):
    def _payload(self, text):
        return {"content": [{"type": "text", "text": text}]}

    def test_extracts_candidates_in_order(self):
        out = llm.parse_response(self._payload(
            '{"candidates":[{"selector":"#a"},{"selector":"#b"}]}'))
        self.assertEqual(out, ["#a", "#b"])

    def test_tolerates_prose_around_json(self):
        out = llm.parse_response(self._payload(
            '我认为是这个：{"candidates":[{"selector":"#a"}]} 供参考'))
        self.assertEqual(out, ["#a"])

    def test_empty_candidates_is_respected(self):
        self.assertEqual(llm.parse_response(self._payload('{"candidates":[]}')), [])

    def test_caps_at_three(self):
        many = ",".join('{"selector":"#%d"}' % i for i in range(9))
        self.assertEqual(len(llm.parse_response(self._payload(
            '{"candidates":[%s]}' % many))), 3)

    def test_garbage_returns_empty(self):
        for bad in ("我不知道", "", "{broken", '{"other":1}'):
            self.assertEqual(llm.parse_response(self._payload(bad)), [])

    def test_malformed_payload_returns_empty(self):
        for bad in ({}, {"content": "x"}, {"content": [{"type": "tool_use"}]}):
            self.assertEqual(llm.parse_response(bad), [])


class TestNoKeyFailsSoft(unittest.TestCase):
    def setUp(self):
        self._orig = llm.api_key
        llm.api_key = lambda: ""

    def tearDown(self):
        llm.api_key = self._orig

    def test_unavailable_without_key(self):
        self.assertFalse(llm.available())

    def test_infer_returns_empty_without_key(self):
        # 没有 key 时静默退回纯规则模式，绝不抛异常
        self.assertEqual(llm.infer(INTENT, ELS), [])

    def test_infer_returns_empty_without_elements(self):
        self.assertEqual(llm.infer(INTENT, []), [])


if __name__ == "__main__":
    unittest.main()
