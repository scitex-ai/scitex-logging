#!/usr/bin/env python3
"""Tests for scitex.logging._config module."""

import logging
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _file_logging_state():
    """Establish each control's default and restore the caller's global gate."""
    from scitex_logging._config import enable_file_logging, is_file_logging_enabled

    previous = is_file_logging_enabled()
    enable_file_logging(True)
    try:
        yield
    finally:
        enable_file_logging(previous)


class TestSetLevel:
    """Test set_level function."""

    def setup_method(self):
        """Reset logging state before each test."""
        import scitex_logging._config as config_module

        config_module._GLOBAL_LEVEL = None

    @pytest.mark.parametrize(
        "level_name,expected",
        [
            ("debug", logging.DEBUG),
            ("info", logging.INFO),
            ("warning", logging.WARNING),
            ("error", logging.ERROR),
            ("critical", logging.CRITICAL),
        ],
    )
    def test_set_level_with_lowercase_string_name_persists(self, level_name, expected):
        """`set_level('debug')` etc. persist the matching numeric level."""
        # Arrange
        from scitex_logging._config import get_level, set_level

        # Act
        set_level(level_name)
        result = get_level()
        # Assert
        assert result == expected

    def test_set_level_with_integer_value_persists(self):
        """`set_level(logging.WARNING)` persists the integer WARNING level."""
        # Arrange
        from scitex_logging._config import get_level, set_level

        # Act
        set_level(logging.WARNING)
        result = get_level()
        # Assert
        assert result == logging.WARNING

    def test_set_level_uppercase_string_is_case_insensitive(self):
        """`set_level('DEBUG')` resolves to logging.DEBUG (case-insensitive)."""
        # Arrange
        from scitex_logging._config import get_level, set_level

        # Act
        set_level("DEBUG")
        result = get_level()
        # Assert
        assert result == logging.DEBUG

    def test_set_level_title_case_string_is_case_insensitive(self):
        """`set_level('Info')` resolves to logging.INFO (case-insensitive)."""
        # Arrange
        from scitex_logging._config import get_level, set_level

        # Act
        set_level("Info")
        result = get_level()
        # Assert
        assert result == logging.INFO

    def test_set_level_with_string_success_maps_to_success_constant(self):
        """`set_level('success')` resolves to the SUCCESS custom level."""
        # Arrange
        from scitex_logging._config import get_level, set_level
        from scitex_logging._levels import SUCCESS

        # Act
        set_level("success")
        result = get_level()
        # Assert
        assert result == SUCCESS

    def test_set_level_with_string_fail_maps_to_fail_constant(self):
        """`set_level('fail')` resolves to the FAIL custom level."""
        # Arrange
        from scitex_logging._config import get_level, set_level
        from scitex_logging._levels import FAIL

        # Act
        set_level("fail")
        result = get_level()
        # Assert
        assert result == FAIL


class TestGetLevel:
    """Test get_level function."""

    def test_get_level_returns_globally_set_level(self):
        """`get_level()` returns the value most recently set via set_level."""
        # Arrange
        from scitex_logging._config import get_level, set_level

        set_level(logging.ERROR)
        # Act
        result = get_level()
        # Assert
        assert result == logging.ERROR

    def test_get_level_falls_back_to_root_logger_when_unset(self):
        """`get_level()` falls back to the root logger level when unset."""
        # Arrange
        import scitex_logging._config as config_module
        from scitex_logging._config import get_level

        config_module._GLOBAL_LEVEL = None
        expected = logging.getLogger().level
        # Act
        result = get_level()
        # Assert
        assert result == expected


class TestFileLogging:
    """Test enable_file_logging and is_file_logging_enabled functions."""

    def setup_method(self):
        """Reset file logging state before each test."""
        import scitex_logging._config as config_module

        config_module._FILE_LOGGING_ENABLED = True

    def test_file_logging_is_enabled_by_default(self):
        """`is_file_logging_enabled()` is True after module import."""
        # Arrange
        from scitex_logging._config import is_file_logging_enabled

        # Act
        result = is_file_logging_enabled()
        # Assert
        assert result is True

    def test_enable_file_logging_true_makes_state_true(self):
        """`enable_file_logging(True)` flips state to True."""
        # Arrange
        from scitex_logging._config import enable_file_logging, is_file_logging_enabled

        # Act
        enable_file_logging(True)
        result = is_file_logging_enabled()
        # Assert
        assert result is True

    def test_enable_file_logging_false_makes_state_false(self):
        """`enable_file_logging(False)` flips state to False."""
        # Arrange
        from scitex_logging._config import enable_file_logging, is_file_logging_enabled

        # Act
        enable_file_logging(False)
        result = is_file_logging_enabled()
        # Assert
        assert result is False

    def test_enable_file_logging_toggle_off_then_on_returns_true(self):
        """Toggling `enable_file_logging(False)` then `(True)` ends at True."""
        # Arrange
        from scitex_logging._config import enable_file_logging, is_file_logging_enabled

        enable_file_logging(False)
        # Act
        enable_file_logging(True)
        result = is_file_logging_enabled()
        # Assert
        assert result is True


