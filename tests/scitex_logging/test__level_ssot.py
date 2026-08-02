#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Level names must have exactly one definition, and stay in sync with it.

A level's four-character name is not decoration: ``record.levelname``
renders it, and the console formatter keys its colour table on it. When
the names were written out twice — once in ``addLevelName``, once as
``COLORS`` keys — renaming a level in one place left the other silently
unmatched, and the only symptom was a line quietly losing its colour.
Nothing raised, so nothing told you.

These tests fail if the two ever diverge again, in either direction:
a level with no colour, or a colour keyed to a level name that no longer
exists.
"""

import logging

from scitex_logging._formatters import (
    COLOR_NAMES,
    LEVEL_COLOR_NAMES,
    SciTeXConsoleFormatter,
)
from scitex_logging._levels import LEVEL_ABBREVIATIONS


def test_every_registered_level_renders_its_declared_abbreviation():
    # Arrange
    declared = dict(LEVEL_ABBREVIATIONS)

    # Act
    rendered = {level: logging.getLevelName(level) for level in declared}

    # Assert
    assert rendered == declared


def test_every_level_has_a_colour_entry():
    # Arrange
    expected_names = set(LEVEL_ABBREVIATIONS.values())

    # Act
    coloured_names = set(SciTeXConsoleFormatter.COLORS)

    # Assert
    assert coloured_names == expected_names


def test_no_colour_is_keyed_to_an_unknown_level_name():
    # Arrange
    known_names = set(LEVEL_ABBREVIATIONS.values())

    # Act
    orphans = set(SciTeXConsoleFormatter.COLORS) - known_names

    # Assert
    assert orphans == set()


def test_every_level_colour_resolves_through_the_named_palette():
    # Arrange
    palette = set(COLOR_NAMES)

    # Act
    unknown = {name for name in LEVEL_COLOR_NAMES.values() if name not in palette}

    # Assert
    assert unknown == set()


def test_level_colours_are_not_transcribed_escape_sequences():
    # Arrange
    palette_codes = set(COLOR_NAMES.values())

    # Act
    off_palette = set(SciTeXConsoleFormatter.COLORS.values()) - palette_codes

    # Assert
    assert off_palette == set()


def test_success_and_fail_keep_their_documented_numeric_levels():
    # Arrange
    from scitex_logging._levels import FAIL, SUCCESS

    # Act
    ordering = (logging.WARNING, SUCCESS, FAIL, logging.ERROR)

    # Assert
    assert list(ordering) == sorted(ordering)


# EOF
