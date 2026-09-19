# 项目架构

## 顶层：代码与 harness 分开存放

```
velocitai/
├── framework/          代码部分 —— Python UI 自动化框架
│   ├── core/           框架核心（base · healing · exceptions · logger）
│   ├── pages/          业务页面对象
│   ├── tests/          业务用例
│   ├── config/         环境与浏览器配置
│   └── conftest.py     fixture 层
│
├── skills/             harness —— agent 操作方法论
├── rules/              harness —— 强制约束
├── docs/               harness —— 项目事实
├── hooks/              harness —— 闸门接线
├── scripts/gate/       harness —— 落库校验实现
└── .claude-plugin/     harness —— 插件清单
```

**为什么 harness 留在仓库根而不是收进子目录**：Claude Code 以「根级
`.claude-plugin/` 目录或 `skills/<name>/SKILL.md`」作为识别插件的标志，
把 `skills/` 挪进子目录会让插件无法被发现。代码没有这个约束，因此收进
`framework/`。

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
所有定位都经 `BasePage._act()` / `_locate()` 收口到拦截器，因此自愈对业务代码
完全透明 —— 页面对象不需要知道自愈存在。定位**作用域**同样收口在一处
（`scope_root()`）：`BaseComponent` 只覆盖它即可把组件内的定位全部限制在 root 之内。
曾经组件覆盖的是 `_locate()`，而 click/fill 走的是 `_act()`，作用域因此形同虚设。

**为什么 core/ 与 pages/ 要分开**：两者混在一起时，页面对象目录里会逐渐堆进
自愈引擎、日志、异常这类谁都不该在写登录页时读到的代码。

## 角色与 context 共享

| 角色 | 基类 | context scope | 起点页面 |
|------|------|--------------|---------|
| （新增角色时在此追加） | | | |

## 决策树

详见 [architecture skill](../skills/architecture/SKILL.md)
