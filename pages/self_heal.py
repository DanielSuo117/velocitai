"""选择器自愈引擎 —— 纯逻辑层，不导入 Playwright，可脱离浏览器单测。

职责边界：
- 本模块只做一件事：根据「定位符原本的意图」+「当前 DOM 快照」生成并排序候选定位符。
- 抓快照、执行候选、判可见性由 BasePage 负责（那里才有 Playwright）。
- 本模块永不改写源码。写回由 agent 侧 skill 完成，且必须过落库闸门。

安全不变量（整个机制的地基）：
    自愈只允许修复「定位」，绝不允许把真失败变成假通过。
真正的危险不是修不好，而是候选匹配到了另一个恰好存在的元素 —— 用例照样绿，
功能其实已经坏了。误报只是吵，假通过是骗。因此候选必须同时满足三条：
意图指纹一致、全页唯一命中、元素可见。任一不满足即放弃自愈，按原样失败。
"""
from __future__ import annotations

import dataclasses
import json
import re
import time

# 与落库闸门 GEN003 同源的判据：构建工具生成的哈希段必然含数字
# （css-1a2b3c / sc-bdVaJa / _abc123），而人写的标识符每段多为纯字母。
# 哈希段下次构建就会变，拿它做定位符等于制造下一次失效。
# 定向匹配已知构建工具的产物，而不是「含数字就算哈希」—— 后者会把 step2 / tab1
# 这类正常 id 误杀，白白丢掉可用锚点。误判为哈希只是少一个候选，误判为稳定
# 则会拼出下次构建就失效的选择器，两种代价不对称，故宁可漏判。
_HASHY_RE = re.compile(
    r"^(?:"
    r"sc-[A-Za-z]{4,}"                                  # styled-components: sc-bdVaJa
    r"|css-(?=[0-9a-z]*[0-9])[0-9a-z]{5,}"              # Emotion: css-1a2b3c
    r"|[A-Za-z]+_(?=[0-9a-z]*[0-9])[0-9a-z]{4,}"        # CSS Modules: Button_a1b2c3
    r"|[0-9a-f]{8,}"                                    # 裸十六进制指纹
    r")$", re.I)
_TESTID_ATTRS = ("data-testid", "data-test-id", "data-test", "data-qa", "data-cy")

MIN_CONFIDENCE = 70          # 低于此分不予采纳，宁可失败也不猜
STRONG_CONFIDENCE = 85       # 无历史指纹时，只接受强锚点


def _is_hashy(token: str) -> bool:
    """该标识符是否像构建工具生成的哈希（下次构建即失效）。"""
    return bool(token) and bool(_HASHY_RE.match(token))


def _norm(text: str | None) -> str:
    """归一化可见文本：压空白、去首尾、转小写，便于跨渲染差异比对。"""
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def _css_escape(value: str) -> str:
    """转义属性值里的引号，避免拼出的选择器语法破损。"""
    return value.replace("\\", "\\\\").replace('"', '\\"')


@dataclasses.dataclass(frozen=True)
class Intent:
    """一个定位符「本来想选中什么」。

    来源是 PageObject 类顶部的常量及其注释，例如：
        LOGIN_BUTTON = "#login-btn"   # P0: 登录按钮
    constant/description 提供语义，tag/role/name 是上次成功命中时留下的指纹。
    指纹缺失时判定会自动收紧（见 rank）。
    """
    constant: str
    selector: str
    description: str = ""
    page_object: str = ""
    tag: str | None = None
    role: str | None = None
    name: str | None = None

    def has_fingerprint(self) -> bool:
        return any((self.tag, self.role, self.name))


@dataclasses.dataclass(frozen=True)
class Candidate:
    selector: str
    strategy: str
    confidence: int
    rationale: str


def _matches_fingerprint(intent: Intent, el: dict) -> bool:
    """元素是否与「原来那个元素」是同一类东西。

    这是防假通过的第一道闸：没有它，一个 role=button 的候选可以顶替
    另一个完全无关的按钮，用例照绿。
    """
    if intent.tag and _norm(el.get("tag")) != _norm(intent.tag):
        return False
    if intent.role and _norm(el.get("role")) != _norm(intent.role):
        return False
    if intent.name:
        want = _norm(intent.name)
        if want and want not in (_norm(el.get("name")), _norm(el.get("text"))):
            return False
    return True


def _describe_hit(intent: Intent, el: dict) -> bool:
    """无指纹时的兜底语义比对：常量注释里的说明是否与元素文本吻合。"""
    desc = _norm(intent.description)
    if not desc:
        return False
    return desc in _norm(el.get("text")) or desc in _norm(el.get("name"))


