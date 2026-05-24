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
