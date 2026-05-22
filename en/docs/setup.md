# Environment Setup

## Prerequisites

- Python 3.10+
- Node.js 16+ (Playwright dependency)

## Installation Steps

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Configuration

1. Copy `config/settings.example.py` to `config/settings.py`
2. Fill in the URLs and tokens for each environment
3. Configure `--env=pre` or `--env=prod`

## Optional Tools

- **agent-browser**: AI-driven browser DOM exploration tool (saves 82-93% tokens)
  - Install: `agent-browser install`
- **code-review-graph**: AST knowledge graph MCP tool
  - Install: refer to code-review-graph documentation
- **allure**: Test report generation
  - Install: `brew install allure` (macOS)

## Running Tests

```bash
# Run by role
pytest tests/<role>/ --env=<pre|prod>

# Full regression
pytest tests/ --env=<pre|prod>

# View report
allure serve reports/allure-results
```