class TestConfigure:
    """Test configure function."""

    def setup_method(self):
        """Reset logging state before each test."""
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)

    def teardown_method(self):
        """Clean up after tests."""
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)

    def test_configure_with_console_only_installs_one_handler(self):
        """`configure(enable_console=True, enable_file=False)` installs 1 handler."""
        # Arrange
        from scitex_logging._config import configure

        configure(
            level="info", enable_console=True, enable_file=False, capture_prints=False
        )
        # Act
        handler_count = len(logging.getLogger().handlers)
        # Assert
        assert handler_count == 1

    def test_configure_with_console_only_installs_stream_handler(self):
        """`configure(enable_console=True, enable_file=False)` installs a StreamHandler."""
        # Arrange
        from scitex_logging._config import configure

        configure(
            level="info", enable_console=True, enable_file=False, capture_prints=False
        )
        # Act
        installed = logging.getLogger().handlers[0]
        # Assert
        assert isinstance(installed, logging.StreamHandler)

    def test_configure_with_warning_level_persists_warning(self):
        """`configure(level='warning')` persists logging.WARNING globally."""
        # Arrange
        from scitex_logging._config import configure, get_level

        # Act
        configure(
            level="warning",
            enable_console=True,
            enable_file=False,
            capture_prints=False,
        )
        result = get_level()
        # Assert
        assert result == logging.WARNING

    def test_configure_with_debug_string_level_persists_debug(self):
        """`configure(level='debug')` persists logging.DEBUG globally."""
        # Arrange
        from scitex_logging._config import configure, get_level

        # Act
        configure(
            level="debug", enable_console=True, enable_file=False, capture_prints=False
        )
        result = get_level()
        # Assert
        assert result == logging.DEBUG

    def test_configure_clears_existing_root_handlers_before_install(self):
        """`configure()` clears pre-existing root handlers before adding new ones."""
        # Arrange
        from scitex_logging._config import configure

        root = logging.getLogger()
        root.addHandler(logging.StreamHandler())
        root.addHandler(logging.StreamHandler())
        # Act
        configure(
            level="info", enable_console=True, enable_file=False, capture_prints=False
        )
        handler_count = len(root.handlers)
        # Assert
        assert handler_count == 1

    def test_configure_with_file_logging_installs_two_handlers(self):
        """`configure(enable_file=True, enable_console=True)` installs 2 handlers."""
        # Arrange
        from scitex_logging._config import configure

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            configure(
                level="info",
                log_file=log_file,
                enable_file=True,
                enable_console=True,
                capture_prints=False,
            )
            # Act
            handler_count = len(logging.getLogger().handlers)
        # Assert
        assert handler_count == 2  # Console + File

    def test_configure_with_both_disabled_installs_zero_handlers(self):
        """`configure(enable_console=False, enable_file=False)` installs 0 handlers."""
        # Arrange
        from scitex_logging._config import configure

        # Act
        configure(
            level="info", enable_console=False, enable_file=False, capture_prints=False
        )
        handler_count = len(logging.getLogger().handlers)
        # Assert
        assert handler_count == 0


class TestGetLogPath:
    """Test get_log_path function."""

    def setup_method(self):
        """Reset logging state before each test."""
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)

    def teardown_method(self):
        """Clean up after tests."""
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)

    def test_get_log_path_returns_none_when_no_file_handler_installed(self):
        """`get_log_path()` is None when only console handlers exist."""
        # Arrange
        from scitex_logging._config import configure, get_log_path

        configure(
            level="info", enable_console=True, enable_file=False, capture_prints=False
        )
        # Act
        result = get_log_path()
        # Assert
        assert result is None

    def test_get_log_path_returns_not_none_when_file_handler_installed(self):
        """`get_log_path()` is not None when a file handler is installed."""
        # Arrange
        from scitex_logging._config import configure, get_log_path

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            configure(
                level="info",
                log_file=log_file,
                enable_file=True,
                enable_console=False,
                capture_prints=False,
            )
            # Act
            result = get_log_path()
        # Assert
        assert result is not None

    def test_get_log_path_returns_configured_file_path_substring(self):
        """`get_log_path()` returns a string containing the configured path."""
        # Arrange
        from scitex_logging._config import configure, get_log_path

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            configure(
                level="info",
                log_file=log_file,
                enable_file=True,
                enable_console=False,
                capture_prints=False,
            )
            # Act
            result = get_log_path()
        # Assert
        assert log_file in result


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: /home/ywatanabe/proj/scitex-code/src/scitex/logging/_config.py
# --------------------------------------------------------------------------------
# (source code preserved separately — see git history)
# --------------------------------------------------------------------------------
# End of Source Code from: /home/ywatanabe/proj/scitex-code/src/scitex/logging/_config.py
# --------------------------------------------------------------------------------
