"""自愈的运行时层 —— 只通过传入的 page 对象操作浏览器，自身不导入 Playwright。

这样做有两个好处：模块可以脱离浏览器被单测（传假 page 即可），
以及 pages 包不会因为引入自愈而多一条硬依赖。

与 self_heal.py 的分工：那边是「给定意图和快照，算出候选」的纯逻辑；
这边负责「从真实页面取快照、把候选拿去实跑验证」。
"""
from __future__ import annotations

import json
import os

from core.healing.engine import (
    Candidate, HealProposal, Intent, matches_intent, rank, record,
)

# 隐式 ARIA role 推导。
# 页面 JS 里没有 element.computedRole（实测确认不存在于 Element.prototype），
# 只用 getAttribute('role') 的话，原生 <button>/<a> 几乎全部得不到 role ——
# 于是「role + 可及名称」策略与指纹的 role 维度都会静默失效。
# 这里只覆盖定位符实际会指向的交互元素，宁缺毋滥。
_ROLE_JS = """
  const implicitRole = (e) => {
    const explicit = e.getAttribute('role');
    if (explicit) return explicit;
    const t = e.tagName.toLowerCase();
    if (t === 'button') return 'button';
    if (t === 'a') return e.hasAttribute('href') ? 'link' : null;
    if (t === 'select') return e.multiple ? 'listbox' : 'combobox';
    if (t === 'textarea') return 'textbox';
    if (/^h[1-6]$/.test(t)) return 'heading';
    if (t === 'li') return 'listitem';
    if (t === 'td') return 'cell';
    if (t === 'th') return 'columnheader';
    if (t === 'input') {
      const ty = (e.getAttribute('type') || 'text').toLowerCase();
      if (ty === 'checkbox') return 'checkbox';
      if (ty === 'radio') return 'radio';
      if (ty === 'submit' || ty === 'button' || ty === 'reset') return 'button';
      if (ty === 'search') return 'searchbox';
      if (ty === 'hidden') return null;
      return 'textbox';
    }
    return null;
  };
  // 可及名称：显式标注优先，其次关联 label，最后回退到自身文本。
  // 按钮和链接的可及名称本就来自其文本内容，不回退等于把它们的名称丢掉。
  const accName = (e) => {
    const explicit = (e.getAttribute('aria-label') || e.getAttribute('title') || '').trim();
    if (explicit) return explicit;
    const lbl = (e.labels && e.labels[0] && e.labels[0].innerText || '').trim();
    if (lbl) return lbl;
    const t = e.tagName.toLowerCase();
    if (t === 'button' || t === 'a' || t === 'label' || /^h[1-6]$/.test(t)) {
      return (e.innerText || '').trim().slice(0, 60) || null;
    }
    return null;
  };
"""

# 只采集可能承载交互或语义的元素，避免把整棵 DOM 拖回 Python 侧。
SNAPSHOT_JS = """
(root) => {""" + _ROLE_JS + """
  const SEL = 'a,button,input,select,textarea,label,[role],[data-testid],[data-test],[data-qa],[data-cy],h1,h2,h3,li,td,th,span[id]';
  // root 非空时只采它内部的元素：组件的自愈不得越出自己的根节点去别处找，
  // 越界修复正是「顶替到无关元素」的典型路径。
  const base = root ? document.querySelector(root) : document;
  if (!base) return [];
  const out = [];
  for (const e of base.querySelectorAll(SEL)) {
    const r = e.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;   // 不可见元素不参与自愈
    const attrs = {};
    for (const a of e.attributes) attrs[a.name] = a.value;
    out.push({
      tag: e.tagName.toLowerCase(),
      attrs: attrs,
      role: implicitRole(e),
      name: accName(e),
      text: (e.innerText || e.value || '').trim().slice(0, 120),
      classes: Array.from(e.classList || []),
    });
    if (out.length >= 400) break;                    // 上限，防止超大页面拖垮
  }
  return out;
}
"""

# 本次运行内发生过的自愈，供 conftest 在会话结束时汇总。
# 自愈过的用例不能被当作「干净通过」—— 它通过了，但定位符已经漂移，
# 沉默地放过去，下次就是真失败，而且没人知道从哪一次开始坏的。
HEALED: list = []

# 本次运行中被写回源码的定位符。写回是不可逆副作用，必须在终端显式点名，
# 不能只躺在文件里等人发现。
PATCHED: list = []

# 接收元素本身而不是选择器字符串：自愈后的选择器可能是 Playwright 的
# role= / text= 语法，document.querySelector 根本解析不了；组件的作用域
# 前缀 `root >> sel` 同样不是合法 CSS。统一经由 locator 求值才通用。
FINGERPRINT_JS = """
(e) => {""" + _ROLE_JS + """
  return { tag: e.tagName.toLowerCase(), role: implicitRole(e), name: accName(e) };
}
"""


