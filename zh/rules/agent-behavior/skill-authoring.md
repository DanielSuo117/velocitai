---
paths:
  - "skills/**"
---

# Skill 编写规则

**触发**：新建 / 修改 `skills/**/SKILL.md`。

## P0.5 · Skill 正文不得写入项目专有标识

禁止写死项目专有类名 / URL / DOM 类名 / 业务术语；必须抽象为通用占位符；项目级细节放 `rules/` 或 `docs/`。

❌ 在 skill 里写 "<角色>端 `/<具体路由>/*` 没有 `.<具体类名>`"
✅ skill 写 "用例跳转目标是否脱离门户布局？"

## P0.6 · 适用范围限定在项目实际技术栈

只写项目实际用到的栈（Playwright + pytest），不泛化到未验证的组合。

❌ `description: ... 适用于 Playwright / Selenium / Cypress ...`
✅ `description: Playwright + pytest ...`

## P0.7 · 新建 skill 必须完成四项配套

1. 在 CLAUDE.md 路由表注册
2. 相关 skill 加交叉引用
3. 自检清理项目专有标识
4. 产出新项目事实时同步更新 `docs/`
