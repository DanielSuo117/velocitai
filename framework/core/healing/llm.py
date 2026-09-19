"""自愈的 LLM 推理后端 —— 启发式规则找不出候选时，让模型看页面结构自己判断。

为什么要有这一层：规则只会按固定策略（testid / id / role+名称 / 文本 / 类名）
拼选择器。碰上「按钮被换成了带图标的 div」「文案从『提交』改成『确认下单』」
这类改版，规则拼不出任何东西，但人一眼能看出来是哪个元素 —— 模型也能。

为什么规则仍然排在前面：有 testid 摆在那儿时，调一次模型既慢又贵，且结论
不会比规则更好。模型只在规则交白卷时才出场。

依赖边界：只用 stdlib urllib，不引 SDK。没有 API key 时静默跳过，
自愈退回纯规则模式 —— 缺这一层不该让任何用例失败。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5"
MAX_ELEMENTS = 60       # 喂给模型的元素上限，超出部分按出现顺序截断
TIMEOUT = 30


def api_key() -> str:
    """按 环境变量 → config.settings 的顺序取 key。取不到返回空串。"""
    k = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if k:
        return k
    try:
        from config.settings import ANTHROPIC_API_KEY  # type: ignore

        return (ANTHROPIC_API_KEY or "").strip()
    except Exception:
        return ""


def available() -> bool:
    return bool(api_key())


def _compact(elements: list) -> list:
    """把快照压成模型够用的最小形态，省 token 也少干扰。"""
    out = []
    for e in elements[:MAX_ELEMENTS]:
        attrs = e.get("attrs") or {}
        item = {"tag": e.get("tag")}
        for k in ("id", "data-testid", "data-test", "data-qa", "name", "type", "placeholder"):
            if attrs.get(k):
                item[k] = attrs[k]
        if e.get("role"):
            item["role"] = e["role"]
        if e.get("name"):
            item["aria"] = e["name"]
        if e.get("text"):
            item["text"] = e["text"][:60]
        cls = [c for c in (e.get("classes") or [])][:4]
        if cls:
            item["class"] = cls
        out.append(item)
    return out


def build_prompt(intent, elements: list, tried: list) -> str:
    return (
        "你是 UI 自动化测试的定位符专家。一个 Playwright 选择器因页面改版失效了，"
        "请根据它原本的意图，从当前页面元素中判断它现在应该指向哪个元素。\n\n"
        f"【失效的选择器】{intent.selector}\n"
        f"【所属页面对象】{intent.page_object or '未知'}\n"
        f"【常量名】{intent.constant}\n"
        f"【代码注释说明】{intent.description or '（无）'}\n"
        f"【上次成功命中时的元素形态】"
        f"标签={intent.tag or '未知'} role={intent.role or '未知'} 可及名称={intent.name or '未知'}\n\n"
        f"【规则已尝试且不可用的候选】{json.dumps(tried, ensure_ascii=False) if tried else '（无）'}\n\n"
        f"【当前页面元素】\n{json.dumps(_compact(elements), ensure_ascii=False, indent=1)}\n\n"
        "要求：\n"
        "1. 只返回 JSON，形如 {\"candidates\": [{\"selector\": \"...\", \"why\": \"...\"}]}，最多 3 个，按把握从高到低。\n"
        "2. 选择器必须是 Playwright 支持的语法（CSS、或 role=xxx[name=\"yyy\"]、或 text=）。\n"
        "3. 优先用 data-testid / id 等稳定锚点；不要使用构建工具生成的哈希类名"
        "（如 css-1a2b3c、sc-bdVaJa），它们下次构建就会变。\n"
        "4. 必须唯一命中一个元素。\n"
        "5. **如果没有任何元素符合原本的意图，返回 {\"candidates\": []}。**"
        "宁可交白卷，也不要勉强给一个看起来像的 —— 顶替错元素会让用例假通过，"
        "那比失败更糟。\n"
    )


def infer(intent, elements: list, tried: list | None = None,
          model: str = DEFAULT_MODEL) -> list:
    """返回模型给出的候选选择器字符串列表。任何失败都返回空列表。"""
    key = api_key()
    if not key or not elements:
        return []
    body = json.dumps({
        "model": model,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": build_prompt(intent, elements, tried or [])}],
    }).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "content-type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            payload = json.loads(r.read().decode("utf-8"))
    except Exception:
        return []       # 网络/鉴权/超时一律静默退回规则模式
    return parse_response(payload)


def parse_response(payload: dict) -> list:
    """从 Messages API 响应里抽出候选选择器。格式不符即返回空列表。"""
    try:
        text = "".join(b.get("text", "") for b in payload.get("content", [])
                       if b.get("type") == "text")
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return []
        data = json.loads(text[start:end + 1])
        out = []
        for c in data.get("candidates", [])[:3]:
            sel = (c.get("selector") or "").strip() if isinstance(c, dict) else ""
            if sel:
                out.append(sel)
        return out
    except Exception:
        return []
