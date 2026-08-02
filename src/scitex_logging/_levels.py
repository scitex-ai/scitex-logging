#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Custom log levels for SciTeX."""

import logging

# Custom log levels for success/fail
SUCCESS = 31  # Between WARNING (30) and ERROR (40)
FAIL = 35  # Between WARNING (30) and ERROR (40)

# Standard levels for convenience
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL

# ---------------------------------------------------------------------------
# Single source of truth for the four-character level abbreviations.
#
# These names are not decoration: they are what ``record.levelname``
# renders, which is what the console formatter keys its colours on. They
# were previously written out twice — once in the ``addLevelName`` calls
# below, once as the ``COLORS`` keys in ``_formatters`` — so renaming a
# level in one place left the other silently unmatched, and the only
# symptom was a line quietly losing its colour. Both readers now consume
# THIS dict, so there is nothing to keep in sync by hand.
# ---------------------------------------------------------------------------
LEVEL_ABBREVIATIONS = {
    DEBUG: "DEBU",
    INFO: "INFO",
    SUCCESS: "SUCC",
    WARNING: "WARN",
    FAIL: "FAIL",
    ERROR: "ERRO",
    CRITICAL: "CRIT",
}

for _level, _abbreviation in LEVEL_ABBREVIATIONS.items():
    logging.addLevelName(_level, _abbreviation)

__all__ = [
    "SUCCESS",
    "FAIL",
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
    "LEVEL_ABBREVIATIONS",
]
