#!/usr/bin/env python3
"""Tests for scitex.logging._handlers module."""

import logging
import logging.handlers
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest


class TestCreateConsoleHandler:
    """Test create_console_handler function."""

    def test_create_console_handler_returns_stream_handler_instance(self):
        """create_console_handler returns a logging.StreamHandler instance."""
        # Arrange
        from scitex_logging._handlers import create_console_handler

        # Act
        handler = create_console_handler()
        # Assert
        assert isinstance(handler, logging.StreamHandler)

    def test_create_console_handler_default_level_is_info(self):
        """create_console_handler defaults its log-level to INFO."""
        # Arrange
        from scitex_logging._handlers import create_console_handler

        # Act
        handler = create_console_handler()
        # Assert
        assert handler.level == logging.INFO

    def test_create_console_handler_custom_level_is_respected(self):
        """create_console_handler honours an explicit `level` argument."""
        # Arrange
        from scitex_logging._handlers import create_console_handler

        requested_level = logging.DEBUG
        # Act
        handler = create_console_handler(level=requested_level)
        # Assert
        assert handler.level == requested_level

    def test_create_console_handler_uses_scitex_console_formatter(self):
        """create_console_handler attaches the SciTeXConsoleFormatter."""
        # Arrange
        from scitex_logging._formatters import SciTeXConsoleFormatter
        from scitex_logging._handlers import create_console_handler

        # Act
        handler = create_console_handler()
        # Assert
        assert isinstance(handler.formatter, SciTeXConsoleFormatter)


class TestCreateFileHandler:
    """Test create_file_handler function."""

    def test_create_file_handler_returns_rotating_file_handler(self):
        """create_file_handler returns a RotatingFileHandler instance."""
        # Arrange
        from scitex_logging._handlers import create_file_handler

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            # Act
            handler = create_file_handler(log_path)
            try:
                # Assert
                assert isinstance(handler, logging.handlers.RotatingFileHandler)
            finally:
                handler.close()

    def test_create_file_handler_creates_parent_directories(self):
        """create_file_handler creates missing parent directories."""
        # Arrange
        from scitex_logging._handlers import create_file_handler

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "nested", "dir", "test.log")
            # Act
            handler = create_file_handler(log_path)
            try:
                # Assert
                assert os.path.isdir(os.path.dirname(log_path))
            finally:
                handler.close()

    def test_create_file_handler_default_level_is_info(self):
        """create_file_handler defaults its log-level to INFO."""
        # Arrange
        from scitex_logging._handlers import create_file_handler

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            # Act
            handler = create_file_handler(log_path)
            try:
                # Assert
                assert handler.level == logging.INFO
            finally:
                handler.close()

    def test_create_file_handler_custom_level_is_respected(self):
        """create_file_handler honours an explicit `level` argument."""
        # Arrange
        from scitex_logging._handlers import create_file_handler

        requested_level = logging.DEBUG
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            # Act
            handler = create_file_handler(log_path, level=requested_level)
            try:
                # Assert
                assert handler.level == requested_level
            finally:
                handler.close()

    def test_create_file_handler_custom_max_bytes_is_respected(self):
        """create_file_handler honours an explicit `max_bytes` argument."""
        # Arrange
        from scitex_logging._handlers import create_file_handler

        requested_max = 1024  # stx-allow: STX-NL001
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            # Act
            handler = create_file_handler(log_path, max_bytes=requested_max)
            try:
                # Assert
                assert handler.maxBytes == requested_max
            finally:
                handler.close()

    def test_create_file_handler_custom_backup_count_is_respected(self):
        """create_file_handler honours an explicit `backup_count` argument."""
        # Arrange
        from scitex_logging._handlers import create_file_handler

        requested_backups = 10
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            # Act
            handler = create_file_handler(log_path, backup_count=requested_backups)
            try:
                # Assert
                assert handler.backupCount == requested_backups
            finally:
                handler.close()

    def test_create_file_handler_uses_scitex_file_formatter(self):
        """create_file_handler attaches the SciTeXFileFormatter."""
        # Arrange
        from scitex_logging._formatters import SciTeXFileFormatter
        from scitex_logging._handlers import create_file_handler

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            # Act
            handler = create_file_handler(log_path)
            try:
                # Assert
                assert isinstance(handler.formatter, SciTeXFileFormatter)
            finally:
                handler.close()

    def test_create_file_handler_writes_log_messages_to_disk(self):
        """create_file_handler emits log records to its target file."""
        # Arrange
        from scitex_logging._handlers import create_file_handler

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            handler = create_file_handler(log_path)
            logger = logging.getLogger("test_file_handler")
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            # Act
            logger.info("Test message")
            handler.flush()
            handler.close()
            with open(log_path) as f:
                content = f.read()
            logger.removeHandler(handler)
            # Assert
            assert "Test message" in content


