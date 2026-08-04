#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for custom log levels."""

import logging

import pytest

from scitex_logging._formatters import (
    COLOR_NAMES,
    LEVEL_COLOR_NAMES,
    SciTeXConsoleFormatter,
)
from scitex_logging._levels import (
    CRITICAL,
    DEBUG,
    ERROR,
    FAIL,
    INFO,
    LEVEL_ABBREVIATIONS,
    SUCCESS,
    WARNING,
)


class TestLogLevels:
    """Test custom log level definitions."""

    def test_success_level_value_equals_31(self):
        """SUCCESS log-level integer is 31."""
        # Arrange
        expected = 31
        # Act
        actual = SUCCESS
        # Assert
        assert actual == expected

    def test_success_level_value_above_warning(self):
        """SUCCESS log-level integer is strictly greater than logging.WARNING."""
        # Arrange
        boundary = logging.WARNING
        # Act
        observed = SUCCESS
        # Assert
        assert observed > boundary

    def test_success_level_value_below_error(self):
        """SUCCESS log-level integer is strictly less than logging.ERROR."""
        # Arrange
        boundary = logging.ERROR
        # Act
        observed = SUCCESS
        # Assert
        assert observed < boundary

    def test_fail_level_value_equals_35(self):
        """FAIL log-level integer is 35."""
        # Arrange
        expected = 35
        # Act
        actual = FAIL
        # Assert
        assert actual == expected

    def test_fail_level_value_above_warning(self):
        """FAIL log-level integer is strictly greater than logging.WARNING."""
        # Arrange
        boundary = logging.WARNING
        # Act
        observed = FAIL
        # Assert
        assert observed > boundary

    def test_fail_level_value_below_error(self):
        """FAIL log-level integer is strictly less than logging.ERROR."""
        # Arrange
        boundary = logging.ERROR
        # Act
        observed = FAIL
        # Assert
        assert observed < boundary

    def test_success_level_name_is_succ(self):
        """SUCCESS level reports its level-name as `SUCC`."""
        # Arrange
        level_int = SUCCESS
        # Act
        name = logging.getLevelName(level_int)
        # Assert
        assert name == "SUCC"

    def test_fail_level_name_is_fail(self):
        """FAIL level reports its level-name as `FAIL`."""
        # Arrange
        level_int = FAIL
        # Act
        name = logging.getLevelName(level_int)
        # Assert
        assert name == "FAIL"

    def test_debug_level_name_is_debu(self):
        """DEBUG level reports its level-name as `DEBU`."""
        # Arrange
        level_int = DEBUG
        # Act
        name = logging.getLevelName(level_int)
        # Assert
        assert name == "DEBU"

    def test_info_level_name_is_info(self):
        """INFO level reports its level-name as `INFO`."""
        # Arrange
        level_int = INFO
        # Act
        name = logging.getLevelName(level_int)
        # Assert
        assert name == "INFO"

    def test_warning_level_name_is_warn(self):
        """WARNING level reports its level-name as `WARN`."""
        # Arrange
        level_int = WARNING
        # Act
        name = logging.getLevelName(level_int)
        # Assert
        assert name == "WARN"

    def test_error_level_name_is_erro(self):
        """ERROR level reports its level-name as `ERRO`."""
        # Arrange
        level_int = ERROR
        # Act
        name = logging.getLevelName(level_int)
        # Assert
        assert name == "ERRO"

    def test_critical_level_name_is_crit(self):
        """CRITICAL level reports its level-name as `CRIT`."""
        # Arrange
        level_int = CRITICAL
        # Act
        name = logging.getLevelName(level_int)
        # Assert
        assert name == "CRIT"

    def test_debug_level_value_matches_stdlib(self):
        """DEBUG re-export equals logging.DEBUG."""
        # Arrange
        expected = logging.DEBUG
        # Act
        actual = DEBUG
        # Assert
        assert actual == expected

    def test_info_level_value_matches_stdlib(self):
        """INFO re-export equals logging.INFO."""
        # Arrange
        expected = logging.INFO
        # Act
        actual = INFO
        # Assert
        assert actual == expected

    def test_warning_level_value_matches_stdlib(self):
        """WARNING re-export equals logging.WARNING."""
        # Arrange
        expected = logging.WARNING
        # Act
        actual = WARNING
        # Assert
        assert actual == expected

    def test_error_level_value_matches_stdlib(self):
        """ERROR re-export equals logging.ERROR."""
        # Arrange
        expected = logging.ERROR
        # Act
        actual = ERROR
        # Assert
        assert actual == expected

    def test_critical_level_value_matches_stdlib(self):
        """CRITICAL re-export equals logging.CRITICAL."""
        # Arrange
        expected = logging.CRITICAL
        # Act
        actual = CRITICAL
        # Assert
        assert actual == expected

    def test_level_ordering_chain_is_monotonic(self):
        """All log-levels are monotonically increasing in priority."""
        # Arrange
        chain = [DEBUG, INFO, WARNING, SUCCESS, FAIL, ERROR, CRITICAL]
        # Act
        is_monotonic = all(chain[i] < chain[i + 1] for i in range(len(chain) - 1))
        # Assert
        assert is_monotonic is True


