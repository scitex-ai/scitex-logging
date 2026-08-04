# Add your tests here
import importlib.util
import logging
import os

import pytest

# Import _formatters directly without triggering scitex_logging.__init__
_formatters_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "src",
    "scitex_logging",
    "_formatters.py",
)
spec = importlib.util.spec_from_file_location("_formatters", _formatters_path)
_formatters = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_formatters)

SciTeXConsoleFormatter = _formatters.SciTeXConsoleFormatter
SciTeXFileFormatter = _formatters.SciTeXFileFormatter
FORMAT_TEMPLATES = _formatters.FORMAT_TEMPLATES
# Note: FORCE_COLOR is evaluated at module load time, so we test via subprocess


def _make_record(msg, level=logging.INFO, levelname="INFO", name="test"):
    """Build a vanilla LogRecord for formatter testing."""
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname="",
        lineno=0,
        msg=msg,
        args=(),
        exc_info=None,
    )
    record.levelname = levelname
    return record


class TestSciTeXConsoleFormatter:
    """Tests for SciTeXConsoleFormatter."""

    def test_basic_format_emits_level_prefix(self):
        """Console formatter prefixes simple messages with `INFO: `."""
        # Arrange
        formatter = SciTeXConsoleFormatter()
        record = _make_record("Hello world")
        # Act
        result = formatter.format(record)
        # Assert
        assert "INFO: Hello world" in result

    def test_leading_newline_moved_before_prefix(self):
        """A leading `\\n` is hoisted in front of the level prefix."""
        # Arrange
        formatter = SciTeXConsoleFormatter()
        record = _make_record("\n============")
        # Act
        result = formatter.format(record)
        # Assert
        assert result.startswith("\n")

    def test_leading_newline_message_keeps_separator(self):
        """A leading-newline message still keeps the divider line."""
        # Arrange
        formatter = SciTeXConsoleFormatter()
        record = _make_record("\n============")
        # Act
        result = formatter.format(record)
        # Assert
        assert "INFO: ============" in result

    def test_leading_newline_does_not_emit_empty_info_line(self):
        """Leading-newline message must NOT produce `INFO: \\n`."""
        # Arrange
        formatter = SciTeXConsoleFormatter()
        record = _make_record("\n============")
        # Act
        result = formatter.format(record)
        # Assert
        assert "INFO: \n" not in result

    def test_multiple_leading_newlines_preserved_as_prefix(self):
        """Three leading newlines remain at the start of the output."""
        # Arrange
        formatter = SciTeXConsoleFormatter()
        record = _make_record("\n\n\nTriple newline")
        # Act
        result = formatter.format(record)
        # Assert
        assert result.startswith("\n\n\n")

    def test_multiple_leading_newlines_keep_payload(self):
        """Three leading newlines still keep the trailing payload prefixed."""
        # Arrange
        formatter = SciTeXConsoleFormatter()
        record = _make_record("\n\n\nTriple newline")
        # Act
        result = formatter.format(record)
        # Assert
        assert "INFO: Triple newline" in result

    def test_internal_newlines_first_line_keeps_prefix(self):
        """Internal-newline message: first line keeps the level prefix."""
        # Arrange
        formatter = SciTeXConsoleFormatter()
        record = _make_record("Line 1\nLine 2\nLine 3")
        # Act
        lines = formatter.format(record).split("\n")
        # Assert
        assert lines[0] == "INFO: Line 1"

    def test_internal_newlines_second_line_gets_prefix(self):
        """Internal-newline message: second line carries the continuation mark."""
        # Arrange
        formatter = SciTeXConsoleFormatter()
        record = _make_record("Line 1\nLine 2\nLine 3")
        # Act
        lines = formatter.format(record).split("\n")
        # Assert
        assert lines[1] == "INFO| Line 2"

    def test_internal_newlines_third_line_gets_prefix(self):
        """Internal-newline message: third line carries the continuation mark."""
        # Arrange
        formatter = SciTeXConsoleFormatter()
        record = _make_record("Line 1\nLine 2\nLine 3")
        # Act
        lines = formatter.format(record).split("\n")
        # Assert
        assert lines[2] == "INFO| Line 3"

    def test_combined_leading_and_internal_newlines_starts_with_newline(self):
        """Leading + internal newlines: output starts with `\\n`."""
        # Arrange
        formatter = SciTeXConsoleFormatter()
        record = _make_record("\nFirst\nSecond")
        # Act
        result = formatter.format(record)
        # Assert
        assert result.startswith("\n")

    def test_combined_newlines_first_payload_line_prefixed(self):
        """Leading + internal newlines: first payload line gets record prefix."""
        # Arrange
        formatter = SciTeXConsoleFormatter()
        record = _make_record("\nFirst\nSecond")
        # Act
        lines = formatter.format(record).split("\n")
        # Assert
        assert lines[1] == "INFO: First"

    def test_combined_newlines_second_payload_line_marked_continuation(self):
        """Leading + internal newlines: second payload line is a CONTINUATION."""
        # Arrange
        formatter = SciTeXConsoleFormatter()
        record = _make_record("\nFirst\nSecond")
        # Act
        lines = formatter.format(record).split("\n")
        # Assert
        assert lines[2] == "INFO| Second"

    def test_empty_continuation_lines_remain_empty(self):
        """An internal blank line stays blank (no spurious `INFO:` prefix)."""
        # Arrange
        formatter = SciTeXConsoleFormatter()
        record = _make_record("Line 1\n\nLine 3")
        # Act
        lines = formatter.format(record).split("\n")
        # Assert
        assert lines[1] == ""

    def test_empty_continuation_lines_keep_neighbours_prefixed(self):
        """Internal blank line: the line after it still gets the continuation mark."""
        # Arrange
        formatter = SciTeXConsoleFormatter()
        record = _make_record("Line 1\n\nLine 3")
        # Act
        lines = formatter.format(record).split("\n")
        # Assert
        assert lines[2] == "INFO| Line 3"

    def test_no_continuation_line_impersonates_a_record(self):
        """THE INVARIANT: a continuation must never match `^<LEVEL>: `.

        A consumer counting `^<LEVEL>: ` must count EVENTS, not paragraphs.
        When continuations carried the identical `LEVEL: ` prefix, one 431-line
        advisory banner parsed as 431 separate records downstream.
        """
        # Arrange
        formatter = SciTeXConsoleFormatter()
        record = _make_record("headline\nbody one\nbody two")
        # Act
        continuations = formatter.format(record).split("\n")[1:]
        # Assert
        assert not any(line.startswith("INFO: ") for line in continuations)

    def test_multiline_record_yields_exactly_one_record_line(self):
        """A three-line record is ONE event, so exactly one `^INFO: ` line."""
        # Arrange
        formatter = SciTeXConsoleFormatter()
        record = _make_record("headline\nbody one\nbody two")
        # Act
        lines = formatter.format(record).split("\n")
        # Assert
        assert sum(1 for line in lines if line.startswith("INFO: ")) == 1

    def test_indent_level_two_applies_four_space_indent(self):
        """`record.indent = 2` with `indent_width=2` indents by 4 spaces."""
        # Arrange
        formatter = SciTeXConsoleFormatter(indent_width=2)
        record = _make_record("Indented message")
        record.indent = 2
        # Act
        result = formatter.format(record)
        # Assert
        assert "INFO:     Indented message" in result  # 4 spaces (2 levels * 2 width)


