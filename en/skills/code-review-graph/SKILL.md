---
name: code-review-graph
description: AST knowledge graph: change review, exploration, debugging, refactoring. Trigger: knowledge graph, code review, impact analysis, blast radius, refactoring.
---

# code-review-graph — Knowledge Graph Toolset

This project connects to an AST-based code knowledge graph via the code-review-graph MCP. When exploring code, **prefer graph tools first**, then fall back to Grep/Glob/Read.

## Token Efficiency Rules (Global)

- **Always** call `get_minimal_context(task="<your task>")` first, then use other graph tools.
- Use `detail_level="minimal"` for all calls; only upgrade to "standard" when necessary.
- Goal: complete the task within 5 tool calls and 800 output tokens.

---

## Workflow 1: Change Review

Risk-aware code review using the knowledge graph.

### Steps

1. Run `detect_changes` to get change analysis with risk scores.
2. Run `get_affected_flows` to find affected execution paths.
3. For high-risk functions, run `query_graph` pattern="tests_for" to check test coverage.
4. Run `get_impact_radius` to understand the scope of impact.
5. For changes without test coverage, suggest specific test cases.

### Output Format

Grouped by risk level (high/medium/low), including: what changed, test coverage status, improvement suggestions, merge recommendation.

---

## Workflow 2: Codebase Exploration

Quickly understand codebase structure using the graph.

### Steps

1. Run `list_graph_stats` to view overall metrics.
2. Run `get_architecture_overview` to understand high-level module structure.
3. Use `list_communities` to find main modules, use `get_community` for details.
4. Use `semantic_search_nodes` to find functions/classes by name or keyword.
5. Use `query_graph`'s `callers_of`, `callees_of`, `imports_of` to trace relationships.
6. Use `list_flows` and `get_flow` to understand execution paths.

### Tips

- Start broad (stats, architecture), then narrow to specific areas.
- `children_of` to see all functions and classes in a file; `find_large_functions` to locate complex code.

---

## Workflow 3: Issue Debugging

Systematically trace and debug issues using the graph.

### Steps

1. Use `semantic_search_nodes` to find code related to the issue.
2. Use `query_graph`'s `callers_of` and `callees_of` to trace call chains.
3. Use `get_flow` to view the complete execution path of suspicious areas.
4. Run `detect_changes` to check if recent changes triggered the issue.
5. Use `get_impact_radius` on suspicious files to see the affected scope.

### Tips

- Check both callers and callees to understand the full context.
- View affected execution flows to find the entry point that triggers the bug.
- Recent changes are the most common source of new issues.

---

## Workflow 4: Safe Refactoring

Plan and execute refactoring confidently using the graph.

### Steps

1. Use `refactor_tool` mode="suggest" to get refactoring suggestions.
2. Use `refactor_tool` mode="dead_code" to find dead code.
3. For renaming, use `refactor_tool` mode="rename" to preview all affected locations.
4. Use `apply_refactor_tool` with refactor_id to apply the rename.
5. After changes, run `detect_changes` to verify impact.

### Safety Checks

- Always preview before applying (rename mode shows a list of edits).
- Check `get_impact_radius` before large-scale refactoring.
- Use `get_affected_flows` to ensure critical paths are not broken.
- `find_large_functions` to identify large functions that need splitting.