class FingerprintStore:
    """记住每个定位符上次成功命中的元素形态 —— 自愈所依据的「旧有逻辑」。

    没有它，失效时就只剩常量注释可用，判定会收紧到几乎无法自愈。
    存盘失败一律吞掉：这是加速结构，不是正确性来源。
    """

    def __init__(self, path: str):
        self.path = path
        self._data: dict = {}
        try:
            with open(path, encoding="utf-8") as f:
                self._data = json.load(f)
        except Exception:
            self._data = {}

    def get(self, key: str) -> dict | None:
        v = self._data.get(key)
        return v if isinstance(v, dict) else None

    def put(self, key: str, fp: dict | None) -> None:
        if not fp:
            return
        if self._data.get(key) == fp:
            return
        self._data[key] = fp
        self._flush()

    def _flush(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def scoped(selector: str, scope: str = "") -> str:
    """把相对选择器落到实际定位范围。scope 为空即整页。

    组件的选择器在源码里写成相对形态（`.btn-ok`），真正定位时必须带上根
    节点（`.modal >> .btn-ok`）—— 否则同一个 class 在页面别处出现时会串台。
    """
    return f"{scope} >> {selector}" if scope else selector


def capture_fingerprint(page, selector: str, scope: str = "") -> dict | None:
    """定位成功时记下它命中的元素形态。任何异常都不得影响正常用例。"""
    try:
        return page.locator(scoped(selector, scope)).first.evaluate(FINGERPRINT_JS)
    except Exception:
        return None


def snapshot(page, scope: str = "") -> list:
    try:
        els = page.evaluate(SNAPSHOT_JS, scope or None)
        return els if isinstance(els, list) else []
    except Exception:
        return []


def _resolves_uniquely(page, selector: str, scope: str = "") -> bool:
    """候选必须在真实页面上唯一命中且可见 —— 快照判定之外的最后一道闸。

    唯一性也在 scope 之内判定：组件内唯一即可，不要求全页唯一。
    """
    try:
        loc = page.locator(scoped(selector, scope))
        if loc.count() != 1:
            return False
        return bool(loc.first.is_visible())
    except Exception:
        return False


ELEMENT_FP_JS = """
(e) => {""" + _ROLE_JS + """
  return { tag: e.tagName.toLowerCase(), role: implicitRole(e), name: accName(e),
           text: (e.innerText || e.value || '').trim().slice(0, 120),
           classes: Array.from(e.classList || []) };
}
"""


def _element_of(page, selector: str, scope: str = ""):
    """取出候选实际命中的那个元素的形态，用于校验它是否真是原来那个。

    不能用 document.querySelector：候选可能是 Playwright 的 role= / text= 语法，
    CSS 引擎不认。必须经由 locator 求值。
    """
    try:
        return page.locator(scoped(selector, scope)).first.evaluate(ELEMENT_FP_JS)
    except Exception:
        return None


def attempt(page, intent: Intent, artifact_path: str = "", test_id: str = "",
            use_llm: bool = False, scope: str = "") -> str | None:
    """尝试为一个失效的定位符找出替代选择器。

    顺序是「规则优先，模型兜底」：有 testid 摆在那儿时调模型既慢又贵，
    结论也不会更好；模型只在规则交白卷时出场。

    scope 非空时全程收窄到该根节点之内（组件场景）：快照只采 root 内部的元素，
    唯一性也在 root 内判定。返回的选择器保持**相对形态**，作用域由调用方重新
    拼上 —— 这样自愈结果写回源码时仍是组件里原本的那种写法。

    返回可用的新选择器，或 None（找不到就按原样失败 —— 绝不放宽标准硬凑一个）。
    无论结果如何都会留下提案记录，供复核与写回。
    """
    elements = snapshot(page, scope)
    candidates = rank(intent, elements)
    chosen = None
    tried = []
    for cand in candidates:
        tried.append(cand.selector)
        if _resolves_uniquely(page, cand.selector, scope):
            chosen = cand
            break

    if chosen is None and use_llm:
        chosen = _llm_candidate(page, intent, elements, tried, scope)
        if chosen:
            candidates = candidates + [chosen]

    if chosen:
        HEALED.append({"page_object": intent.page_object, "constant": intent.constant,
                       "old": intent.selector, "new": chosen.selector,
                       "strategy": chosen.strategy, "confidence": chosen.confidence,
                       "test_id": test_id})

    if artifact_path:
        url = ""
        try:
            url = page.url
        except Exception:
            pass
        record(HealProposal(intent=intent, candidates=candidates, chosen=chosen,
                            url=url, test_id=test_id), artifact_path)
    return chosen.selector if chosen else None


def _llm_candidate(page, intent: Intent, elements: list, tried: list, scope: str = ""):
    """让模型看页面结构推断，再用与规则候选完全相同的闸逐条校验。

    模型可以提出规则拼不出的候选，但**不能豁免任何一道闸**：
    它的建议同样必须唯一命中、可见、且命中的元素符合意图指纹。
    否则「让模型来判断」就成了绕过防假通过保证的后门。
    """
    try:
        from core.healing import llm as heal_llm

        if not heal_llm.available():
            return None
        for sel in heal_llm.infer(intent, elements, tried):
            if not _resolves_uniquely(page, sel, scope):   # 闸②③：唯一 + 可见
                continue
            el = _element_of(page, sel, scope)
            if not el or not matches_intent(intent, el):   # 闸①：意图指纹
                continue
            return Candidate(sel, "llm", 80,
                             "模型依据常量注释与历史指纹推断，并已通过全部三道闸校验")
    except Exception:
        return None       # 推理层任何故障都不得影响测试结论
    return None
