#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Custom handlers for SciTeX logging."""

import logging
import logging.handlers
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

from ._formatters import SciTeXConsoleFormatter, SciTeXFileFormatter
from ._print_capture import PrintCapture

_PKG_SHORT = "logging"

# ---------------------------------------------------------------------------
# Deprecation / migration tracking (one-time warning per process)
# ---------------------------------------------------------------------------
_MIGRATION_WARNED = False


def _get_scitex_dir() -> Path:
    """Get SCITEX_DIR with priority: env -> default (~/.scitex)."""
    env_val = os.getenv("SCITEX_DIR")
    if env_val:
        return Path(env_val).expanduser()
    return Path.home() / ".scitex"


def _get_pkg_runtime_dir() -> Path:
    """Return ``<scitex_dir>/<pkg_short>/runtime/``.

    Resolves ``SCITEX_DIR`` (env var) or ``~/.scitex``, appends the
    canonical package-scoped runtime path.  The directory is **not**
    created here -- :func:`get_default_log_path` creates it lazily.
    """
    return _get_scitex_dir() / _PKG_SHORT / "runtime"


def _get_old_logs_dir() -> Path:
    """Return the legacy (pre-2026) logs directory.

    Before the ecosystem-wide local-state layout was adopted,
    ``scitex-logging`` wrote directly to ``~/.scitex/logs/``.  This
    function returns that legacy path so migrations can find and move
    old files.
    """
    return _get_scitex_dir() / "logs"


class LazyStderrStreamHandler(logging.StreamHandler):
    """StreamHandler that resolves ``sys.stderr`` on every emit.

    Stock ``StreamHandler()`` caches a reference to ``sys.stderr`` at
    construction time. If a caller temporarily replaces ``sys.stderr``
    (e.g. via a stdio-capture context manager) and the captured stream
    is later closed, subsequent emits raise
    ``ValueError: I/O operation on closed file.`` and Python's logging
    module surfaces a "Logging error" traceback even when the application
    code completed cleanly.

    By re-resolving ``sys.stderr`` per emit (and per ``flush`` for
    correctness), the handler always writes to whatever ``sys.stderr``
    points at *right now* — which is what users of the standard library
    ``print`` already get. Stays in lockstep with ``contextlib.redirect_stderr``,
    pytest's ``capsys`` / ``capfd``, click's isolated streams, and the
    scitex-dev audit pipeline.
    """

    def __init__(self, level=logging.NOTSET):
        # Pass `None` so the base initialiser uses ``sys.stderr`` at
        # construction time; we'll override ``self.stream`` per-emit below
        # via the ``stream`` property.
        super().__init__(stream=None)
        self.setLevel(level)

    # The base class stores the stream in ``self.stream``; intercept via
    # a property so each ``.write`` / ``.flush`` call gets the current
    # ``sys.stderr``. Setter is a no-op so ``setStream`` calls from the
    # base class don't pin a stale reference.
    @property
    def stream(self):  # type: ignore[override]
        return sys.stderr

    @stream.setter
    def stream(self, _value):
        # Intentionally ignore: we always want the live ``sys.stderr``.
        # ``logging.StreamHandler.__init__`` and ``setStream`` will try to
        # assign here; we want both to be no-ops.
        return


class LazyStdoutStreamHandler(logging.StreamHandler):
    """``LazyStderrStreamHandler``'s twin, writing to ``sys.stdout``.

    Same lazy-resolution rationale as the stderr handler above: the
    stream is looked up per emit so the handler stays in lockstep with
    ``contextlib.redirect_stdout``, pytest's ``capsys`` / ``capfd``, and
    click's isolated streams.

    Stdout exists as a separate destination because stderr and stdout
    answer different questions. Diagnostics belong on stderr, where they
    do not corrupt a pipeline. Output the user asked for — a result, a
    status line they are reading — belongs on stdout, where it can be
    piped, redirected, and read by another program. Routing the second
    kind to stderr is what makes logging awkward to consume. See
    :func:`scitex_logging.getConsole`.
    """

    def __init__(self, level=logging.NOTSET):
        # `None` so the base initialiser does not pin a stream; the
        # ``stream`` property overrides it per emit.
        super().__init__(stream=None)
        self.setLevel(level)

    @property
    def stream(self):  # type: ignore[override]
        stream = sys.stdout
        # ``configure(capture_prints=True)`` — the DEFAULT — replaces
        # ``sys.stdout`` with a tee that writes the real stdout *and* logs
        # what it sees. Resolving to that tee would send every console line
        # to stdout once and, via the log, to stderr again: the caller asked
        # for one stream and would get two. ``propagate = False`` cannot
        # prevent it, because the second copy never travels through the
        # logger hierarchy — it re-enters through ``sys.stdout`` itself.
        #
        # So write past the tee, to the stdout it replaced. Lazy resolution
        # is preserved: this still reads ``sys.stdout`` per emit, so
        # ``redirect_stdout`` and pytest's ``capsys`` keep working.
        if isinstance(stream, PrintCapture):
            return stream.original_stdout
        return stream

    @stream.setter
    def stream(self, _value):
        # Intentionally ignore, so ``setStream`` cannot pin a stale
        # reference. Mirrors LazyStderrStreamHandler.
        return


