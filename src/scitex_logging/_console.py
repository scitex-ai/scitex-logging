#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""``getConsole()`` — a logger whose output goes to stdout.

``getLogger()`` writes to stderr. That is the right default for
diagnostics: stderr does not corrupt a pipeline, and a program's
complaints should not land in a file the user is building.

It is the wrong default for output the user asked to see. A result, a
progress line, a success message they are reading on purpose — that
belongs on stdout, where it can be piped, redirected, and consumed by
another program. Sending it to stderr makes it invisible to `> out.txt`
and mixes it into error streams that other tools scrape.

So this module adds the second destination rather than changing the
first::

    from scitex_logging import getConsole

    console = getConsole()
    console.success("shown on stdout, formatted exactly like the logger")

Formatting is deliberately identical to the logger's — the same
``SciTeXConsoleFormatter``, the same ``SUCC`` / ``FAIL`` level names. A
line does not change appearance because it changed stream; only its
destination differs, which is the whole point of having two.

The returned object IS a logger (``SciTeXLogger``), so the full level
surface is available: ``debug`` / ``info`` / ``success`` / ``warning`` /
``fail`` / ``error`` / ``critical``, including the ``indent`` / ``sep`` /
``c`` / ``pprint`` keyword arguments.
"""

from __future__ import annotations

import logging

from ._handlers import LazyStdoutStreamHandler, create_stdout_handler
from ._print_capture import PrintCapture

# Distinct from any application logger name, so attaching a stdout
# handler here can never add stdout output to somebody's existing logger.
DEFAULT_CONSOLE_NAME = "scitex.console"


def getConsole(name: str | None = None, level: int = logging.INFO):
    """Return a logger that writes to **stdout**.

    Args:
        name: Logger name. Defaults to ``scitex.console``. Pass a name to
            keep an independent console (its own level) for a subsystem.
        level: Threshold for both the logger and its stdout handler.

    Returns:
        The ``SciTeXLogger`` for *name*, carrying exactly one stdout
        handler.

    Calling this repeatedly with the same name returns the same logger
    and does **not** stack handlers — a second handler would print every
    line twice, which is the classic logging bug this guards against.

    ``propagate`` is disabled: without that, records would also travel to
    the root logger and be emitted a second time on *stderr* by the
    handler :func:`scitex_logging.configure` installs there. The caller
    asked for stdout, so stdout is where the line goes — once.
    """
    console = logging.getLogger(name or DEFAULT_CONSOLE_NAME)
    console.setLevel(level)

    # Ancestors (including root) carry stderr handlers. Propagating would
    # duplicate every line onto the stream the caller explicitly did not
    # ask for.
    console.propagate = False

    for handler in console.handlers:
        if isinstance(handler, LazyStdoutStreamHandler):
            handler.setLevel(level)
            break
    else:
        console.addHandler(create_stdout_handler(level))

    return console


class PlainConsole:
    """A stdout writer with the console call surface but no level prefix.

    Where output IS the product — a hook's protocol frame, a path a shell
    consumes, a probe verdict a build script greps — an ``INFO: `` prefix
    would corrupt the payload rather than clarify it. ``PlainConsole``
    writes the message verbatim to stdout (plus newline), so protocol
    frames keep byte-exact output while sharing the ``getConsole``
    discovery pattern with levelled output.

    This is NOT a general print hatch: human-facing status and diagnostics
    belong on ``getLogger``/``getConsole``, which carry the level, the
    aligned prefix and the searchable record the mandate exists for.
    """

    def __init__(self, name: str | None = None) -> None:
        self._name = name or DEFAULT_CONSOLE_NAME

    def emit(self, message: str) -> None:
        """Write a result to current stdout without capturing it as a log."""
        import sys

        stream = sys.stdout
        # Print capture owns diagnostic duplication. A plain result must
        # bypass only our wrappers, while respecting the current redirected
        # stream and any foreign wrapper's own write/flush behavior.
        while isinstance(stream, PrintCapture):
            stream = stream.original_stdout
        stream.write(f"{message}\n")
        stream.flush()

    # Alias parity with the logger surface — all unprefixed.
    print = emit
    write = emit


def getPlainConsole(name: str | None = None) -> PlainConsole:
    """Return a prefix-free stdout writer for protocol-frame output.

    Args:
        name: Retained for call-site symmetry with :func:`getConsole`;
            carried on the object but otherwise unused.

    Returns:
        A :class:`PlainConsole` writing verbatim lines to stdout.
    """
    return PlainConsole(name)


__all__ = ["getConsole", "getPlainConsole", "PlainConsole", "DEFAULT_CONSOLE_NAME"]

# EOF