class TestSciTeXFileFormatter:
    """Tests for SciTeXFileFormatter."""

    def test_file_format_includes_logger_name(self):
        """File formatter renders the logger name in the output."""
        # Arrange
        formatter = SciTeXFileFormatter()
        record = _make_record("File log message", name="test.module")
        # Act
        result = formatter.format(record)
        # Assert
        assert "test.module" in result

    def test_file_format_includes_level_name(self):
        """File formatter renders the level name in the output."""
        # Arrange
        formatter = SciTeXFileFormatter()
        record = _make_record("File log message", name="test.module")
        # Act
        result = formatter.format(record)
        # Assert
        assert "INFO" in result

    def test_file_format_includes_message_body(self):
        """File formatter renders the message body in the output."""
        # Arrange
        formatter = SciTeXFileFormatter()
        record = _make_record("File log message", name="test.module")
        # Act
        result = formatter.format(record)
        # Assert
        assert "File log message" in result


class TestFormatTemplates:
    """Tests for format templates."""

    @pytest.mark.parametrize("name", ["minimal", "default", "detailed", "debug", "full"])
    def test_template_name_is_registered(self, name):
        """Each expected template name is registered in FORMAT_TEMPLATES."""
        # Arrange
        registered = FORMAT_TEMPLATES
        # Act
        is_present = name in registered
        # Assert
        assert is_present is True

    @pytest.mark.parametrize("name", ["minimal", "default", "detailed", "debug", "full"])
    def test_template_contains_message_placeholder(self, name):
        """Every registered template embeds the `%(message)s` placeholder."""
        # Arrange
        template = FORMAT_TEMPLATES[name]
        # Act
        has_message = "%(message)s" in template
        # Assert
        assert has_message is True


