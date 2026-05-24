from playwright.sync_api import Page


class BasePage:

    def __init__(self, page: Page):
        self.page = page

    def click(self, selector: str, **kwargs):
        self.page.locator(selector).click(**kwargs)

    def fill(self, selector: str, value: str, **kwargs):
        self.page.locator(selector).fill(value, **kwargs)

    def get_text(self, selector: str) -> str:
        return self.page.locator(selector).inner_text()

    def is_visible(self, selector: str, timeout: int | None = None) -> bool:
        try:
            kwargs = {"timeout": timeout} if timeout is not None else {}
            self.page.locator(selector).wait_for(state="visible", **kwargs)
            return True
        except Exception:
            return False

    def wait_for_element(self, selector: str, state: str = "visible", timeout: int = 15000):
        self.page.locator(selector).wait_for(state=state, timeout=timeout)

    def get_element_count(self, selector: str) -> int:
        return self.page.locator(selector).count()

    def is_page_loaded(self) -> bool:
        raise NotImplementedError("Subclasses must implement is_page_loaded()")