class TestGetDefaultLogPath:
    """Test get_default_log_path function."""

    def test_get_default_log_path_returns_string_value(self):
        """get_default_log_path returns a `str` instance."""
        # Arrange
        from scitex_logging._handlers import get_default_log_path

        # Act
        path = get_default_log_path()
        # Assert
        assert isinstance(path, str)

    def test_get_default_log_path_filename_contains_scitex(self):
        """get_default_log_path puts `scitex` in the log filename."""
        # Arrange
        from scitex_logging._handlers import get_default_log_path

        # Act
        path = get_default_log_path()
        # Assert
        assert "scitex" in os.path.basename(path).lower()

    def test_get_default_log_path_contains_current_date(self):
        """get_default_log_path embeds today's ISO date in the path."""
        # Arrange
        from scitex_logging._handlers import get_default_log_path

        today = datetime.now().strftime("%Y-%m-%d")
        # Act
        path = get_default_log_path()
        # Assert
        assert today in path

    def test_get_default_log_path_ends_with_log_extension(self):
        """get_default_log_path returns a path ending in `.log`."""
        # Arrange
        from scitex_logging._handlers import get_default_log_path

        # Act
        path = get_default_log_path()
        # Assert
        assert path.endswith(".log")

    def test_get_default_log_path_contains_runtime_directory(self):
        """get_default_log_path nests the file under the ``runtime/`` directory."""
        # Arrange
        from scitex_logging._handlers import get_default_log_path

        # Act
        path = get_default_log_path()
        # Assert
        assert "runtime" in path

    def test_get_default_log_path_resolves_under_runtime_slash(self):
        """Resolved pkg-runtime dir contains ``/runtime/`` before the filename."""
        # Arrange
        from scitex_logging._handlers import _get_pkg_runtime_dir

        # Act
        runtime_dir = _get_pkg_runtime_dir()
        # Assert
        assert "/runtime" in str(runtime_dir) or "\\runtime" in str(runtime_dir)

    def test_get_default_log_path_respects_scitex_dir_env(self, request):
        """``get_default_log_path`` honours the ``SCITEX_DIR`` env var."""
        # Arrange
        old_env = os.environ.get("SCITEX_DIR")
        os.environ["SCITEX_DIR"] = "/tmp/stx-test-logging"

        def _restore():
            if old_env is None:
                os.environ.pop("SCITEX_DIR", None)
            else:
                os.environ["SCITEX_DIR"] = old_env

        request.addfinalizer(_restore)

        from scitex_logging._handlers import get_default_log_path

        # Act
        path = get_default_log_path()
        # Assert
        assert path.startswith("/tmp/stx-test-logging/logging/runtime/")


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: /home/ywatanabe/proj/scitex-code/src/scitex/logging/_handlers.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# """Custom handlers for SciTeX logging."""
#
# import logging
# import logging.handlers
# from datetime import datetime
# from pathlib import Path
#
# from scitex.config import get_scitex_dir
#
# from ._formatters import SciTeXConsoleFormatter, SciTeXFileFormatter
#
#
# def create_console_handler(level=logging.INFO):
#     """Create a console handler with SciTeX formatting."""
#     handler = logging.StreamHandler()
#     handler.setLevel(level)
#     handler.setFormatter(SciTeXConsoleFormatter())
#     return handler
#
#
# def create_file_handler(
#     log_file_path, level=logging.INFO, max_bytes=10 * 1024 * 1024, backup_count=5
# ):
#     """Create a rotating file handler for log files.
#
#     Args:
#         log_file_path: Path to the log file
#         level: Log level for the handler
#         max_bytes: Maximum size of log file before rotation (default: 10MB)
#         backup_count: Number of backup files to keep (default: 5)
#     """
#     # Ensure the log directory exists
#     log_dir = Path(log_file_path).parent
#     log_dir.mkdir(parents=True, exist_ok=True)
#
#     # Use RotatingFileHandler to prevent log files from growing too large
#     handler = logging.handlers.RotatingFileHandler(
#         log_file_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
#     )
#     handler.setLevel(level)
#     handler.setFormatter(SciTeXFileFormatter())
#     return handler
#
#
# def get_default_log_path():
#     """Get the default log file path for SciTeX.
#
#     Uses SCITEX_DIR environment variable with fallback to ~/.scitex.
#     Supports .env file loading for configuration.
#     """
#     scitex_dir = get_scitex_dir()
#     logs_dir = scitex_dir / "logs"
#
#     # Create timestamped log file
#     timestamp = datetime.now().strftime("%Y-%m-%d")
#     log_file = logs_dir / f"scitex-{timestamp}.log"
#
#     return str(log_file)
#
#
# __all__ = ["create_console_handler", "create_file_handler", "get_default_log_path"]

# --------------------------------------------------------------------------------
# End of Source Code from: /home/ywatanabe/proj/scitex-code/src/scitex/logging/_handlers.py
# --------------------------------------------------------------------------------
