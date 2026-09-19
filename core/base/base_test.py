"""所有测试类的基类 —— 公共的用例生命周期在此封装。

放在 core/ 而不是 tests/ 的理由：它是框架能力，不是某个业务用例。
tests/ 目录应当只有业务用例，读到的人不必先翻框架代码。
"""
from __future__ import annotations

import pytest

from core.logger import get_logger

log = get_logger("velocitai.test")


class BaseTest:
    """业务测试类继承它，获得统一的用例前后置处理。"""

    @pytest.fixture(autouse=True)
    def _case_lifecycle(self, request):
        """每个用例前后各做一次记录。

        故意不在这里塞登录、建数据之类的业务前置 —— 那些属于角色基类
        （见 skills/architecture 的角色分层），放进通用基类会让所有用例
        背上它们并不需要的开销。
        """
        log.info("用例开始：%s", request.node.nodeid)
        yield
        log.info("用例结束：%s", request.node.nodeid)
