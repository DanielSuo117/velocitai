"""自愈的运行时层 —— 只通过传入的 page 对象操作浏览器，自身不导入 Playwright。

这样做有两个好处：模块可以脱离浏览器被单测（传假 page 即可），
以及 pages 包不会因为引入自愈而多一条硬依赖。

与 self_heal.py 的分工：那边是「给定意图和快照，算出候选」的纯逻辑；
这边负责「从真实页面取快照、把候选拿去实跑验证」。
"""
from __future__ import annotations

import json
import os

from pages.self_heal import HealProposal, Intent, rank, record

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
() => {""" + _ROLE_JS + """
  const SEL = 'a,button,input,select,textarea,label,[role],[data-testid],[data-test],[data-qa],[data-cy],h1,h2,h3,li,td,th,span[id]';
  const out = [];
  for (const e of document.querySelectorAll(SEL)) {
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

FINGERPRINT_JS = """
(sel) => {""" + _ROLE_JS + """
  const e = document.querySelector(sel);
  if (!e) return null;
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


def capture_fingerprint(page, selector: str) -> dict | None:
    """定位成功时记下它命中的元素形态。任何异常都不得影响正常用例。"""
    try:
        return page.evaluate(FINGERPRINT_JS, selector)
    except Exception:
        return None


def snapshot(page) -> list:
    try:
        els = page.evaluate(SNAPSHOT_JS)
        return els if isinstance(els, list) else []
    except Exception:
        return []


def _resolves_uniquely(page, selector: str) -> bool:
    """候选必须在真实页面上唯一命中且可见 —— 快照判定之外的最后一道闸。"""
    try:
        loc = page.locator(selector)
        if loc.count() != 1:
            return False
        return bool(loc.first.is_visible())
    except Exception:
        return False


def attempt(page, intent: Intent, artifact_path: str = "",
            test_id: str = "") -> str | None:
    """尝试为一个失效的定位符找出替代选择器。

    返回可用的新选择器，或 None（找不到就按原样失败 —— 绝不放宽标准硬凑一个）。
    无论结果如何都会留下提案记录，供 agent 侧复核与写回。
    """
    elements = snapshot(page)
    candidates = rank(intent, elements)
    chosen = None
    for cand in candidates:
        if _resolves_uniquely(page, cand.selector):
            chosen = cand
            break

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
