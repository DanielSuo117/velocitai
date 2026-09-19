"""LLM 自愈档（--self-heal=auto）的端到端验证 —— 真浏览器、真三道闸。

网络那一跳是桩的（拦 urllib.request.urlopen），除此之外全是真的：真的取
key、真的拼 prompt、真的解析 Messages API 响应格式、真的在真实 DOM 上跑
唯一性 / 可见性 / 意图指纹三道闸。桩掉网络是为了让断言确定，而不是为了
绕开逻辑 —— 被桩掉的只有 Anthropic 那一次 HTTP 往返本身。

夹具 v4 造的是「规则必然交白卷」的局面：两个按钮 tag / role / 可及名称
完全相同，class 全是构建哈希。规则拼得出的候选一个都不唯一，模型才有出场
的理由 —— 它能用结构上下文（main / nav）把二者分开，规则不会拼这种选择器。

运行：pytest framework/tests/e2e/test_llm_healing_e2e.py --env=pre --self-heal=on
"""
import json
import io
from pathlib import Path

import pytest

from core.base.base_page import BasePage
from core.healing import llm as heal_llm
from core.healing import runtime

FIXTURES = Path(__file__).parent / "fixtures"


def url(name: str) -> str:
    return (FIXTURES / name).as_uri()


class AmbiguousLoginPage(BasePage):
    # 注释里的「主区」是模型唯一能用来区分两个同名按钮的线索 ——
    # 这也是规则做不到的那一步。
    MAIN_LOGIN_BTN = "#main-login"      # P0: 页面主区(main)里的登录按钮，不是导航栏那个

    def is_page_loaded(self) -> bool:
        return self.get_element_count("nav") > 0


class _LoginLike(BasePage):
    """带稳定 testid 可自愈的页面 —— 用来验证规则命中时不调模型。"""

    LOGIN_BTN = "#login-btn"        # P0: 登录按钮

    def is_page_loaded(self) -> bool:
        return True


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


@pytest.fixture(autouse=True)
def heal_env(request, tmp_path, monkeypatch):
    if request.config.getoption("--self-heal") == "off":
        pytest.skip("本组用例验证自愈行为，需 --self-heal=on|strict|auto")
    monkeypatch.setattr(BasePage, "heal_fingerprints", str(tmp_path / "fp.json"))
    monkeypatch.setattr(BasePage, "heal_artifact", str(tmp_path / "proposals.jsonl"))
    # 只开模型推理，不开写回：写回会真去改 PageObject 源文件（见 P0.4）。
    monkeypatch.setattr(BasePage, "self_heal_use_llm", True)
    monkeypatch.setattr(BasePage, "self_heal_patch", False)


@pytest.fixture
def drift():
    start = len(runtime.HEALED)
    return lambda: runtime.HEALED[start:]


@pytest.fixture
def fake_api(monkeypatch):
    """桩掉那一次 HTTP 往返，其余全部真跑。返回 calls 供断言 prompt 内容。"""
    calls = []

    def install(candidates):
        # 刻意不用 sk-ant- 前缀：仓库是公开的，带真实 key 形态的字符串
        # 会被 GitHub 的密钥扫描当成泄露报警。
        monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key-for-tests")

        def fake_urlopen(req, timeout=None):
            calls.append({
                "url": req.full_url,
                "headers": dict(req.headers),
                "body": json.loads(req.data.decode("utf-8")),
            })
            payload = {"content": [{"type": "text", "text": json.dumps(
                {"candidates": [{"selector": s, "why": "测试桩"} for s in candidates]},
                ensure_ascii=False)}]}
            return _FakeResponse(json.dumps(payload).encode("utf-8"))

        monkeypatch.setattr(heal_llm.urllib.request, "urlopen", fake_urlopen)
        return calls

    return install


def _prime(page):
    """先在改版前点一次，让指纹库记下这个定位符命中过什么元素。"""
    po = AmbiguousLoginPage(page)
    po.goto(url("v4_before.html"))
    po.click(AmbiguousLoginPage.MAIN_LOGIN_BTN)
    return po


class TestRulesGiveUpFirst:
    def test_without_key_rules_give_up_and_test_fails(self, page, drift, monkeypatch):
        """没有 key 时退回纯规则模式。规则交白卷，用例照常失败 —— 不该凑。"""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(heal_llm, "available", lambda: False)
        po = _prime(page)
        po.goto(url("v4_after.html"))
        with pytest.raises(Exception):
            po.click(AmbiguousLoginPage.MAIN_LOGIN_BTN)
        assert drift() == [], "规则本该交白卷，却给出了候选"


