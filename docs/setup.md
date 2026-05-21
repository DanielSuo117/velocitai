# 环境搭建

## 前置条件

- Python 3.10+
- Node.js 16+（Playwright 依赖）

## 安装步骤

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## 配置

1. 复制 `config/settings.example.py` 为 `config/settings.py`
2. 填入各环境的 URL 和 Token
3. 配置 `--env=pre` 或 `--env=prod`

## 可选工具

- **agent-browser**：AI 驱动的浏览器 DOM 探索工具（节省 82-93% token）
  - 安装：`agent-browser install`
- **code-review-graph**：AST 知识图谱 MCP 工具
  - 安装：参考 code-review-graph 文档
- **allure**：测试报告生成
  - 安装：`brew install allure`（macOS）

## 运行测试

```bash
# 按角色运行
pytest tests/<role>/ --env=<pre|prod>

# 全量回归
pytest tests/ --env=<pre|prod>

# 查看报告
allure serve reports/allure-results
```
