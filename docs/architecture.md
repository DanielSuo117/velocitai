# 项目架构

## POM 分层

```
┌──────────────────────────────────────────────────────┐
│  tests/ 测试层                                        │
│  按角色拆分：test_<role>_flow.py，继承 BaseTest        │
├──────────────────────────────────────────────────────┤
│  pages/ 业务页面对象层                                 │
│  LoginPage / LandingPage ... 一律继承 BasePage         │
│  只放业务页面对象，不放框架代码                          │
├──────────────────────────────────────────────────────┤
│  core/ 框架核心层（公共能力，与业务无关）                 │
│    base/       BasePage · BaseComponent · BaseTest    │
│    healing/    interceptor · engine · runtime         │
│                llm · patcher                          │
│    exceptions.py  logger.py                           │
├──────────────────────────────────────────────────────┤
│  config/ 配置层                                       │
│  URL、Token、浏览器参数、自愈产物路径按环境切换           │
├──────────────────────────────────────────────────────┤
│  conftest.py Fixture 层                               │
│  browser → context → page → Role-specific base        │
└──────────────────────────────────────────────────────┘
```

**PO 原则**：公共能力一律沉到 `core/base/`，业务代码继承即可，不重复实现。
所有定位都经 `BasePage._locate()` 收口到拦截器，因此自愈对业务代码完全透明 ——
页面对象不需要知道自愈存在。

**为什么 core/ 与 pages/ 要分开**：两者混在一起时，页面对象目录里会逐渐堆进
自愈引擎、日志、异常这类谁都不该在写登录页时读到的代码。

## 角色与 context 共享

| 角色 | 基类 | context scope | 起点页面 |
|------|------|--------------|---------|
| （新增角色时在此追加） | | | |

## 决策树

详见 [architecture skill](../skills/architecture/SKILL.md)
