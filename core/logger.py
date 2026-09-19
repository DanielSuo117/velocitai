"""统一日志。

自愈会在运行期悄悄改变定位行为，若不留痕，使用者只会看到「用例莫名其妙
通过了」。这里的日志是让那些改变可见的唯一手段。
"""
from __future__ import annotations

import logging
import os
import sys

_LEVEL = os.environ.get("VELOCITAI_LOG_LEVEL", "INFO").upper()
_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def get_logger(name: str) -> logging.Logger:
    """取一个已配置好的 logger。重复调用不会叠加 handler。"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, _LEVEL, logging.INFO))
        logger.propagate = False
    return logger
