import pytest


class BaseTest:

    @pytest.fixture(autouse=True)
    def _login_setup(self):
        yield