class TestLLMHealing:
    def test_llm_candidate_passes_gates_and_heals(self, page, drift, fake_api):
        """模型用结构上下文把两个同名按钮分开 —— 规则拼不出这种选择器。"""
        calls = fake_api(['main >> role=button[name="登录"]'])
        po = _prime(page)
        po.goto(url("v4_after.html"))
        po.click(AmbiguousLoginPage.MAIN_LOGIN_BTN)

        assert len(calls) == 1, "模型没有被调用 —— LLM 分支未生效"
        assert len(drift()) == 1
        assert drift()[0]["strategy"] == "llm"
        assert drift()[0]["new"] == 'main >> role=button[name="登录"]'
        assert page.evaluate("() => window.CLICKED") == ["main-login"], \
            "自愈到了导航栏那个按钮"

    def test_prompt_carries_intent_and_fingerprint(self, page, fake_api):
        """送进模型的必须是意图 + 指纹，而不是让它自由发挥。"""
        calls = fake_api(['main >> role=button[name="登录"]'])
        po = _prime(page)
        po.goto(url("v4_after.html"))
        po.click(AmbiguousLoginPage.MAIN_LOGIN_BTN)

        prompt = calls[0]["body"]["messages"][0]["content"]
        assert "#main-login" in prompt                 # 失效的选择器
        assert "MAIN_LOGIN_BTN" in prompt              # 常量名
        assert "主区" in prompt                         # 代码注释里的意图
        assert "可及名称=登录" in prompt                 # 上次命中的元素形态
        assert calls[0]["headers"]["X-api-key"] == "dummy-key-for-tests"

    def test_rules_win_first_model_not_called(self, page, drift, fake_api):
        """规则能给出答案时不调模型 —— 有 testid 摆着还调模型既慢又贵。"""
        calls = fake_api(["#whatever"])
        po = _LoginLike(page)
        po.goto(url("v1_login.html"))
        po.click(_LoginLike.LOGIN_BTN)
        po.goto(url("v2_login.html"))
        po.click(_LoginLike.LOGIN_BTN)
        assert calls == [], "规则已经找到 testid 候选，不该再调模型"
        assert drift()[0]["strategy"] == "testid"



class TestModelIsNotABackdoor:
    """模型可以提候选，但不能豁免任何一道闸。"""

    def test_gate_rejects_semantically_wrong_suggestion(self, page, drift, fake_api):
        """模型指向一个语义完全不同的按钮 —— 意图指纹必须把它挡掉。"""
        fake_api(["#retry-btn"])
        po = _LoginLike(page)
        po.goto(url("v1_login.html"))
        po.click(_LoginLike.LOGIN_BTN)
        po.goto(url("v3_gone.html"))
        with pytest.raises(Exception):
            po.click(_LoginLike.LOGIN_BTN)
        assert drift() == [], "模型的建议绕过了意图指纹闸 —— 这就是假通过的后门"

    def test_gate_rejects_nonexistent_selector(self, page, drift, fake_api):
        """模型凭空编一个选择器 —— 唯一命中闸必须把它挡掉。"""
        fake_api(["#totally-made-up"])
        po = _prime(page)
        po.goto(url("v4_after.html"))
        with pytest.raises(Exception):
            po.click(AmbiguousLoginPage.MAIN_LOGIN_BTN)
        assert drift() == []

    def test_gate_rejects_ambiguous_selector(self, page, drift, fake_api):
        """模型给出的选择器命中 2 个元素 —— 唯一性闸必须把它挡掉。"""
        fake_api(['role=button[name="登录"]'])
        po = _prime(page)
        po.goto(url("v4_after.html"))
        with pytest.raises(Exception):
            po.click(AmbiguousLoginPage.MAIN_LOGIN_BTN)
        assert drift() == []


class TestKnownLimit:
    """已知边界：指纹分不开的两个元素，闸也分不开。

    v4 页面上的两个按钮 tag / role / 可及名称完全相同。三道闸查的是
    「唯一命中 + 可见 + 符合意图指纹」—— 模型指向导航栏那个时，这三条
    **全都满足**，闸放行。此时正确与否完全取决于模型的判断。

    这不是缺陷修复的遗漏，而是机制的固有边界：闸能挡住「语义明显不对」和
    「凭空编造」，挡不住「两个长得一模一样的元素里挑错了一个」。

    本用例断言的是**当前真实行为**。它变红说明闸的判定强度变了，需要重新
    评估这段说明是否还成立。
    """

    def test_identical_fingerprint_is_not_discriminated(self, page, drift, fake_api):
        fake_api(['nav >> role=button[name="登录"]'])     # 故意指向错的那个
        po = _prime(page)
        po.goto(url("v4_after.html"))
        po.click(AmbiguousLoginPage.MAIN_LOGIN_BTN)

        assert len(drift()) == 1, "闸挡住了 —— 判定强度已变，请更新本用例的说明"
        assert page.evaluate("() => window.CLICKED") == ["nav-login"], \
            "闸放行了模型指向的元素，且点中的确实是导航栏那个"
