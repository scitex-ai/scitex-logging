"""Canonical isolated stderr diagnostics for embedded protocol producers."""

from __future__ import annotations

import logging
import threading

from ._handlers import create_console_handler

_DIAGNOSTICS = {}
_LOCK = threading.RLock()


def getDiagnostic(name=None, level=None):
    """Return one non-propagating SciTeX stderr logger.

    Unlike getLogger, this channel never inherits a caller's stdout handler.
    Formatting and thresholds still use the canonical SciTeX implementation.
    Repeated acquisition preserves an explicit level and never stacks handlers.
    """
    with _LOCK:
        name = name or "scitex.diagnostic"
        if not isinstance(name, str):
            raise TypeError("A logger name must be a string")
        logger = _DIAGNOSTICS.get(name)
        if logger is None:
            logger = logging.getLogger(name)
            logger.propagate = False
            logger.addHandler(create_console_handler(logging.NOTSET))
            _DIAGNOSTICS[name] = logger
        if level is not None:
            logger.setLevel(level)
        return logger