def _candidates_for(el: dict) -> list[Candidate]:
    """为单个元素生成它所有可用的定位方式，按稳定性打分。"""
    out: list[Candidate] = []
    attrs = el.get("attrs") or {}
    tag = el.get("tag") or "*"

    for a in _TESTID_ATTRS:
        v = attrs.get(a)
        if v and not _is_hashy(v):
            out.append(Candidate(f'[{a}="{_css_escape(v)}"]', "testid", 95,
                                 f"专用测试属性 {a}，最不易随样式改动而失效"))

    el_id = attrs.get("id")
    if el_id and not _is_hashy(el_id):
        out.append(Candidate(f"#{el_id}", "id", 90, "元素 id，页面内唯一且语义稳定"))

    role, name = el.get("role"), el.get("name")
    if role and name:
        out.append(Candidate(f'{tag}[role="{_css_escape(role)}"]', "role-name", 85,
                             f"ARIA role={role} + 可及名称「{name}」，跟随语义而非样式"))

    text = (el.get("text") or "").strip()
    if text and len(text) <= 40 and tag in ("button", "a", "label", "span", "li", "td", "th"):
        out.append(Candidate(f'{tag}:has-text("{_css_escape(text)}")', "text", 75,
                             f"可见文本「{text}」，文案改动会失效但语义直观"))

    stable = [c for c in (el.get("classes") or []) if c and not _is_hashy(c)]
    if stable:
        out.append(Candidate(tag + "".join(f".{c}" for c in stable[:2]), "stable-class", 60,
                             "非哈希类名组合，样式重构时可能失效"))
    return out


def rank(intent: Intent, elements: list[dict],
         min_confidence: int = MIN_CONFIDENCE) -> list[Candidate]:
    """产出可采纳的候选定位符，最优先者在前。

    唯一性在这里就强制：一个候选只要在快照里命中多于一个元素就直接丢弃，
    因为「唯一命中」是防假通过的第二道闸，留到执行期再判等于把风险后移。
    """
    fingerprinted = intent.has_fingerprint()
    pool = []
    for el in elements:
        if fingerprinted:
            if not _matches_fingerprint(intent, el):
                continue
        elif not _describe_hit(intent, el):
            # 既无指纹又对不上说明 —— 没有任何依据认定它就是原来那个元素
            continue
        pool.append(el)

    floor = min_confidence if fingerprinted else max(min_confidence, STRONG_CONFIDENCE)
    counts: dict[str, int] = {}
    produced: list[tuple[Candidate, dict]] = []
    for el in pool:
        for cand in _candidates_for(el):
            if cand.confidence < floor:
                continue
            produced.append((cand, el))
    for cand, _ in produced:
        counts[cand.selector] = counts.get(cand.selector, 0) + 1

    seen: set[str] = set()
    result: list[Candidate] = []
    for cand, _ in sorted(produced, key=lambda p: -p[0].confidence):
        if counts[cand.selector] != 1 or cand.selector in seen:
            continue      # 命中多个元素 = 不唯一 = 不可用
        seen.add(cand.selector)
        result.append(cand)
    return result


@dataclasses.dataclass
class HealProposal:
    """一次自愈尝试的完整记录，供 agent 侧 skill 审阅并写回。"""
    intent: Intent
    candidates: list[Candidate]
    chosen: Candidate | None
    url: str = ""
    test_id: str = ""
    created_at: float = dataclasses.field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "intent": dataclasses.asdict(self.intent),
            "candidates": [dataclasses.asdict(c) for c in self.candidates],
            "chosen": dataclasses.asdict(self.chosen) if self.chosen else None,
            "url": self.url,
            "test_id": self.test_id,
            "created_at": self.created_at,
        }


def record(proposal: HealProposal, path: str) -> bool:
    """把提案追加为 JSONL。写失败绝不能影响测试结论，故一律吞掉异常。"""
    try:
        import os
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(proposal.to_dict(), ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


_CONST_RE_TMPL = r'^\s*([A-Z][A-Z0-9_]*)\s*=\s*(["\'])(?P<val>.*?)\2\s*(?:#\s*(?P<note>.*))?$'


def intent_from_source(source: str, selector: str, page_object: str = "",
                       fingerprint: dict | None = None) -> Intent:
    """从 PageObject 源码里还原某个失效选择器「本来想选中什么」。

    依据本项目的 PageObject 骨架约定：定位符是类顶部常量，且注释即语义说明——
        LOGIN_BUTTON = "#login-btn"   # P0: 登录按钮
    常量名与注释合起来，就是这个定位符的意图；fingerprint 则是它上次成功命中
    时留下的形态。两者缺一时判定会自动收紧（见 rank）。
    """
    const, note = "", ""
    for line in source.splitlines():
        m = re.match(_CONST_RE_TMPL, line)
        if m and m.group("val") == selector:
            const = m.group(1)
            note = (m.group("note") or "").strip()
            break
    # 去掉优先级前缀 P0: / P3： ，只留人写的语义说明
    note = re.sub(r"^P[0-5]\s*[:：]\s*", "", note).strip()
    fp = fingerprint or {}
    return Intent(
        constant=const or "<unknown>",
        selector=selector,
        description=note,
        page_object=page_object,
        tag=fp.get("tag"),
        role=fp.get("role"),
        name=fp.get("name"),
    )
