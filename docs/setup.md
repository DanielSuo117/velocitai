# 环境搭建

## 前置条件

- Python 3.10+
- Node.js 16+（Playwright 依赖）

## 安装步骤

```bash
python -m venv .venv
source .venv/bin/activate   # Windows：source .venv/Scripts/activate（Git Bash）或 .venv\Scripts\Activate.ps1（PowerShell）
pip install -r requirements.txt
playwright install chromium
```

## 配置

1. 复制 `framework/config/settings.example.py` 为 `framework/config/settings.py`
2. 填入各环境的 URL 和 Token
3. 配置 `--env=pre` 或 `--env=prod`

## 新建角色

```bash
python scripts/scaffold_role.py teacher --label 教师
```

生成 `framework/tests/teacher/`：角色基类 `TeacherBaseTest`（class 级登录一次，用例共享 `self.teacher_page`）和主流程文件 `test_teacher_flow.py`。之后按 `teacher_base_test.py` 里的 `LOGIN_PATH` 调整登录方式，并在 `docs/architecture.md` 的角色表登记。页面对象放 `framework/pages/`，测试数据放 `framework/data/<role>/`。

## 可选工具

- **agent-browser**：AI 驱动的浏览器 DOM 探索工具（节省 82-93% token）
  - 安装：`agent-browser install`
- **code-review-graph**：AST 知识图谱 MCP 工具
  - 安装：参考 code-review-graph 文档
- **allure**：测试报告生成
  - 安装：`brew install allure`（macOS）；`scoop install allure` 或 `npm i -g allure-commandline`（Windows）

## 运行测试

```bash
# 按角色运行
pytest framework/tests/<role>/ --env=<pre|prod>

# 全量回归
pytest framework/tests/ --env=<pre|prod>

# 查看报告
allure serve reports/allure-results
```
