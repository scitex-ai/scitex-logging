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
import threading
from typing import TextIO

from ._handlers import LazyStdoutStreamHandler, create_stdout_handler
from ._logger import SciTeXLogger
from ._print_capture import PrintCapture

# Console objects are cached separately from diagnostic logger names.
DEFAULT_CONSOLE_NAME = "scitex.console"
_CONSOLES: dict[str, SciTeXLogger] = {}
_CONSOLE_LOCK = threading.RLock()


class _ConsoleLogger(SciTeXLogger):
    """An independent stdout logger with live inherited thresholds."""

    def isEnabledFor(self, level):
        # These loggers deliberately do not belong to loggerDict. The
        # manager cannot invalidate their usual Logger._cache when root's
        # level or logging.disable changes, so read both values directly.
        return (
            not self.disabled
            and self.manager.disable < level
            and level >= self.getEffectiveLevel()
        )


def getConsole(name: str | None = None, level: int | None = None):
    """Return a logger that writes to **stdout**.

    Args:
        name: Logger name. Defaults to ``scitex.console``. Pass a name to
            keep an independent console (its own level) for a subsystem.
        level: Explicit threshold, or inherit the global/root threshold
            for a new console. Omitting it preserves an existing console's
            explicit level.

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
    with _CONSOLE_LOCK:
        console_name = name or DEFAULT_CONSOLE_NAME
        if not isinstance(console_name, str):
            raise TypeError("A logger name must be a string")
        console = _CONSOLES.get(console_name)
        if console is None:
            # The requested name remains visible in records, but must not
            # share the diagnostic logger's handlers, level or propagation.
            console = _ConsoleLogger(console_name)
            console.parent = logging.getLogger()
            console.manager = console.parent.manager
            console.propagate = False
            _CONSOLES[console_name] = console
        if level is not None:
            console.setLevel(level)
        for handler in console.handlers:
            if isinstance(handler, LazyStdoutStreamHandler):
                break
        else:
            # The logger applies its effective threshold. Keeping the
            # handler at NOTSET also respects later console.setLevel calls.
            console.addHandler(create_stdout_handler(logging.NOTSET))
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

    def emit(
        self, message: str, *, stream: TextIO | None = None, flush: bool = True
    ) -> None:
        """Write one unprefixed line to stdout or a caller-owned stream.

        Only SciTeX print-capture wrappers are bypassed. Other streams keep
        their own write/flush behavior, and failures propagate to the caller.
        """
        import sys

        stream = sys.stdout if stream is None else stream
        # Print capture owns diagnostic duplication. A plain result must
        # bypass only our wrappers, while respecting the current redirected
        # stream and any foreign wrapper's own write/flush behavior.
        while isinstance(stream, PrintCapture):
            stream = stream.original_stdout
        stream.write(f"{message}\n")
        if flush:
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
