"""定位失败拦截器 —— 自愈的统一入口。

为什么单独成一个组件，而不是把逻辑写进 BasePage：
拦截策略是会变的（先规则后模型、是否写回、要不要拦某些页面），基类不该
因为这些变化被反复改。BasePage 只负责把定位委派出去，换一种拦截策略时
基类一行都不用动。

拦截范围严格限定在**元素定位失败**。断言不通过、超时、网络错误一律不归它管 ——
自愈介入那些场景就等于替业务掩盖真实缺陷。
"""
from __future__ import annotations

import inspect

from core.exceptions import ElementLocationError
from core.healing import patcher, runtime
from core.healing.engine import intent_from_source
from core.logger import get_logger

log = get_logger("velocitai.healing")

# Playwright 定位失败时抛出的异常，其文本特征。用于把「元素没找到」
# 与「断言不通过」区分开 —— 只有前者允许自愈介入。
_LOCATION_HINTS = (
    "strict mode violation",
    "waiting for locator",
    "element is not attached",
    "no element matches",
    "failed to find element",
)


def is_location_failure(exc: BaseException) -> bool:
    """这个异常是不是「元素定位失败」。

    只靠捕获 Exception 无法区分「按钮找不到」和「断言不通过」，
    而自愈只允许介入前者。
    """
    if isinstance(exc, ElementLocationError):
        return True
    name = type(exc).__name__
    if name in ("TimeoutError", "PlaywrightTimeoutError"):
        return True
    text = str(exc).lower()
    return any(h in text for h in _LOCATION_HINTS)


class LocatorInterceptor:
    """把每一次定位收口到这里，失败时决定是否自愈。

    职责：指纹记忆、定位失败判定、自愈调度、可选的源码写回。
    """

    def __init__(self, page, owner, *, artifact: str = "", fingerprints: str = "",
                 use_llm: bool = False, patch: bool = False):
        self.page = page
        self.owner = owner                  # PageObject 的类，用于取源码与命名
        self.artifact = artifact
        self.use_llm = use_llm
        self.patch = patch
        self._store = runtime.FingerprintStore(fingerprints) if fingerprints else None
        self._healed: dict = {}             # 本次运行内已修复的选择器
        self._seen: set = set()

    # ── 对外入口 ──────────────────────────────────────────────────────
    def resolve(self, selector: str) -> str:
        """返回本次应当使用的选择器。

        命中则原样返回并记指纹；失效则尝试自愈，愈不了仍返回原选择器 ——
        让调用方按原样失败，绝不放宽标准硬凑一个。
        """
        if selector in self._healed:
            return self._healed[selector]
        try:
            if self.page.locator(selector).count() > 0:
                self._remember(selector)
                return selector
        except Exception:
            return selector          # 定位器本身异常不归自愈管
        healed = self.heal(selector)
        return healed or selector

    def handle_failure(self, exc: BaseException, selector: str) -> str | None:
        """反应式入口：给定一个已经抛出的异常，若属定位失败则尝试自愈。

        供在 BasePage 之外捕获到异常的调用方使用（例如自定义等待逻辑）。
        """
        if not is_location_failure(exc):
            return None
        return self.heal(selector)

    # ── 内部 ─────────────────────────────────────────────────────────
    def _fp_key(self, selector: str) -> str:
        return f"{self.owner.__name__}.{selector}"

    def _remember(self, selector: str) -> None:
        """定位成功时记下命中元素的形态，作为将来自愈的依据。

        每个选择器只记一次，避免给每次点击都加一趟 evaluate。
        """
        if selector in self._seen or self._store is None:
            return
        self._seen.add(selector)
        self._store.put(self._fp_key(selector),
                        runtime.capture_fingerprint(self.page, selector))

    def _intent(self, selector: str):
        try:
            source = inspect.getsource(self.owner)
        except Exception:
            source = ""      # 源码取不到就只靠指纹，判定会自动收紧
        fp = self._store.get(self._fp_key(selector)) if self._store else None
        return intent_from_source(source, selector, self.owner.__name__, fp)

    def heal(self, selector: str) -> str | None:
        """尝试为一个失效的定位符找出替代选择器。"""
        intent = self._intent(selector)
        log.info("定位失败，尝试自愈：%s.%s = %s",
                 intent.page_object or "?", intent.constant, selector)
        new = runtime.attempt(self.page, intent, self.artifact, use_llm=self.use_llm)
        if not new:
            log.info("未找到可靠替代，按原样失败：%s", selector)
            return None
        self._healed[selector] = new
        log.info("已自愈：%s -> %s", selector, new)
        if self.patch:
            self._write_back(intent, new)
        return new

    def _write_back(self, intent, new_selector: str) -> None:
        """把修复写回 PageObject 源码。

        失败不抛：本次运行已经愈好了，写回失败只意味着下次还要再修一遍，
        不该因此让用例失败。
        """
        try:
            path = inspect.getsourcefile(self.owner)
        except Exception:
            path = None
        if not path:
            return
        ok = patcher.patch_file(path, intent.constant, intent.selector, new_selector)
        runtime.PATCHED.append({
            "file": path, "constant": intent.constant,
            "old": intent.selector, "new": new_selector, "ok": ok,
        })
        log.info("写回源码 %s：%s", "成功" if ok else "失败", path)
