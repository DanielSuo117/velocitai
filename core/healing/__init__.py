"""选择器自愈。

模块职责：
- engine      纯逻辑：意图 + DOM 快照 → 候选定位符（不依赖 Playwright）
- runtime     运行时：抓快照、实跑验证、记录提案、指纹存取
- interceptor 拦截器：定位失败时的统一入口，BasePage 经此接入
- llm         模型推理后端，规则交白卷时出场
- patcher     把修复写回 PageObject 源码
"""
