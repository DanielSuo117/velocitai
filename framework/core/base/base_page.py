"""所有页面对象的基类 —— 公共能力在此封装，业务页面继承即可。

约定（见 rules/coding-conventions）：
- 定位符写作类顶部常量，并带注释说明其语义，例如
      LOGIN_BUTTON = "#login-btn"   # P0: 登录按钮
  注释不是可有可无的装饰：它是选择器失效时自愈用来还原意图的依据。
- 子类必须实现 is_page_loaded()，作为页面加载完成的判定锚点。

所有定位都经由 _locate() 收口到拦截器，因此自愈对业务代码完全透明 ——
页面对象不需要知道自愈存在。
"""
from __future__ import annotations

from playwright.sync_api import Locator, Page

from core.healing.interceptor import LocatorInterceptor


class BasePage:
    # 自愈默认关闭。它会改变「失败」的含义，必须由使用者显式选择
    # （pytest --self-heal=on|strict|auto，见 conftest.py）。
    self_heal_enabled = False
    self_heal_use_llm = False        # 规则交白卷时让模型出场，需要 API key
    self_heal_patch = False          # 把修复写回源码，会改动工作区文件
    heal_artifact = "reports/self-heal/proposals.jsonl"
    heal_fingerprints = "reports/self-heal/fingerprints.json"

    def __init__(self, page: Page):
        self.page = page
        self._interceptor: LocatorInterceptor | None = None

    # ── 定位入口 ────────────────────────────────────────────────────
    @property
    def interceptor(self) -> LocatorInterceptor:
        if self._interceptor is None:
            self._interceptor = LocatorInterceptor(
                self.page, type(self),
                artifact=self.heal_artifact,
                fingerprints=self.heal_fingerprints,
                use_llm=self.self_heal_use_llm,
                patch=self.self_heal_patch,
            )
        return self._interceptor

    def _locate(self, selector: str) -> Locator:
        """所有定位的唯一入口。自愈关闭时与直接 locator() 逐字等价。"""
        if not self.self_heal_enabled:
            return self.page.locator(selector)
        return self.page.locator(self.interceptor.resolve(selector))

    # ── 导航 ────────────────────────────────────────────────────────
    def goto(self, url: str, **kwargs):
        self.page.goto(url, **kwargs)

    def reload(self, **kwargs):
        self.page.reload(**kwargs)

    @property
    def url(self) -> str:
        return self.page.url

    @property
    def title(self) -> str:
        return self.page.title()

    # ── 交互 ────────────────────────────────────────────────────────
    def click(self, selector: str, **kwargs):
        self._locate(selector).click(**kwargs)

    def double_click(self, selector: str, **kwargs):
        self._locate(selector).dblclick(**kwargs)

    def fill(self, selector: str, value: str, **kwargs):
        self._locate(selector).fill(value, **kwargs)

    def type_text(self, selector: str, value: str, **kwargs):
        """逐字符输入。仅在目标控件依赖 keydown 事件时使用，否则用 fill。"""
        self._locate(selector).type(value, **kwargs)

    def clear(self, selector: str, **kwargs):
        self._locate(selector).fill("", **kwargs)

    def hover(self, selector: str, **kwargs):
        self._locate(selector).hover(**kwargs)

    def check(self, selector: str, **kwargs):
        self._locate(selector).check(**kwargs)

    def uncheck(self, selector: str, **kwargs):
        self._locate(selector).uncheck(**kwargs)

    def select_option(self, selector: str, value, **kwargs):
        self._locate(selector).select_option(value, **kwargs)

    def upload(self, selector: str, files, **kwargs):
        self._locate(selector).set_input_files(files, **kwargs)

    def press(self, selector: str, key: str, **kwargs):
        self._locate(selector).press(key, **kwargs)

    def scroll_into_view(self, selector: str, **kwargs):
        self._locate(selector).scroll_into_view_if_needed(**kwargs)

    # ── 读取 ────────────────────────────────────────────────────────
    def get_text(self, selector: str) -> str:
        return self._locate(selector).inner_text()

    def get_value(self, selector: str) -> str:
        return self._locate(selector).input_value()

    def get_attribute(self, selector: str, name: str):
        return self._locate(selector).get_attribute(name)

    def get_element_count(self, selector: str) -> int:
        return self._locate(selector).count()

    def get_all_texts(self, selector: str) -> list:
        return self._locate(selector).all_inner_texts()

    # ── 状态判定 ────────────────────────────────────────────────────
    def is_visible(self, selector: str, timeout: int | None = None) -> bool:
        try:
            kwargs = {"timeout": timeout} if timeout is not None else {}
            self._locate(selector).wait_for(state="visible", **kwargs)
            return True
        except Exception:
            return False

    def is_enabled(self, selector: str) -> bool:
        try:
            return self._locate(selector).is_enabled()
        except Exception:
            return False

    def is_checked(self, selector: str) -> bool:
        try:
            return self._locate(selector).is_checked()
        except Exception:
            return False

    # ── 等待 ────────────────────────────────────────────────────────
    def wait_for_element(self, selector: str, state: str = "visible", timeout: int = 15000):
        self._locate(selector).wait_for(state=state, timeout=timeout)

    def wait_for_url(self, url, **kwargs):
        self.page.wait_for_url(url, **kwargs)

    def wait_for_load_state(self, state: str = "load", **kwargs):
        self.page.wait_for_load_state(state, **kwargs)

    # ── 子类契约 ────────────────────────────────────────────────────
    def is_page_loaded(self) -> bool:
        """页面是否加载完成。子类必须实现，作为断言与等待的锚点。"""
        raise NotImplementedError("Subclasses must implement is_page_loaded()")