def create_console_handler(level=logging.INFO):
    """Create a **stderr** handler with SciTeX formatting.

    Named ``console`` for historical reasons; the stream is ``sys.stderr``.
    For stdout, use :func:`create_stdout_handler` (or the higher-level
    :func:`scitex_logging.getConsole`).

    Uses ``LazyStderrStreamHandler`` so the handler stays in sync with
    ``sys.stderr`` even when callers temporarily redirect it (capture
    helpers, click's isolated streams, etc.).
    """
    handler = LazyStderrStreamHandler(level=level)
    handler.setFormatter(SciTeXConsoleFormatter())
    return handler


def create_stdout_handler(level=logging.INFO):
    """Create a **stdout** handler with the same SciTeX formatting.

    Identical formatting to :func:`create_console_handler` — same
    ``SciTeXConsoleFormatter`` — so a line's appearance does not tell you
    which stream it went to. Only the destination differs.
    """
    handler = LazyStdoutStreamHandler(level=level)
    handler.setFormatter(SciTeXConsoleFormatter())
    return handler


def create_file_handler(
    log_file_path, level=logging.INFO, max_bytes=10 * 1024 * 1024, backup_count=5
):
    """Create a rotating file handler for log files.

    Args:
        log_file_path: Path to the log file
        level: Log level for the handler
        max_bytes: Maximum size of log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
    """
    # Ensure the log directory exists
    log_dir = Path(log_file_path).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Use RotatingFileHandler to prevent log files from growing too large
    handler = logging.handlers.RotatingFileHandler(
        log_file_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    handler.setLevel(level)
    handler.setFormatter(SciTeXFileFormatter())
    return handler


def _migrate_legacy_logs() -> None:
    """Move log files from the legacy ``~/.scitex/logs/`` layout.

    Before 2026 the default path was ``~/.scitex/logs/scitex-YYYY-MM-DD.log``.
    The canonical layout is ``~/.scitex/logging/runtime/scitex-YYYY-MM-DD.log``.
    On the first call this function moves any existing files and emits a
    one-time ``SciTeXDeprecationWarning``.

    The shim is kept for one minor version (per ecosystem convention).
    """
    global _MIGRATION_WARNED
    if _MIGRATION_WARNED:
        return

    old_dir = _get_old_logs_dir()
    new_dir = _get_pkg_runtime_dir()
    if not old_dir.is_dir():
        _MIGRATION_WARNED = True
        return

    new_dir.mkdir(parents=True, exist_ok=True)
    moved = 0
    for p in sorted(old_dir.glob("scitex-*.log*")):
        dest = new_dir / p.name
        if not dest.exists():
            p.rename(dest)
            moved += 1
    # Remove old dir if empty
    try:
        old_dir.rmdir()
    except OSError:
        pass

    if moved:
        from ._warnings import SciTeXDeprecationWarning  # fmt: skip

        warnings.warn(
            "scitex-logging: log files have moved from "
            f"{old_dir}/ to {new_dir}/. "
            "Set $SCITEX_DIR to relocate the entire tree.",
            SciTeXDeprecationWarning,
            stacklevel=2,
        )
    _MIGRATION_WARNED = True


def get_default_log_path():
    """Get the default log file path for SciTeX.

    Returns a path under ``~/.scitex/logging/runtime/`` (or
    ``$SCITEX_DIR/logging/runtime/`` when ``SCITEX_DIR`` is set).

    On first call, legacy log files from the old ``~/.scitex/logs/``
    location are automatically migrated with a deprecation warning.

    Returns:
        str: Absolute path to the current day's log file.
    """
    _migrate_legacy_logs()
    runtime_dir = _get_pkg_runtime_dir()
    runtime_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d")
    log_file = runtime_dir / f"scitex-{timestamp}.log"

    return str(log_file)


__all__ = [
    "create_console_handler",
    "create_file_handler",
    "create_stdout_handler",
    "get_default_log_path",
]
