# 项目架构

## POM 分层

```
┌─────────────────────────────────────────────┐
│                  tests/ 测试层                │
│  按角色拆分文件：test_<role>_flow.py          │
│  每个测试类继承 Base（或 Role-Base）           │
├─────────────────────────────────────────────┤
│                  pages/ 页面对象层             │
│  BasePage ← LoginPage ← LandingPage ← ...    │
├─────────────────────────────────────────────┤
│                  config/ 配置层                │
│  URL、Token、浏览器参数按环境切换              │
├─────────────────────────────────────────────┤
│                  conftest.py Fixture 层        │
│  browser → context → page → Role-specific base │
└─────────────────────────────────────────────┘
```

## 角色与 context 共享

| 角色 | 基类 | context scope | 起点页面 |
|------|------|--------------|---------|
| （新增角色时在此追加） | | | |

## 决策树

详见 [architecture skill](../.claude/skills/architecture/SKILL.md)
