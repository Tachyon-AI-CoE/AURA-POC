"""Logging configuration and helper utilities."""

import logging
import os
import time


_DEFAULT_FMT = "%(levelname)s %(asctime)sZ [%(name)s] %(message)s"


class _UTCFormatter(logging.Formatter):
    """Force UTC timestamps with trailing 'Z'."""

    converter = time.gmtime


def setup_logging():
    """Idempotent root logger setup.

    Respects LOG_LEVEL environment variable (default: INFO).

    Returns:
        Configured root logger.
    """
    level = os.getenv("LOG_LEVEL", "INFO").upper()

    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_UTCFormatter(_DEFAULT_FMT))
        root.addHandler(handler)

    root.setLevel(level)
    return root
