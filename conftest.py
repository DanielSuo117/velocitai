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
