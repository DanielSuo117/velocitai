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

# Playwright 在「等某个元素」时才会写进报错文本的措辞。业务代码几乎不可能
# 凑巧写出这些句子，因此不论异常类型一律认。
_LOCATOR_MARKERS = (
    "strict mode violation",
    "waiting for locator",
    "waiting for selector",
)

# 同样指向定位失败，但措辞太普通，业务异常可能恰好包含（实测：一个写着
# "no element matches the criteria" 的 ValueError 会被误判为定位失败）。
# 因此只在异常确实由 Playwright 抛出时才认。
_WEAK_MARKERS = (
    "element is not attached",
    "no element matches",
    "failed to find element",
)

# 页面级操作的超时：导航、等 URL、等加载状态、等事件。它们不是定位失败 ——
# 接口挂了、跳转没发生，自愈介入只会替真实缺陷打掩护，而且抓到的快照是
# 一个还没到位的页面，极易顶替到无关元素。这条是硬否决，优先于一切标志。
_PAGE_LEVEL_OPS = (
    "page.goto", "page.reload", "page.go_back", "page.go_forward",
    "page.wait_for_url", "page.wait_for_load_state",
    "page.wait_for_event", "page.wait_for_function",
    "frame.goto", "browsercontext.", "browser.", "response.", "request.",
)


def _from_playwright(exc: BaseException) -> bool:
    return type(exc).__module__.split(".")[0] == "playwright"


def is_location_failure(exc: BaseException) -> bool:
    """这个异常是不是「元素定位失败」。

    只靠捕获 Exception 无法区分「按钮找不到」和「断言不通过」，
    而自愈只允许介入前者。

    判定刻意偏保守：拿不准就返回 False。漏判的代价是用例照常失败（等于
    没有自愈，安全）；误判的代价是在一个不该动的场景上启动自愈，可能把
    真失败变成假通过 —— 那是整套机制唯一不能失守的地方。

    这也是为什么不再「凡 TimeoutError 即定位失败」：实测 page.goto 的导航
    超时正是 TimeoutError，会被一路误判进自愈。
    """
    if isinstance(exc, ElementLocationError):
        return True
    text = str(exc).lower()
    if any(op in text for op in _PAGE_LEVEL_OPS):
        return False
    if any(m in text for m in _LOCATOR_MARKERS):
        return True
    return _from_playwright(exc) and any(m in text for m in _WEAK_MARKERS)


class LocatorInterceptor:
    """把每一次定位收口到这里，失败时决定是否自愈。

    职责：指纹记忆、定位失败判定、自愈调度、可选的源码写回。

    **自愈是反应式的**：只在操作真正抛出定位失败之后介入，绝不在操作前
    预探测。预探测会在页面尚未渲染完时误判，详见 current() 的说明。
    """

    # 单个页面对象实例内的自愈次数上限。定位符大面积失效时，逐个抓全页快照
    # 既慢又没有意义 —— 那已经不是「某个选择器过期」，而是页面整体变了。
    MAX_ATTEMPTS = 25

    def __init__(self, page, owner, *, artifact: str = "", fingerprints: str = "",
                 use_llm: bool = False, patch: bool = False, scope: str = ""):
        self.page = page
        self.owner = owner                  # PageObject 的类，用于取源码与命名
        self.artifact = artifact
        # 组件的根节点选择器；整页对象为空。定位、指纹、自愈全部收窄到它之内。
        self.scope = scope
        self.use_llm = use_llm
        self.patch = patch
        self._store = runtime.FingerprintStore(fingerprints) if fingerprints else None
        self._healed: dict = {}             # 本次运行内已修复的选择器
        self._failed: set = set()           # 已尝试且愈不了的，不再重复抓快照
        self._attempts = 0
        self._seen: set = set()

    # ── 对外入口 ──────────────────────────────────────────────────────
    def current(self, selector: str) -> str:
        """返回本次应当使用的选择器：已愈过就用新的，否则用原来的。

        **不碰页面**。自愈是反应式的 —— 只有操作真正失败后才介入。
        曾经这里用 locator.count() 做前置探测，那是错的：count() 不做自动
        等待，SPA 页面尚在渲染时会把「还没挂载」误判成「定位失效」，于是在
        半渲染的页面上启动自愈，极易顶替到一个恰好已渲染的无关元素 ——
        用例照绿而点的是别的按钮，正是本机制要防的假通过。
        """
        return self._healed.get(selector, selector)

    def note_success(self, selector: str, effective: str | None = None) -> None:
        """操作成功后记下命中元素的形态，作为将来自愈的依据。

        effective 是本次实际生效的选择器：自愈之后它与原始选择器不同，
        必须拿它去采指纹 —— 用已失效的原始选择器查，只会拿到 null。
        归档仍按原始选择器为键，因为那才是源码里写着的那个。
        """
        self._remember(selector, effective or selector)

    def handle_failure(self, exc: BaseException, selector: str) -> str | None:
        """反应式入口：操作抛出异常后调用。属定位失败才自愈，否则返回 None。

        断言不通过、参数错误等一律不介入 —— 自愈碰那些场景就等于替业务
        掩盖真实缺陷。
        """
        if not is_location_failure(exc):
            return None
        return self.heal(selector)

    # ── 内部 ─────────────────────────────────────────────────────────
    def _fp_key(self, selector: str) -> str:
        return f"{self.owner.__name__}.{selector}"

    def _remember(self, selector: str, effective: str | None = None) -> None:
        """定位成功时记下命中元素的形态，作为将来自愈的依据。

        按 (原始选择器, 实际生效选择器) 去重，而不是只按原始选择器：自愈之后
        生效的是新选择器，它命中的元素形态必须重新采一次。只按原始选择器记，
        自愈后的指纹会永远停留在失效前的那一份。

        去重仍然存在，是为了避免给每次点击都加一趟 evaluate。
        """
        eff = effective or selector
        if self._store is None or (selector, eff) in self._seen:
            return
        self._seen.add((selector, eff))
        self._store.put(self._fp_key(selector),
                        runtime.capture_fingerprint(self.page, eff, self.scope))

    def _intent(self, selector: str):
        try:
            source = inspect.getsource(self.owner)
        except Exception:
            source = ""      # 源码取不到就只靠指纹，判定会自动收紧
        fp = self._store.get(self._fp_key(selector)) if self._store else None
        return intent_from_source(source, selector, self.owner.__name__, fp)

    def heal(self, selector: str) -> str | None:
        """尝试为一个失效的定位符找出替代选择器。"""
        if selector in self._healed:
            return self._healed[selector]
        if selector in self._failed:
            return None      # 愈不了的不反复重试：is_page_loaded 这类轮询会
                             # 让每次调用都抓一次全页快照，代价高且结论不变
        if self._attempts >= self.MAX_ATTEMPTS:
            log.warning("自愈次数已达上限 %d，不再尝试：%s", self.MAX_ATTEMPTS, selector)
            return None
        self._attempts += 1
        intent = self._intent(selector)
        log.info("定位失败，尝试自愈：%s.%s = %s",
                 intent.page_object or "?", intent.constant, selector)
        new = runtime.attempt(self.page, intent, self.artifact,
                              use_llm=self.use_llm, scope=self.scope)
        if not new:
            log.info("未找到可靠替代，按原样失败：%s", selector)
            self._failed.add(selector)
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
