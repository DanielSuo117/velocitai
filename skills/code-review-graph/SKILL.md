---
name: code-review-graph
description: AST 知识图谱：变更审查、探索、调试、重构。触发：知识图谱、代码审查、影响分析、爆炸半径、重构。
---

# code-review-graph — 知识图谱工具集

本项目通过 code-review-graph MCP 接入了基于 AST 的代码知识图谱。探索代码时**优先使用图谱工具**，再降级到 Grep/Glob/Read。

## Token 效率规则（全局）

- **始终**先调用 `get_minimal_context(task="<你的任务>")`，再使用其他图谱工具。
- 所有调用使用 `detail_level="minimal"`，仅在不够用时升级到 "standard"。
- 目标：5 次工具调用、800 个输出 token 内完成任务。

---

## 工作流一：变更审查

利用知识图谱进行风险感知的代码审查。

### 步骤

1. 运行 `detect_changes` 获取带风险评分的变更分析。
2. 运行 `get_affected_flows` 查找受影响的执行路径。
3. 对高风险函数，运行 `query_graph` pattern="tests_for" 检查测试覆盖。
4. 运行 `get_impact_radius` 理解影响范围。
5. 对未覆盖测试的变更，建议具体的测试用例。

### 输出格式

按风险等级（高/中/低）分组，包含：变更内容、测试覆盖状态、改进建议、合并建议。

---

## 工作流二：代码库探索

利用图谱快速理解代码库结构。

### 步骤

1. 运行 `list_graph_stats` 查看整体指标。
2. 运行 `get_architecture_overview` 了解高层模块结构。
3. 使用 `list_communities` 查找主要模块，用 `get_community` 获取详情。
4. 使用 `semantic_search_nodes` 按名称或关键词查找函数/类。
5. 使用 `query_graph` 的 `callers_of`、`callees_of`、`imports_of` 追踪关系。
6. 使用 `list_flows` 和 `get_flow` 理解执行路径。

### 提示

- 先宏观（统计、架构），再缩小到具体区域。
- `children_of` 查看文件内所有函数和类；`find_large_functions` 定位复杂代码。

---

## 工作流三：问题调试

利用图谱系统化追踪和调试问题。

### 步骤

1. 使用 `semantic_search_nodes` 查找与问题相关的代码。
2. 使用 `query_graph` 的 `callers_of` 和 `callees_of` 追踪调用链。
3. 使用 `get_flow` 查看可疑区域的完整执行路径。
4. 运行 `detect_changes` 检查近期变更是否引发了问题。
5. 对可疑文件使用 `get_impact_radius` 查看受影响范围。

### 提示

- 同时检查调用者和被调用者，理解完整上下文。
- 查看受影响的执行流，找到触发 bug 的入口点。
- 近期变更是新问题最常见的来源。

---

## 工作流四：安全重构

利用图谱自信地规划和执行重构。

### 步骤

1. 使用 `refactor_tool` mode="suggest" 获取重构建议。
2. 使用 `refactor_tool` mode="dead_code" 查找死代码。
3. 重命名时用 `refactor_tool` mode="rename" 预览所有受影响位置。
4. 使用 `apply_refactor_tool` 配合 refactor_id 应用重命名。
5. 变更后运行 `detect_changes` 验证影响。

### 安全检查

- 应用前始终先预览（rename 模式给出编辑清单）。
- 大规模重构前先检查 `get_impact_radius`。
- 使用 `get_affected_flows` 确保关键路径未被破坏。
- `find_large_functions` 识别需要拆分的大函数。
