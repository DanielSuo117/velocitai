# 环境 URL 配置
ENVS = {
    "pre": {
        "base_url": "https://pre.example.com",
        "token": "your-pre-environment-token",
    },
    "prod": {
        "base_url": "https://www.example.com",
        "token": "your-prod-environment-token",
    },
}

DEFAULT_ENV = "pre"

# 浏览器配置
HEADLESS = False
SLOW_MO = 500
DEFAULT_TIMEOUT = 15000
DEFAULT_NAVIGATION_TIMEOUT = 15000
VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 900

# 选择器自愈配置
# 产物路径。proposals 供 agent 侧复核与写回，fingerprints 是自愈所依据的
# 「旧有逻辑」—— 定位符上次成功命中时的元素形态。
SELF_HEAL_ARTIFACT = "reports/self-heal/proposals.jsonl"
SELF_HEAL_FINGERPRINTS = "reports/self-heal/fingerprints.json"

# 自愈的 LLM 推理后端（--self-heal=auto 时使用）。
# 留空则自愈退回纯规则模式，不会因此报错。也可改用环境变量 ANTHROPIC_API_KEY。
ANTHROPIC_API_KEY = ""
