#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``getConsole()`` must reach stdout, exactly once, formatted like the logger.

Every test here guards a way this could look correct while being wrong:

- writing to stderr (the bug being fixed — "console" already meant stderr)
- writing to BOTH streams via propagation to root's stderr handler
- printing every line twice after a second ``getConsole()`` call
- diverging in appearance from ``getLogger()``, which would make the
  stream choice visible in the output and defeat the point
"""

import logging

import pytest

from scitex_logging import getConsole, getLogger


@pytest.fixture(autouse=True)
def _isolated_console_name(request):
    """Give each test its own console so handler state cannot leak."""
    name = f"scitex.console.test.{request.node.name}"
    yield name
    logging.getLogger(name).handlers.clear()


def test_success_message_appears_on_stdout(capsys, _isolated_console_name):
    # Arrange
    console = getConsole(_isolated_console_name)

    # Act
    console.success("reached stdout")
    captured = capsys.readouterr()

    # Assert
    assert "reached stdout" in captured.out


def test_success_message_does_not_appear_on_stderr(capsys, _isolated_console_name):
    # Arrange
    console = getConsole(_isolated_console_name)

    # Act
    console.success("reached stdout")
    captured = capsys.readouterr()

    # Assert
    assert "reached stdout" not in captured.err


def test_repeated_getConsole_calls_do_not_duplicate_output(
    capsys, _isolated_console_name
):
    # Arrange
    getConsole(_isolated_console_name)
    console = getConsole(_isolated_console_name)

    # Act
    console.info("emitted once")
    captured = capsys.readouterr()

    # Assert
    assert captured.out.count("emitted once") == 1


def test_repeated_getConsole_calls_keep_exactly_one_handler(_isolated_console_name):
    # Arrange
    getConsole(_isolated_console_name)

    # Act
    console = getConsole(_isolated_console_name)

    # Assert
    assert len(console.handlers) == 1


def test_console_level_surface_matches_the_logger(_isolated_console_name):
    # Arrange
    logger_methods = {m for m in dir(getLogger("probe")) if not m.startswith("_")}

    # Act
    console_methods = {
        m for m in dir(getConsole(_isolated_console_name)) if not m.startswith("_")
    }

    # Assert
    assert logger_methods == console_methods


def test_console_formatting_matches_the_stderr_console_formatting(
    _isolated_console_name,
):
    # Arrange
    #
    # Compare the FORMATTERS on a shared record rather than comparing
    # captured stdout against captured stderr. The stream-capture version
    # of this test passed alone and failed in the full suite: pytest's
    # logging plugin intercepts the stderr logger's records, so `capsys`
    # sees an empty stderr and the comparison fails for a reason that has
    # nothing to do with formatting. Formatting equality is the actual
    # claim, so assert it directly — this also catches the regression
    # that matters, someone handing getConsole a plain logging.Formatter.
    from scitex_logging._handlers import create_console_handler

    record = logging.LogRecord(
        name="probe",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="same shape",
        args=(),
        exc_info=None,
    )
    stdout_handler = getConsole(_isolated_console_name).handlers[0]
    stderr_handler = create_console_handler()

    # Act
    rendered = (
        stdout_handler.formatter.format(record),
        stderr_handler.formatter.format(record),
    )

    # Assert
    assert rendered[0] == rendered[1]


def test_getConsole_returns_a_stdout_handler_not_a_stderr_one(_isolated_console_name):
    # Arrange
    from scitex_logging._handlers import LazyStdoutStreamHandler

    # Act
    console = getConsole(_isolated_console_name)

    # Assert
    assert isinstance(console.handlers[0], LazyStdoutStreamHandler)


# EOF
