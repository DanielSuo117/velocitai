"""所有页面对象的基类 —— 公共能力在此封装，业务页面继承即可。

约定（见 rules/coding-conventions）：
- 定位符写作类顶部常量，并带注释说明其语义，例如
      LOGIN_BUTTON = "#login-btn"   # P0: 登录按钮
  注释不是可有可无的装饰：它是选择器失效时自愈用来还原意图的依据。
- 子类必须实现 is_page_loaded()，作为页面加载完成的判定锚点。

所有定位都经由 _act()/_locate() 收口到拦截器，因此自愈对业务代码完全透明 ——
页面对象不需要知道自愈存在。定位作用域同样只有一个出口：scope_root()。
"""
from __future__ import annotations

from playwright.sync_api import Locator, Page

from core.healing.interceptor import LocatorInterceptor
from core.healing.runtime import scoped


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
                scope=self.scope_root(),
            )
        return self._interceptor

    def scope_root(self) -> str:
        """本对象的定位作用域根节点。整页对象为空串，组件覆盖为其 root。

        **所有** locator 构造都经由 _scoped() 带上它。子类若只覆盖 _locate()
        而不覆盖本方法，作用域会在 _act() 路径上悄悄丢失 —— 那正是本方法
        存在的原因（组件的 root 曾因此完全失效，操作跑到整页去找元素）。
        """
        return ""

    def _scoped(self, selector: str) -> str:
        return scoped(selector, self.scope_root())

    def _locate(self, selector: str) -> Locator:
        """取一个 Locator。已愈过的选择器会返回修复后的版本。

        注意：经由本方法拿到 Locator 后再自行调用 .click() 等操作时，
        **自愈无法介入** —— 异常在本方法之外抛出。需要自愈保护的操作请走
        下面封装好的方法，或用 _act()。
        """
        if not self.self_heal_enabled:
            return self.page.locator(self._scoped(selector))
        return self.page.locator(self._scoped(self.interceptor.current(selector)))

    def _act(self, selector: str, op):
        """执行一次定位操作；**仅在操作真正因定位失败而报错后**才自愈并重试一次。

        为什么不在操作前预探测（例如 locator.count() > 0）：count() 不做
        自动等待。SPA 页面尚在渲染时，目标元素还没挂载，预探测会把「还没到」
        误判成「定位失效」，于是在半渲染的页面上启动自愈 —— 极易顶替到一个
        恰好已渲染的无关元素，用例照绿而点的是别的按钮。那正是本机制存在
        的意义所在的反面。

        反应式的另一个好处：Playwright 自身的自动等待先跑完，只有它都等不到
        才算真的失效，判定依据比预探测强得多。
        """
        if not self.self_heal_enabled:
            return op(self.page.locator(self._scoped(selector)))
        itc = self.interceptor
        effective = itc.current(selector)
        try:
            result = op(self.page.locator(self._scoped(effective)))
        except Exception as exc:
            new = itc.handle_failure(exc, selector)
            if not new:
                raise                      # 愈不了就按原样失败，绝不吞异常
            result = op(self.page.locator(self._scoped(new)))
            itc.note_success(selector, new)
            return result
        itc.note_success(selector, effective)
        return result

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
        self._act(selector, lambda loc: loc.click(**kwargs))

    def double_click(self, selector: str, **kwargs):
        self._act(selector, lambda loc: loc.dblclick(**kwargs))

    def fill(self, selector: str, value: str, **kwargs):
        self._act(selector, lambda loc: loc.fill(value, **kwargs))

    def type_text(self, selector: str, value: str, **kwargs):
        """逐字符输入。仅在目标控件依赖 keydown 事件时使用，否则用 fill。"""
        self._act(selector, lambda loc: loc.type(value, **kwargs))

    def clear(self, selector: str, **kwargs):
        self._act(selector, lambda loc: loc.fill("", **kwargs))

    def hover(self, selector: str, **kwargs):
        self._act(selector, lambda loc: loc.hover(**kwargs))

    def check(self, selector: str, **kwargs):
        self._act(selector, lambda loc: loc.check(**kwargs))

    def uncheck(self, selector: str, **kwargs):
        self._act(selector, lambda loc: loc.uncheck(**kwargs))

    def select_option(self, selector: str, value, **kwargs):
        self._act(selector, lambda loc: loc.select_option(value, **kwargs))

    def upload(self, selector: str, files, **kwargs):
        self._act(selector, lambda loc: loc.set_input_files(files, **kwargs))

    def press(self, selector: str, key: str, **kwargs):
        self._act(selector, lambda loc: loc.press(key, **kwargs))

    def scroll_into_view(self, selector: str, **kwargs):
        self._act(selector, lambda loc: loc.scroll_into_view_if_needed(**kwargs))

    # ── 读取 ────────────────────────────────────────────────────────
    def get_text(self, selector: str) -> str:
        return self._act(selector, lambda loc: loc.inner_text())

    def get_value(self, selector: str) -> str:
        return self._act(selector, lambda loc: loc.input_value())

    def get_attribute(self, selector: str, name: str):
        return self._act(selector, lambda loc: loc.get_attribute(name))

    def get_element_count(self, selector: str) -> int:
        """元素个数。**不触发自愈**：返回 0 是合法答案（断言「列表为空」），
        把它当成定位失效会导致在正常页面上乱找元素。"""
        return self._locate(selector).count()

    def get_all_texts(self, selector: str) -> list:
        return self._act(selector, lambda loc: loc.all_inner_texts())

    # ── 状态判定 ────────────────────────────────────────────────────
    def is_visible(self, selector: str, timeout: int | None = None) -> bool:
        try:
            kwargs = {"timeout": timeout} if timeout is not None else {}
            self._act(selector, lambda loc: loc.wait_for(state="visible", **kwargs))
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
        self._act(selector, lambda loc: loc.wait_for(state=state, timeout=timeout))

    def wait_for_url(self, url, **kwargs):
        self.page.wait_for_url(url, **kwargs)

    def wait_for_load_state(self, state: str = "load", **kwargs):
        self.page.wait_for_load_state(state, **kwargs)

    # ── 子类契约 ────────────────────────────────────────────────────
    def is_page_loaded(self) -> bool:
        """页面是否加载完成。子类必须实现，作为断言与等待的锚点。"""
        raise NotImplementedError("Subclasses must implement is_page_loaded()")
