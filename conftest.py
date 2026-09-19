import pytest
from playwright.sync_api import sync_playwright

from config.settings import (
    DEFAULT_NAVIGATION_TIMEOUT,
    DEFAULT_TIMEOUT,
    ENVS,
    HEADLESS,
    SLOW_MO,
    VIEWPORT_HEIGHT,
    VIEWPORT_WIDTH,
)


def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        required=True,
        help="Target environment: pre | prod",
    )
    parser.addoption(
        "--self-heal",
        action="store",
        default="off",
        choices=["off", "on", "strict", "auto"],
        help=(
            "选择器自愈：off=关闭（默认）；on=失效时尝试重建定位符，用例继续；"
            "strict=同 on，但只要发生过自愈就让会话以非零码结束，便于 CI 发现漂移；"
            "auto=同 on，并让模型在规则交白卷时推理，且把修复写回 PageObject 源码"
            "（需要 ANTHROPIC_API_KEY；会改动工作区文件）"
        ),
    )


@pytest.fixture(scope="session")
def env(request):
    name = request.config.getoption("--env")
    if name not in ENVS:
        pytest.fail(f"Unknown env '{name}'. Available: {list(ENVS.keys())}")
    return ENVS[name]


@pytest.fixture(scope="session")
def base_url(env):
    return env["base_url"]


@pytest.fixture(scope="session")
def token(env):
    return env["token"]


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance):
    browser = playwright_instance.chromium.launch(
        headless=HEADLESS,
        slow_mo=SLOW_MO,
        args=["--incognito"],
    )
    yield browser
    browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(
        viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
    )
    new_page = context.new_page()
    new_page.set_default_timeout(DEFAULT_TIMEOUT)
    new_page.set_default_navigation_timeout(DEFAULT_NAVIGATION_TIMEOUT)
    yield new_page
    new_page.close()
    context.close()


@pytest.fixture(scope="class")
def class_page(browser, request):
    context = browser.new_context(
        viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
    )
    new_page = context.new_page()
    new_page.set_default_timeout(DEFAULT_TIMEOUT)
    new_page.set_default_navigation_timeout(DEFAULT_NAVIGATION_TIMEOUT)
    request.cls.page = new_page
    yield new_page
    new_page.close()
    context.close()


def pytest_configure(config):
    """按需开启自愈。默认关闭 —— 它会改变「失败」的含义，不能悄悄生效。"""
    if config.getoption("--self-heal") == "off":
        return
    from pages.base_page import BasePage

    BasePage.self_heal_enabled = True
    if config.getoption("--self-heal") == "auto":
        BasePage.self_heal_use_llm = True
        BasePage.self_heal_patch = True
    try:
        from config.settings import SELF_HEAL_ARTIFACT, SELF_HEAL_FINGERPRINTS

        BasePage.heal_artifact = SELF_HEAL_ARTIFACT
        BasePage.heal_fingerprints = SELF_HEAL_FINGERPRINTS
    except ImportError:
        pass      # 旧配置文件没有这两项时沿用类默认值


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """自愈过的用例不能被当成干净通过，必须在报告里显式点名。"""
    from pages import heal_runtime

    if not heal_runtime.HEALED:
        return
    terminalreporter.section("选择器自愈", sep="=", bold=True)
    for h in heal_runtime.HEALED:
        terminalreporter.write_line(
            f"  {h['page_object']}.{h['constant']}: {h['old']} -> {h['new']} "
            f"（{h['strategy']}，置信 {h['confidence']}）"
        )
    if heal_runtime.PATCHED:
        terminalreporter.section("源码已被改写", sep="=", bold=True)
        for h in heal_runtime.PATCHED:
            flag = "已写回" if h["ok"] else "写回失败"
            terminalreporter.write_line(
                f"  [{flag}] {h['file']}::{h['constant']}  {h['old']} -> {h['new']}"
            )
        terminalreporter.write_line(
            "  原文件已备份为同名 .heal-bak。请 review 后再提交 —— "
            "写回同样要过落库闸门。"
        )
        terminalreporter.write_line(
            f"  共 {len(heal_runtime.HEALED)} 处定位符已修复，其中 "
            f"{sum(1 for h in heal_runtime.PATCHED if h['ok'])} 处已写回源码。"
        )
    else:
        terminalreporter.write_line(
            f"  共 {len(heal_runtime.HEALED)} 处定位符已在运行期临时修复；"
            f"源码尚未改动，写回需经 selector-self-heal skill 并通过落库闸门。"
        )


def pytest_sessionfinish(session, exitstatus):
    """strict 模式下，发生过自愈即以非零码结束，避免定位符漂移被沉默吞掉。"""
    from pages import heal_runtime

    if heal_runtime.HEALED and session.config.getoption("--self-heal") == "strict":
        session.exitstatus = 1
