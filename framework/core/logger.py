"""统一日志。

自愈会在运行期悄悄改变定位行为，若不留痕，使用者只会看到「用例莫名其妙
通过了」。这里的日志是让那些改变可见的唯一手段。

两种运行方式，两种去处：
- pytest 下不挂自己的 handler，记录向 root 传播，由 pytest 统一收进
  reports/pytest.log（pytest.ini 的 log_file）和失败报告的 Captured log。
- 脚本或 REPL 里单独运行时，自带一个 stderr handler，保证有输出。
"""
from __future__ import annotations

import logging
import os
import sys

_LEVEL = os.environ.get("VELOCITAI_LOG_LEVEL", "INFO").upper()
_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def _under_pytest() -> bool:
    return "pytest" in sys.modules


def get_logger(name: str) -> logging.Logger:
    """取一个已配置好的 logger。重复调用不会叠加 handler。"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, _LEVEL, logging.INFO))
    if not _under_pytest() and not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_FORMAT))
        logger.addHandler(handler)
        logger.propagate = False
    return logger
