#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print capture system for SciTeX logging."""

import logging
import sys


class PrintCapture:
    """Capture print() output and redirect to logging system."""

    def __init__(self, logger_name: str = "scitex.print_capture"):
        self.logger = logging.getLogger(logger_name)
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.capturing = False
        self._context_owners = []

    def start_capture(self):
        """Start capturing print output."""
        if self.capturing:
            return

        # A redirect may have restored this inactive wrapper after an
        # earlier stop. Never make the wrapper its own forwarding target.
        stream = sys.stdout
        while isinstance(stream, PrintCapture) and not stream.capturing:
            stream = stream.original_stdout
        self.original_stdout = stream
        self.original_stderr = sys.stderr
        self.capturing = True
        sys.stdout = self

    def stop_capture(self):
        """Stop capturing print output."""
        self.capturing = False
        # Another redirect owns stdout while it is current. Its eventual
        # restoration may expose this inactive wrapper, which then forwards
        # bytes without capture until it is explicitly stopped/restarted.
        if sys.stdout is self:
            stream = self.original_stdout
            while isinstance(stream, PrintCapture) and not stream.capturing:
                stream = stream.original_stdout
            sys.stdout = stream

    def write(self, text):
        """Handle write calls from print()."""
        # Also write to original stdout for real-time viewing
        written = self.original_stdout.write(text)
        self.original_stdout.flush()

        # Log the output (strip newlines for cleaner logs)
        clean_text = text.rstrip("\n")
        if self.capturing and clean_text:  # Only log active, non-empty text
            self.logger.info(clean_text)
        return written

    def flush(self):
        """Handle flush calls."""
        self.original_stdout.flush()

    def isatty(self):
        """Handle isatty calls."""
        return self.original_stdout.isatty()

    def __enter__(self):
        """Context manager entry."""
        self._context_owners.append(not self.capturing)
        self.start_capture()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._context_owners.pop():
            self.stop_capture()


# Global print capture instance
_print_capture = None


def enable_print_capture(logger_name: str = "scitex.print_capture"):
    """Enable automatic print capture globally."""
    global _print_capture
    if _print_capture is None:
        _print_capture = PrintCapture(logger_name)
    _print_capture.start_capture()


def disable_print_capture():
    """Disable automatic print capture globally."""
    global _print_capture
    if _print_capture is not None:
        _print_capture.stop_capture()


def is_print_capture_enabled():
    """Check if print capture is currently enabled."""
    global _print_capture
    return _print_capture is not None and _print_capture.capturing


__all__ = [
    "PrintCapture",
    "enable_print_capture",
    "disable_print_capture",
    "is_print_capture_enabled",
]