class TestForceColor:
    """Tests for SCITEX_FORCE_COLOR environment variable."""

    @pytest.fixture(autouse=True)
    def setup_pythonpath(self):
        """Set up PYTHONPATH for subprocess tests."""
        project_root = os.path.join(os.path.dirname(__file__), "..", "..")
        self.project_root = os.path.abspath(project_root)
        self.src_dir = os.path.join(self.project_root, "src")
        existing_pythonpath = os.environ.get("PYTHONPATH", "")
        if existing_pythonpath:
            self.pythonpath = f"{self.src_dir}:{existing_pythonpath}"
        else:
            self.pythonpath = self.src_dir

    def test_force_color_env_value_one_is_parsed_true(self):
        """`SCITEX_FORCE_COLOR=1` materialises `FORCE_COLOR is True` at import."""
        # Arrange
        import subprocess

        script = (
            "import os\n"
            "os.environ['SCITEX_FORCE_COLOR'] = '1'\n"
            "import importlib.util\n"
            "spec = importlib.util.spec_from_file_location('_formatters',\n"
            "    'src/scitex_logging/_formatters.py')\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(mod)\n"
            "print('FORCE_COLOR:', mod.FORCE_COLOR)\n"
        )
        # Act
        result = subprocess.run(
            ["python", "-c", script],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
        )
        # Assert
        assert "FORCE_COLOR: True" in result.stdout

    @pytest.mark.slow
    @pytest.mark.timeout(120)
    def test_force_color_adds_ansi_codes_to_piped_output(self):
        """`SCITEX_FORCE_COLOR=1` makes piped stderr include ANSI colour codes."""
        # Arrange
        import subprocess

        script = (
            "from scitex_logging import getLogger\n"
            "logger = getLogger('test')\n"
            "logger.warning('test warning')\n"
        )
        env = {
            **os.environ,
            "SCITEX_FORCE_COLOR": "1",
            "PYTHONPATH": self.pythonpath,
        }
        # Act
        result = subprocess.run(
            ["python", "-c", script],
            env=env,
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=90,
        )
        output = result.stdout + result.stderr
        has_ansi = "\033[33m" in output or "\x1b[33m" in output
        # Assert
        assert has_ansi is True

    @pytest.mark.slow
    @pytest.mark.timeout(120)
    def test_unset_force_color_keeps_piped_output_plain(self):
        """Without `SCITEX_FORCE_COLOR`, piped stderr has no ANSI colour codes."""
        # Arrange
        import subprocess

        env = {k: v for k, v in os.environ.items() if k != "SCITEX_FORCE_COLOR"}
        env["PYTHONPATH"] = self.pythonpath
        script = (
            "from scitex_logging import getLogger\n"
            "logger = getLogger('test')\n"
            "logger.warning('test warning')\n"
        )
        # Act
        result = subprocess.run(
            ["python", "-c", script],
            env=env,
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=90,
        )
        output = result.stdout + result.stderr
        has_ansi = "\033[33m" in output or "\x1b[33m" in output
        # Assert
        assert has_ansi is False

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "YES"])
    def test_force_color_truthy_value_parses_true(self, value):
        """`SCITEX_FORCE_COLOR` parses any truthy string as `True`."""
        # Arrange
        import subprocess

        script = (
            "import os\n"
            f"os.environ['SCITEX_FORCE_COLOR'] = '{value}'\n"
            "import importlib.util\n"
            "spec = importlib.util.spec_from_file_location('_formatters',\n"
            "    'src/scitex_logging/_formatters.py')\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(mod)\n"
            "print('FORCE_COLOR:', mod.FORCE_COLOR)\n"
        )
        # Act
        result = subprocess.run(
            ["python", "-c", script],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
        )
        # Assert
        assert "FORCE_COLOR: True" in result.stdout, f"Failed for value: {value}"

    @pytest.mark.parametrize("value", ["0", "false", "no", ""])
    def test_force_color_falsy_value_parses_false(self, value):
        """`SCITEX_FORCE_COLOR` parses any falsy string as `False`."""
        # Arrange
        import subprocess

        script = (
            "import os\n"
            f"os.environ['SCITEX_FORCE_COLOR'] = '{value}'\n"
            "import importlib.util\n"
            "spec = importlib.util.spec_from_file_location('_formatters',\n"
            "    'src/scitex_logging/_formatters.py')\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(mod)\n"
            "print('FORCE_COLOR:', mod.FORCE_COLOR)\n"
        )
        # Act
        result = subprocess.run(
            ["python", "-c", script],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
        )
        # Assert
        assert "FORCE_COLOR: False" in result.stdout, f"Failed for value: {value}"


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: /home/ywatanabe/proj/scitex-code/src/scitex/logging/_formatters.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# # Timestamp: "2025-10-11 00:17:43 (ywatanabe)"
# # File: /home/ywatanabe/proj/scitex_repo/src/scitex/logging/_formatters.py
# # ----------------------------------------
# from __future__ import annotations
# import os
#
# __FILE__ = "./src/scitex/logging/_formatters.py"
# __DIR__ = os.path.dirname(__FILE__)
# # ----------------------------------------
#
# __FILE__ = __file__
# """Custom formatters for SciTeX logging."""
#
# import logging
# import sys
#
# # Global format configuration via environment variable
# # Options: default, minimal, detailed, debug, full
# # SCITEX_LOG_FORMAT=debug python script.py
# LOG_FORMAT = os.getenv("SCITEX_LOG_FORMAT", "default")
#
# # Force color output even when stdout is not a TTY (e.g., when piping through tee)
# # SCITEX_FORCE_COLOR=1 python script.py | tee output.log
# FORCE_COLOR = os.getenv("SCITEX_FORCE_COLOR", "").lower() in ("1", "true", "yes")
#
# # Available format templates
# FORMAT_TEMPLATES = {
#     "minimal": "%(levelname)s: %(message)s",
#     "default": "%(levelname)s: %(message)s",
#     "detailed": "%(levelname)s: [%(name)s] %(message)s",
#     "debug": "%(levelname)s: [%(filename)s:%(lineno)d - %(funcName)s()] %(message)s",
#     "full": "%(asctime)s - %(levelname)s: [%(filename)s:%(lineno)d - %(name)s.%(funcName)s()] %(message)s",
# }
#
#
# class SciTeXConsoleFormatter(logging.Formatter):
#     """Custom formatter with color support and configurable format."""
#
#     # ANSI color codes for log levels
#     COLORS = {
#         "DEBU": "\033[90m",  # Grey
#         "INFO": "\033[90m",  # Grey
#         "SUCC": "\033[32m",  # Green
#         "WARN": "\033[33m",  # Yellow
#         "FAIL": "\033[91m",  # Light Red
#         "ERRO": "\033[31m",  # Red
#         "CRIT": "\033[35m",  # Magenta
#     }
#
#     # Color name to ANSI code mapping
#     COLOR_NAMES = {
#         "black": "\033[30m",
#         "red": "\033[31m",
#         "green": "\033[32m",
#         "yellow": "\033[33m",
#         "blue": "\033[34m",
#         "magenta": "\033[35m",
#         "cyan": "\033[36m",
#         "white": "\033[37m",
#         "grey": "\033[90m",
#         "light_red": "\033[91m",
#         "light_green": "\033[92m",
#         "light_yellow": "\033[93m",
#         "lightblue": "\033[94m",
#         "light_magenta": "\033[95m",
#         "light_cyan": "\033[96m",
#     }
#
#     RESET = "\033[0m"
#
#     def __init__(self, fmt=None, indent_width=2):
#         """
#         Initialize with format from global config.
#
#         Args:
#             fmt: Format template string
#             indent_width: Number of spaces per indent level (default: 2)
#         """
#         if fmt is None:
#             fmt = FORMAT_TEMPLATES.get(LOG_FORMAT, FORMAT_TEMPLATES["default"])
#         super().__init__(fmt)
#         self.indent_width = indent_width
#
#     def format(self, record):
#         # Handle leading newlines: extract and preserve them
#         msg = str(record.msg) if record.msg else ""
#         leading_newlines = ""
#         while msg.startswith("\n"):
#             leading_newlines += "\n"
#             msg = msg[1:]
#         record.msg = msg
#
#         # Apply indentation if specified in record
#         indent_level = getattr(record, "indent", 0)
#         if indent_level > 0:
#             indent = " " * (indent_level * self.indent_width)
#             record.msg = f"{indent}{record.msg}"
#
#         # Use parent formatter to apply template
#         formatted = super().format(record)
#
#         # Handle internal newlines: each line gets the level prefix
#         if "\n" in formatted:
#             lines = formatted.split("\n")
#             # First line already has prefix from parent formatter
#             # Add prefix to each continuation line
#             prefix = f"{record.levelname}: "
#             formatted = lines[0] + "\n" + "\n".join(
#                 prefix + line if line.strip() else line
#                 for line in lines[1:]
#             )
#
#         # Check if we can use colors (stdout is a tty and not closed, or forced)
#         try:
#             use_colors = FORCE_COLOR or (hasattr(sys.stdout, "isatty") and sys.stdout.isatty())
#         except ValueError:
#             # stdout/stderr is closed
#             use_colors = FORCE_COLOR
#
#         if use_colors:
#             # Check for custom color override
#             custom_color = getattr(record, "color", None)
#
#             if custom_color and custom_color in self.COLOR_NAMES:
#                 # Use custom color
#                 color = self.COLOR_NAMES[custom_color]
#                 return f"{leading_newlines}{color}{formatted}{self.RESET}"
#             else:
#                 # Use default color for log level
#                 levelname = record.levelname
#                 if levelname in self.COLORS:
#                     color = self.COLORS[levelname]
#                     return f"{leading_newlines}{color}{formatted}{self.RESET}"
#
#         return f"{leading_newlines}{formatted}"
#
#
# class SciTeXFileFormatter(logging.Formatter):
#     """Custom formatter for file output without colors."""
#
#     def __init__(self):
#         super().__init__(
#             fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
#             datefmt="%Y-%m-%d %H:%M:%S",
#         )
#
#
# __all__ = [
#     "SciTeXConsoleFormatter",
#     "SciTeXFileFormatter",
#     "LOG_FORMAT",
#     "FORMAT_TEMPLATES",
#     "FORCE_COLOR",
# ]
#
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: /home/ywatanabe/proj/scitex-code/src/scitex/logging/_formatters.py
# --------------------------------------------------------------------------------
