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

## P0.8 · SKILL.md 是决策层，细节走渐进式披露

**触发**：新建 skill、或某个 SKILL.md 超过约 150 行时。

SKILL.md 命中即被整体载入。把「只在某个分支才需要」的细节写在正文里，
等于每次都为不走那个分支的场景付出上下文代价 —— 而上下文是有限且昂贵的。

正文只留**做判断所需**的内容：何时适用、决策表/速查表、主干流程、检查清单。
展开性材料（完整代码示例、特殊场景处理、失败对照表、产出模板）移入
`references/<topic>.md`，由正文用一行指路，命中该分支时才读。

❌ 把 SPA 白屏三态判断的 80 行实现细节直接写进 `page-load-assertion/SKILL.md`，
   使每次做页面断言决策都要载入这段只在 SPA 场景用得上的内容

✅ 正文保留四种模式的决策树，白屏检测移入
   `references/blank-screen-detection.md`，正文只留「SPA 且容器可见不代表已挂载
   → 按需展开」一行指路

**注意**：内容移入 `references/` 后相对路径深了一层，原有链接需各加一级
（`../foo/SKILL.md` → `../../foo/SKILL.md`），否则闸门会以 STR004 拦下。