class TestLevelNameSingleSourceOfTruth:
    """Level names must have exactly one definition, and stay in sync with it.

    A level's four-character name is not decoration: ``record.levelname``
    renders it, and the console formatter keys its colour table on it. When
    the names were written out twice — once in ``addLevelName``, once as
    ``COLORS`` keys — renaming a level in one place left the other silently
    unmatched, and the only symptom was a line quietly losing its colour.
    Nothing raised, so nothing told you.

    These fail if the two ever diverge again, in either direction: a level
    with no colour, or a colour keyed to a level name that no longer exists.
    """

    def test_every_registered_level_renders_its_declared_abbreviation(self):
        # Arrange
        declared = dict(LEVEL_ABBREVIATIONS)
        # Act
        rendered = {level: logging.getLevelName(level) for level in declared}
        # Assert
        assert rendered == declared

    def test_every_level_has_a_colour_entry(self):
        # Arrange
        expected_names = set(LEVEL_ABBREVIATIONS.values())
        # Act
        coloured_names = set(SciTeXConsoleFormatter.COLORS)
        # Assert
        assert coloured_names == expected_names

    def test_no_colour_is_keyed_to_an_unknown_level_name(self):
        # Arrange
        known_names = set(LEVEL_ABBREVIATIONS.values())
        # Act
        orphans = set(SciTeXConsoleFormatter.COLORS) - known_names
        # Assert
        assert orphans == set()

    def test_every_level_colour_resolves_through_the_named_palette(self):
        # Arrange
        palette = set(COLOR_NAMES)
        # Act
        unknown = {n for n in LEVEL_COLOR_NAMES.values() if n not in palette}
        # Assert
        assert unknown == set()

    def test_level_colours_are_not_transcribed_escape_sequences(self):
        # Arrange
        palette_codes = set(COLOR_NAMES.values())
        # Act
        off_palette = set(SciTeXConsoleFormatter.COLORS.values()) - palette_codes
        # Assert
        assert off_palette == set()

    def test_success_and_fail_keep_their_documented_numeric_levels(self):
        # Arrange
        ordering = (logging.WARNING, SUCCESS, FAIL, logging.ERROR)
        # Act
        in_order = list(ordering) == sorted(ordering)
        # Assert
        assert in_order is True


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: /home/ywatanabe/proj/scitex-code/src/scitex/logging/_levels.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# """Custom log levels for SciTeX."""
#
# import logging
#
# # Custom log levels for success/fail
# SUCCESS = 31  # Between WARNING (30) and ERROR (40)
# FAIL = 35  # Between WARNING (30) and ERROR (40)
#
# # Add custom levels to logging module with 4-character abbreviations
# logging.addLevelName(SUCCESS, "SUCC")
# logging.addLevelName(FAIL, "FAIL")
# logging.addLevelName(logging.DEBUG, "DEBU")
# logging.addLevelName(logging.INFO, "INFO")
# logging.addLevelName(logging.WARNING, "WARN")
# logging.addLevelName(logging.ERROR, "ERRO")
# logging.addLevelName(logging.CRITICAL, "CRIT")
#
# # Standard levels for convenience
# DEBUG = logging.DEBUG
# INFO = logging.INFO
# WARNING = logging.WARNING
# ERROR = logging.ERROR
# CRITICAL = logging.CRITICAL
#
# __all__ = ["SUCCESS", "FAIL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# --------------------------------------------------------------------------------
# End of Source Code from: /home/ywatanabe/proj/scitex-code/src/scitex/logging/_levels.py
# --------------------------------------------------------------------------------
