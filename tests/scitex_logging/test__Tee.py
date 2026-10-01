#!/usr/bin/env python3
"""Tests for scitex.logging._Tee module."""

import os
import sys
import tempfile
from io import StringIO

import pytest


def _run_tee_open_failure(tmp_path, backend_setup=""):
    import subprocess
    from pathlib import Path

    path = tmp_path / "missing-parent" / "test.log"
    env = {
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.defpath,
        "SCITEX_DIR": str(tmp_path / "state"),
        "TMPDIR": str(tmp_path),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    script = (
        "import sys\n"
        "def guard(event,args):\n"
        "    if event in {'socket.bind','socket.connect','socket.getaddrinfo'}:\n"
        "        raise RuntimeError('Tee error fixture must remain offline')\n"
        "sys.addaudithook(guard)\n"
        "import scitex_logging as s\nimport logging\n"
        "s.configure(level='error',enable_file=False,capture_prints=False)\n"
        + backend_setup
        + f"tee=s.Tee(sys.stdout,{str(path)!r},verbose=False)\n"
        "sys.stdout.write('NONE\\n' if tee._log_file is None else 'OPEN\\n')\n"
    )
    result = subprocess.run([sys.executable, "-c", script], env=env, cwd=tmp_path,
                            capture_output=True, text=True, timeout=30)
    original = f"Failed to open log file {path}: [Errno 2] No such file or directory: '{path}'\n"
    return result, original


class TestTee:
    """Test Tee class."""

    def test_tee_init_with_stdout_stores_stream_reference(self):
        """`Tee(sys.stdout, path)` stores `sys.stdout` on `tee._stream`."""
        # Arrange
        from scitex_logging._Tee import Tee

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            # Act
            tee = Tee(sys.stdout, log_path, verbose=False)
            try:
                stored = tee._stream
            finally:
                tee.close()
        # Assert
        assert stored is sys.stdout

    def test_tee_init_with_stdout_stores_log_path(self):
        """`Tee(stream, path)` stores `path` on `tee._log_path`."""
        # Arrange
        from scitex_logging._Tee import Tee

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            # Act
            tee = Tee(sys.stdout, log_path, verbose=False)
            try:
                stored = tee._log_path
            finally:
                tee.close()
        # Assert
        assert stored == log_path

    def test_tee_init_with_stdout_marks_is_stderr_false(self):
        """`Tee(sys.stdout, ...)` records `_is_stderr = False`."""
        # Arrange
        from scitex_logging._Tee import Tee

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            # Act
            tee = Tee(sys.stdout, log_path, verbose=False)
            try:
                stored = tee._is_stderr
            finally:
                tee.close()
        # Assert
        assert stored is False

    def test_tee_init_with_stderr_marks_is_stderr_true(self):
        """`Tee(sys.stderr, ...)` records `_is_stderr = True`."""
        # Arrange
        from scitex_logging._Tee import Tee

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            # Act
            tee = Tee(sys.stderr, log_path, verbose=False)
            try:
                stored = tee._is_stderr
            finally:
                tee.close()
        # Assert
        assert stored is True

    def test_tee_init_creates_log_file_on_disk(self):
        """Constructing a `Tee(...)` creates its log file on disk."""
        # Arrange
        from scitex_logging._Tee import Tee

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            # Act
            tee = Tee(sys.stdout, log_path, verbose=False)
            try:
                file_exists = os.path.exists(log_path)
            finally:
                tee.close()
        # Assert
        assert file_exists is True

    def test_tee_write_forwards_to_underlying_stream(self):
        """`tee.write(text)` forwards the text to the wrapped stream."""
        # Arrange
        from scitex_logging._Tee import Tee

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            buffer = StringIO()
            tee = Tee(buffer, log_path, verbose=False)
            try:
                # Act
                tee.write("test message")
                tee.flush()
                buffer_content = buffer.getvalue()
            finally:
                tee.close()
        # Assert
        assert "test message" in buffer_content

    def test_tee_write_persists_text_to_log_file(self):
        """`tee.write(text)` persists the text to the log file too."""
        # Arrange
        from scitex_logging._Tee import Tee

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            buffer = StringIO()
            tee = Tee(buffer, log_path, verbose=False)
            # Act
            tee.write("test message")
            tee.flush()
            tee.close()
            with open(log_path) as f:
                content = f.read()
        # Assert
        assert "test message" in content

    def test_tee_stderr_logs_plain_error_message(self):
        """A stderr-flagged Tee writes plain (non-progress) messages to disk."""
        # Arrange
        from scitex_logging._Tee import Tee

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            buffer = StringIO()
            tee = Tee(buffer, log_path, verbose=False)
            tee._is_stderr = True
            # Act
            tee.write("error message\n")
            tee.write("  50%|████      [A")
            tee.close()
            with open(log_path) as f:
                content = f.read()
        # Assert
        assert "error message" in content

    def test_tee_stderr_filters_progress_bar_pattern(self):
        """A stderr-flagged Tee filters out tqdm-style progress lines."""
        # Arrange
        from scitex_logging._Tee import Tee

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            buffer = StringIO()
            tee = Tee(buffer, log_path, verbose=False)
            tee._is_stderr = True
            # Act
            tee.write("error message\n")
            tee.write("  50%|████      [A")
            tee.close()
            with open(log_path) as f:
                content = f.read()
        # Assert
        assert "50%" not in content

    def test_tee_flush_does_not_raise(self):
        """`tee.flush()` is callable and returns without raising."""
        # Arrange
        from scitex_logging._Tee import Tee

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            tee = Tee(sys.stdout, log_path, verbose=False)
            try:
                tee.write("test")
                # Act
                returned = tee.flush()
            finally:
                tee.close()
        # Assert
        assert returned is None

    def test_tee_isatty_returns_boolean_value(self):
        """`tee.isatty()` returns a boolean (forwards to underlying stream)."""
        # Arrange
        from scitex_logging._Tee import Tee

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            tee = Tee(sys.stdout, log_path, verbose=False)
            try:
                # Act
                result = tee.isatty()
            finally:
                tee.close()
        # Assert
        assert isinstance(result, bool)

    def test_tee_fileno_returns_integer_value(self):
        """`tee.fileno()` returns an int (forwards to underlying stream)."""
        # Arrange
        from scitex_logging._Tee import Tee

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            tee = Tee(sys.stdout, log_path, verbose=False)
            try:
                # Act
                result = tee.fileno()
            finally:
                tee.close()
        # Assert
        assert isinstance(result, int)

    def test_tee_buffer_property_returns_underlying_stream_buffer(self):
        """`tee.buffer` exposes the wrapped stream's `.buffer`."""
        # Arrange
        from scitex_logging._Tee import Tee

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            tee = Tee(sys.stdout, log_path, verbose=False)
            try:
                # Act
                buffer = tee.buffer
            finally:
                tee.close()
        # Assert
        assert buffer is sys.stdout.buffer

    def test_tee_close_sets_log_file_attribute_to_none(self):
        """`tee.close()` sets `_log_file` to `None`."""
        # Arrange
        from scitex_logging._Tee import Tee

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            tee = Tee(sys.stdout, log_path, verbose=False)
            # Act
            tee.close()
            stored = tee._log_file
        # Assert
        assert stored is None

    def test_tee_close_called_twice_is_idempotent(self):
        """`tee.close()` called twice does not raise on the second call."""
        # Arrange
        from scitex_logging._Tee import Tee

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test.log")
            tee = Tee(sys.stdout, log_path, verbose=False)
            tee.close()
            # Act
            returned = tee.close()
        # Assert
        assert returned is None

    def test_tee_handles_unwritable_log_path_with_none_file(self):
        """A path that cannot be opened leaves `_log_file = None`."""
        # Arrange
        from scitex_logging._Tee import Tee

        # Act
        tee = Tee(sys.stdout, "/nonexistent/deep/path/test.log", verbose=False)
        stored = tee._log_file
        # Assert
        assert stored is None

    def test_tee_open_failure_is_a_levelled_public_logger_error(self, tmp_path):
        # Arrange
        setup = ""
        # Act
        result, original = _run_tee_open_failure(tmp_path, setup)
        # Assert
        assert (result.returncode, result.stdout, result.stderr) == (
            0, "NONE\n", "ERRO: " + original,
        )

    def test_tee_open_failure_survives_a_real_failing_log_handler(self, tmp_path):
        # Arrange
        setup = (
            "class BrokenHandler(logging.Handler):\n"
            "    def emit(self,record): raise RuntimeError('handler failed')\n"
            "logging.getLogger().handlers=[BrokenHandler()]\n"
        )
        # Act
        result, original = _run_tee_open_failure(tmp_path, setup)
        # Assert
        assert (result.returncode, result.stdout, result.stderr) == (
            0, "NONE\n", original,
        )

    def test_tee_open_failure_survives_a_real_failing_logger_constructor(self, tmp_path):
        # Arrange
        setup = (
            "class BrokenLogger(logging.Logger):\n"
            "    def __init__(self,*args,**kwargs): raise RuntimeError('logger failed')\n"
            "logging.setLoggerClass(BrokenLogger)\n"
        )
        # Act
        result, original = _run_tee_open_failure(tmp_path, setup)
        # Assert
        assert (result.returncode, result.stdout, result.stderr) == (
            0, "NONE\n", original,
        )


class TestTeeFunction:
    """Test tee() function."""

    def test_tee_function_returns_a_tuple(self):
        """`tee(sys, sdir=...)` returns a Python tuple."""
        # Arrange
        from scitex_logging._Tee import tee

        with tempfile.TemporaryDirectory() as tmpdir:
            # Act
            result = tee(sys, sdir=tmpdir, verbose=False)
            try:
                is_tuple = isinstance(result, tuple)
            finally:
                result[0].close()
                result[1].close()
        # Assert
        assert is_tuple is True

    def test_tee_function_returns_two_element_tuple(self):
        """`tee(sys, sdir=...)` returns a length-2 tuple (stdout, stderr)."""
        # Arrange
        from scitex_logging._Tee import tee

        with tempfile.TemporaryDirectory() as tmpdir:
            # Act
            result = tee(sys, sdir=tmpdir, verbose=False)
            try:
                length = len(result)
            finally:
                result[0].close()
                result[1].close()
        # Assert
        assert length == 2

    def test_tee_function_first_element_is_tee_instance(self):
        """`tee(sys, sdir=...)[0]` is a Tee instance (stdout wrapper)."""
        # Arrange
        from scitex_logging._Tee import Tee, tee

        with tempfile.TemporaryDirectory() as tmpdir:
            # Act
            result = tee(sys, sdir=tmpdir, verbose=False)
            try:
                is_tee = isinstance(result[0], Tee)
            finally:
                result[0].close()
                result[1].close()
        # Assert
        assert is_tee is True

    def test_tee_function_second_element_is_tee_instance(self):
        """`tee(sys, sdir=...)[1]` is a Tee instance (stderr wrapper)."""
        # Arrange
        from scitex_logging._Tee import Tee, tee

        with tempfile.TemporaryDirectory() as tmpdir:
            # Act
            result = tee(sys, sdir=tmpdir, verbose=False)
            try:
                is_tee = isinstance(result[1], Tee)
            finally:
                result[0].close()
                result[1].close()
        # Assert
        assert is_tee is True

    def test_tee_function_creates_stdout_log_on_disk(self):
        """`tee(sys, sdir=...)` creates `<sdir>/logs/stdout.log` on disk."""
        # Arrange
        from scitex_logging._Tee import tee

        with tempfile.TemporaryDirectory() as tmpdir:
            stdout_tee, stderr_tee = tee(sys, sdir=tmpdir, verbose=False)
            try:
                expected = os.path.join(tmpdir, "logs", "stdout.log")
                # Act
                file_exists = os.path.exists(expected)
            finally:
                stdout_tee.close()
                stderr_tee.close()
        # Assert
        assert file_exists is True

    def test_tee_function_creates_stderr_log_on_disk(self):
        """`tee(sys, sdir=...)` creates `<sdir>/logs/stderr.log` on disk."""
        # Arrange
        from scitex_logging._Tee import tee

        with tempfile.TemporaryDirectory() as tmpdir:
            stdout_tee, stderr_tee = tee(sys, sdir=tmpdir, verbose=False)
            try:
                expected = os.path.join(tmpdir, "logs", "stderr.log")
                # Act
                file_exists = os.path.exists(expected)
            finally:
                stdout_tee.close()
                stderr_tee.close()
        # Assert
        assert file_exists is True

    def test_tee_function_creates_logs_subdirectory(self):
        """`tee(sys, sdir=...)` creates the `<sdir>/logs/` directory."""
        # Arrange
        from scitex_logging._Tee import tee

        with tempfile.TemporaryDirectory() as tmpdir:
            stdout_tee, stderr_tee = tee(sys, sdir=tmpdir, verbose=False)
            try:
                logs_dir = os.path.join(tmpdir, "logs")
                # Act
                dir_exists = os.path.isdir(logs_dir)
            finally:
                stdout_tee.close()
                stderr_tee.close()
        # Assert
        assert dir_exists is True


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: /home/ywatanabe/proj/scitex-code/src/scitex/logging/_Tee.py
# --------------------------------------------------------------------------------
# (source code preserved separately — see git history)
# --------------------------------------------------------------------------------
# End of Source Code from: /home/ywatanabe/proj/scitex-code/src/scitex/logging/_Tee.py
# --------------------------------------------------------------------------------
