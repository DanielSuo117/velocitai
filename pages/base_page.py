import inspect

from playwright.sync_api import Page

from pages import heal_patch, heal_runtime
from pages.self_heal import intent_from_source


class BasePage:
    # 自愈默认关闭。开启会改变「失败」的含义，必须由使用者显式选择
    # （pytest --self-heal=on|strict，见 conftest.py）。
    self_heal_enabled = False
    # 让模型在规则交白卷时出场。需要 ANTHROPIC_API_KEY，取不到则静默退回纯规则。
    self_heal_use_llm = False
    # 自愈成功后把新选择器写回 PageObject 源码。默认关闭 —— 测试进程里改源码
    # 是不可逆的副作用，必须由使用者显式选择（--self-heal=auto）。
    self_heal_patch = False
    heal_artifact = "reports/self-heal/proposals.jsonl"
    heal_fingerprints = "reports/self-heal/fingerprints.json"

    def __init__(self, page: Page):
        self.page = page
        self._heal_cache: dict = {}   # 本次运行内已修复的选择器，避免重复推断
        self._fp_seen: set = set()
        self._store = None

    # ── 自愈 ────────────────────────────────────────────────────────────
    def _fingerprints(self):
        if self._store is None:
            self._store = heal_runtime.FingerprintStore(self.heal_fingerprints)
        return self._store

    def _fp_key(self, selector: str) -> str:
        return f"{type(self).__name__}.{selector}"

    def _remember(self, selector: str) -> None:
        """定位成功时记下命中元素的形态，作为将来自愈的依据。

        每个选择器每个实例只记一次，避免给每次点击都加一趟 evaluate。
        """
        if selector in self._fp_seen:
            return
        self._fp_seen.add(selector)
        fp = heal_runtime.capture_fingerprint(self.page, selector)
        self._fingerprints().put(self._fp_key(selector), fp)

    def _attempt_heal(self, selector: str):
        try:
            source = inspect.getsource(type(self))
        except Exception:
            source = ""      # 源码取不到就只靠指纹，判定会自动收紧
        intent = intent_from_source(
            source, selector, type(self).__name__,
            self._fingerprints().get(self._fp_key(selector)),
        )
        new = heal_runtime.attempt(self.page, intent, self.heal_artifact,
                                   use_llm=self.self_heal_use_llm)
        if new and self.self_heal_patch:
            self._patch_source(intent, new)
        return new

    def _patch_source(self, intent, new_selector: str) -> None:
        """把修复写回 PageObject 源码。失败不抛 —— 本次运行已经healed，
        写回失败只意味着下次还要再修一遍，不该因此让用例失败。"""
        try:
            path = inspect.getsourcefile(type(self))
        except Exception:
            return
        if not path:
            return
        ok = heal_patch.patch_file(path, intent.constant, intent.selector, new_selector)
        heal_runtime.PATCHED.append({
            "file": path, "constant": intent.constant,
            "old": intent.selector, "new": new_selector, "ok": ok,
        })

    def _locate(self, selector: str):
        """所有定位的唯一入口。自愈关闭时行为与直接 locator() 完全一致。"""
        if not self.self_heal_enabled:
            return self.page.locator(selector)
        healed = self._heal_cache.get(selector)
        if healed:
            return self.page.locator(healed)
        loc = self.page.locator(selector)
        try:
            if loc.count() > 0:
                self._remember(selector)
                return loc
        except Exception:
            return loc       # 定位器本身异常不归自愈管，原样抛给调用方
        new = self._attempt_heal(selector)
        if not new:
            return loc       # 找不到可靠替代就按原样失败，绝不放宽标准硬凑
        self._heal_cache[selector] = new
        return self.page.locator(new)

    # ── 基础操作 ────────────────────────────────────────────────────────
    def click(self, selector: str, **kwargs):
        self._locate(selector).click(**kwargs)

    def fill(self, selector: str, value: str, **kwargs):
        self._locate(selector).fill(value, **kwargs)

    def get_text(self, selector: str) -> str:
        return self._locate(selector).inner_text()

    def is_visible(self, selector: str, timeout: int | None = None) -> bool:
        try:
            kwargs = {"timeout": timeout} if timeout is not None else {}
            self._locate(selector).wait_for(state="visible", **kwargs)
            return True
        except Exception:
            return False

    def wait_for_element(self, selector: str, state: str = "visible", timeout: int = 15000):
        self._locate(selector).wait_for(state=state, timeout=timeout)

    def get_element_count(self, selector: str) -> int:
        return self._locate(selector).count()

    def is_page_loaded(self) -> bool:
        raise NotImplementedError("Subclasses must implement is_page_loaded()")
