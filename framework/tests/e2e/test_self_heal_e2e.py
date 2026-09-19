"""选择器自愈的端到端验证 —— 真浏览器、真 DOM、真 Playwright 异常。

单测用假 page 验证判定逻辑，但有一类事情假 page 永远证明不了：Playwright
真正抛出的异常长什么样、自动等待到底等不等、组件的 `>>` 作用域在真实引擎里
是否生效。本文件补的就是这一段。

夹具是两份 HTML，模拟一次前端改版（`#login-btn` 被构建拿掉，换成
`data-testid`）。每份夹具里都放了**诱饵** —— 与目标同标签、同文案、甚至
同 class 的另一个元素。自愈一旦越界或过早触发就会点中诱饵，而 window.CLICKED
会把它记下来。断言「点成功了」不够，必须断言「点的是哪一个」。

运行（需要浏览器）：
    pytest framework/tests/e2e --env=pre --self-heal=on
不加 --self-heal 时整组跳过。
"""
from pathlib import Path

import pytest

from core.base.base_component import BaseComponent
from core.base.base_page import BasePage
from core.healing import runtime

FIXTURES = Path(__file__).parent / "fixtures"


def url(name: str) -> str:
    return (FIXTURES / name).as_uri()


class LoginPage(BasePage):
    LOGIN_BTN = "#login-btn"        # P0: 登录按钮

    def is_page_loaded(self) -> bool:
        return self.get_element_count("nav") > 0


class OkDialog(BaseComponent):
    ROOT = ".modal"                 # P0: 弹窗根节点
    OK_BTN = ".btn-ok"              # P0: 弹窗里的确定按钮

    def is_page_loaded(self) -> bool:
        return self.is_present()


@pytest.fixture(autouse=True)
def heal_env(request, tmp_path, monkeypatch):
    """每个用例独立的指纹库与提案文件，用例之间不互相影响。"""
    if request.config.getoption("--self-heal") == "off":
        pytest.skip("本组用例验证自愈行为，需 --self-heal=on|strict|auto")
    monkeypatch.setattr(BasePage, "heal_fingerprints", str(tmp_path / "fp.json"))
    monkeypatch.setattr(BasePage, "heal_artifact", str(tmp_path / "proposals.jsonl"))


@pytest.fixture
def drift():
    """本用例内新增的自愈记录。

    刻意**不清空** runtime.HEALED：它是会话级产物，conftest 要靠它出终端汇总、
    strict 档要靠它决定退出码。测试图省事把它清掉，等于把被测特性一起关了
    —— 实测过一次，strict 跑完退出码是 0，汇总一片空白。
    """
    start = len(runtime.HEALED)
    return lambda: runtime.HEALED[start:]


def clicked(page) -> list:
    return page.evaluate("() => window.CLICKED || []")


class TestSelectorDrift:
    """前端改版导致定位符失效 —— 自愈的正题。"""

    def test_heals_after_id_disappears(self, page, drift):
        """改版前点一次记下指纹，改版后 id 没了，必须自愈到同一个按钮。"""
        po = LoginPage(page)

        po.goto(url("v1_login.html"))
        po.click(LoginPage.LOGIN_BTN)
        assert clicked(page) == ["login-v1"]
        assert drift() == [], "改版前不该发生任何自愈"

        po.goto(url("v2_login.html"))          # 前端改版：#login-btn 被拿掉
        po.click(LoginPage.LOGIN_BTN)

        assert len(drift()) == 1, "定位符已失效却没有自愈"
        d = drift()[0]
        assert d["old"] == "#login-btn"
        assert d["new"] == '[data-testid="login"]'
        assert d["strategy"] == "testid"
        assert clicked(page) == ["login-v2"], "自愈顶替到了别的元素"

    def test_healed_selector_is_reused(self, page, drift):
        """同一选择器第二次使用走缓存，不再重复抓快照。"""
        po = LoginPage(page)
        po.goto(url("v1_login.html"))
        po.click(LoginPage.LOGIN_BTN)
        po.goto(url("v2_login.html"))
        po.click(LoginPage.LOGIN_BTN)
        po.click(LoginPage.LOGIN_BTN)
        assert len(drift()) == 1
        assert clicked(page) == ["login-v2", "login-v2"]


class TestNeverFalsePass:
    """机制唯一不能失守的地方：绝不把真失败变成假通过。"""

    def test_no_plausible_candidate_fails_as_usual(self, page, drift):
        """登录按钮真的没了，页面上只剩语义不同的「重试」—— 必须照常失败。"""
        po = LoginPage(page)
        po.goto(url("v1_login.html"))
        po.click(LoginPage.LOGIN_BTN)          # 先记下指纹

        po.goto(url("v3_gone.html"))
        with pytest.raises(Exception) as got:
            po.click(LoginPage.LOGIN_BTN)

        assert "login-btn" in str(got.value)
        assert drift() == [], "在没有可靠替代时硬凑了一个，这就是假通过"
        assert "retry" not in clicked(page), "顶替到了语义完全不同的按钮"

    def test_not_yet_rendered_does_not_heal(self, page, drift):
        """元素只是还没渲染（1.5s 后才挂载）—— Playwright 会等到它，不该自愈。

        页面上另有一个早就渲染好、指纹完全吻合的诱饵。预探测语义下会点中它。
        """
        po = LoginPage(page)
        po.goto(url("v1_login.html"))
        po.click(LoginPage.LOGIN_BTN)          # 先记下指纹

        po.goto(url("late.html"))
        po.click(LoginPage.LOGIN_BTN)

        assert drift() == [], "元素尚未渲染就触发了自愈"
        assert clicked(page) == ["login-late"], "点中了诱饵 —— 用例照绿而点的是别的按钮"


class TestComponentScope:
    """组件的定位不得越出 root —— 越界修复是「顶替到无关元素」的典型路径。"""

    def test_click_stays_inside_root(self, page, drift):
        """页面主区有一个同 class、同文案的诱饵，组件必须点中弹窗里那个。"""
        dlg = OkDialog(page)
        dlg.goto(url("modal.html"))
        dlg.click(OkDialog.OK_BTN)
        assert clicked(page) == ["modal-ok"], "组件的 root 作用域丢失"

    def test_heals_inside_root_only(self, page, drift):
        """弹窗改版后，自愈必须在 root 内找替代，不能挑中主区那个 testid。"""
        dlg = OkDialog(page)
        dlg.goto(url("modal.html"))
        dlg.click(OkDialog.OK_BTN)
        assert drift() == []

        dlg.goto(url("modal_v2.html"))         # 弹窗里的 .btn-ok 没了
        dlg.click(OkDialog.OK_BTN)

        assert len(drift()) == 1
        assert drift()[0]["new"] == '[data-testid="dialog-ok"]', \
            "自愈越出了 root，挑中了页面主区的元素"
        assert clicked(page) == ["modal-ok"]
