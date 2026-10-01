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

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

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


# ``capture_prints=True`` is the DEFAULT of ``configure()``, and it swaps
# ``sys.stdout`` for a tee that writes the real stdout *and* logs what it
# sees — which would put every console line on stderr as well. `capsys`
# cannot measure that honestly, because it replaces ``sys.stdout`` itself
# and so changes the very thing under test. A subprocess with real pipes
# is the only reading that means anything here.
_CAPTURE_PRINTS_SCRIPT = """
import scitex_logging as s
s.configure(level="info", enable_file=False, enable_console=True, capture_prints=True)
s.getConsole("scitex.console.capture_prints_probe").success("DELIVERABLE")
"""


def _run_console_under_print_capture():
    """Return (stdout, stderr) of one console write with print capture on."""
    import subprocess
    import sys as _sys

    completed = subprocess.run(
        [_sys.executable, "-c", _CAPTURE_PRINTS_SCRIPT],
        capture_output=True,
        text=True,
    )
    return completed.stdout, completed.stderr


def test_console_reaches_stdout_when_print_capture_is_enabled():
    # Arrange
    expected = "DELIVERABLE"

    # Act
    stdout, _ = _run_console_under_print_capture()

    # Assert
    assert expected in stdout


def test_console_does_not_leak_to_stderr_when_print_capture_is_enabled():
    # Arrange
    unexpected = "DELIVERABLE"

    # Act
    _, stderr = _run_console_under_print_capture()

    # Assert
    assert unexpected not in stderr


# EOF


def test_plain_console_writes_verbatim_without_prefix(capsys):
    # Arrange
    from scitex_logging import getPlainConsole

    plain = getPlainConsole("scitex.console.test.plain")

    # Act
    plain.emit("/worktrees/myagent")
    captured = capsys.readouterr()

    # Assert
    assert captured.out == "/worktrees/myagent\n"


def test_plain_console_never_touches_stderr(capsys):
    # Arrange
    from scitex_logging import getPlainConsole

    plain = getPlainConsole("scitex.console.test.plain-stderr")

    # Act
    plain.emit("protocol frame")
    captured = capsys.readouterr()

    # Assert
    assert captured.err == ""


def _run_plain_boundary(tmp_path, body):
    """Use real pipes: replacing stdout in this process hides print capture."""
    import scitex_logging

    env = {
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.defpath,
        "SCITEX_DIR": str(tmp_path / "state"),
        "TMPDIR": str(tmp_path),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "PYTHONPATH": str(Path(scitex_logging.__file__).resolve().parents[1]),
        "PYTHONDONTWRITEBYTECODE": "1",
        "NO_COLOR": "1",
    }
    script = (
        "import sys,json,io,contextlib\n"
        "def guard(event,args):\n"
        "    if event in {'socket.bind','socket.connect','socket.getaddrinfo'}:\n"
        "        raise RuntimeError('result-boundary controls must remain offline')\n"
        "sys.addaudithook(guard)\n"
        "import scitex_logging as s\n" + body
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return result


@pytest.mark.parametrize("capture", [False, True])
@pytest.mark.parametrize("level", ["info", "critical"])
def test_plain_boundary_json_is_exact_and_never_a_diagnostic(tmp_path, capture, level):
    # Arrange
    script = f"s.configure(level={level!r},enable_file=False,capture_prints={capture!r})\ns.getPlainConsole('owned.json').emit(json.dumps({{'ok':True,'count':2,'label':'Δ plain'}},ensure_ascii=False))"
    # Act
    result = _run_plain_boundary(tmp_path, script)
    # Assert
    assert (result.stdout, json.loads(result.stdout), result.stderr) == (
        '{"ok": true, "count": 2, "label": "Δ plain"}\n',
        {"ok": True, "count": 2, "label": "Δ plain"},
        "",
    )


def test_plain_boundary_aliases_remain_prefix_free_and_uncaptured(tmp_path):
    # Arrange
    script = "s.configure(level='info',enable_file=False,capture_prints=True)\nplain=s.getPlainConsole('owned.paths')\nplain.emit('/owned/one')\nplain.write('/owned/two')\nplain.print('/owned/three')"
    # Act
    result = _run_plain_boundary(tmp_path, script)
    # Assert
    assert (result.stdout, result.stderr) == (
        "/owned/one\n/owned/two\n/owned/three\n",
        "",
    )


@pytest.mark.parametrize("capture", [False, True])
@pytest.mark.parametrize("level", ["info", "critical"])
def test_plain_boundary_does_not_disable_print_diagnostic_capture(
    tmp_path, capture, level
):
    # Arrange
    script = f"s.configure(level={level!r},enable_file=False,capture_prints={capture!r})\ns.getPlainConsole('owned.result').emit('RESULT')\nprint('PRINTED-DIAGNOSTIC')"
    expected = "INFO: PRINTED-DIAGNOSTIC\n" if capture and level == "info" else ""
    # Act
    result = _run_plain_boundary(tmp_path, script)
    # Assert
    assert (result.stdout, result.stderr) == ("RESULT\nPRINTED-DIAGNOSTIC\n", expected)


def test_plain_boundary_capture_started_inside_redirect_restores_owned_streams(
    tmp_path,
):
    # Arrange
    script = "original=sys.stdout\na=io.StringIO()\nb=io.StringIO()\nwith contextlib.redirect_stdout(a):\n    s.configure(level='info',enable_file=False,capture_prints=True)\n    active=sys.stdout\n    s.getPlainConsole().emit('A')\n    with contextlib.redirect_stdout(b):\n        s.getPlainConsole().emit('B')\n    assert sys.stdout is active\n    s.getPlainConsole().emit('C')\nassert sys.stdout is original\noriginal.write(json.dumps({'a':a.getvalue(),'b':b.getvalue()})+'\\n')"
    # Act
    result = _run_plain_boundary(tmp_path, script)
    # Assert
    assert (json.loads(result.stdout), result.stderr) == (
        {"a": "A\nC\n", "b": "B\n"},
        "",
    )


def test_plain_boundary_redirects_after_capture_resolve_current_stream_per_emit(
    tmp_path,
):
    # Arrange
    script = "s.configure(level='info',enable_file=False,capture_prints=True)\nactive=sys.stdout\na=io.StringIO()\nb=io.StringIO()\nplain=s.getPlainConsole()\nwith contextlib.redirect_stdout(a):\n    plain.emit('A')\n    with contextlib.redirect_stdout(b):\n        plain.emit('B')\n    plain.emit('C')\nassert sys.stdout is active\nplain.emit(json.dumps({'a':a.getvalue(),'b':b.getvalue()}))"
    # Act
    result = _run_plain_boundary(tmp_path, script)
    # Assert
    assert (json.loads(result.stdout), result.stderr) == (
        {"a": "A\nC\n", "b": "B\n"},
        "",
    )


def test_plain_boundary_preserves_foreign_stream_with_original_stdout_attribute(
    tmp_path,
):
    # Arrange
    script = "s.configure(level='info',enable_file=False,capture_prints=False)\nclass ForeignStream:\n    def __init__(self):\n        self.original_stdout=io.StringIO()\n        self.destination=io.StringIO()\n        self.flushes=0\n    def write(self,text): return self.destination.write(text)\n    def flush(self): self.flushes+=1\nstream=ForeignStream()\nwith contextlib.redirect_stdout(stream):\n    s.getPlainConsole().emit('foreign-owned')\ns.getPlainConsole().emit(json.dumps({'destination':stream.destination.getvalue(),'decoy':stream.original_stdout.getvalue(),'flushes':stream.flushes}))"
    # Act
    result = _run_plain_boundary(tmp_path, script)
    # Assert
    assert (json.loads(result.stdout), result.stderr) == (
        {"destination": "foreign-owned\n", "decoy": "", "flushes": 1},
        "",
    )


@pytest.mark.parametrize("capture", [False, True])
def test_plain_boundary_real_click_json_result_respects_cli_isolation(
    tmp_path, capture
):
    # Arrange
    script = f"import click\nfrom click.testing import CliRunner\noriginal=sys.stdout\ns.configure(level='info',enable_file=False,capture_prints={capture!r})\n@click.command()\n@click.option('--json','as_json',is_flag=True)\ndef cli(as_json):\n    assert as_json\n    s.getPlainConsole().emit(json.dumps({{'result':'owned-cli','ok':True}}))\nresult=CliRunner().invoke(cli,['--json'])\nassert result.exit_code==0,result.exception\nassert result.stderr==''\noriginal.write(result.stdout)"
    # Act
    result = _run_plain_boundary(tmp_path, script)
    # Assert
    assert (json.loads(result.stdout), result.stderr) == (
        {"result": "owned-cli", "ok": True},
        "",
    )


def test_plain_boundary_nested_owned_capture_keeps_only_print_diagnostics_captured(
    tmp_path,
):
    # Arrange
    script = "from scitex_logging._print_capture import PrintCapture\ns.configure(level='info',enable_file=False,capture_prints=False)\noriginal=sys.stdout\nwith PrintCapture('owned.outer') as outer:\n    with PrintCapture('owned.inner') as inner:\n        s.getPlainConsole().emit('/owned/nested-result')\n        assert sys.stdout is inner and inner.capturing and outer.capturing\n        print('NESTED-DIAGNOSTIC')\n    assert sys.stdout is outer and outer.capturing\nassert sys.stdout is original"
    # Act
    result = _run_plain_boundary(tmp_path, script)
    # Assert
    assert (result.stdout, result.stderr) == (
        "/owned/nested-result\nNESTED-DIAGNOSTIC\n",
        "INFO: NESTED-DIAGNOSTIC\nINFO: NESTED-DIAGNOSTIC\n",
    )


def test_plain_boundary_owned_capture_exception_restores_current_redirect(tmp_path):
    # Arrange
    script = "from scitex_logging._print_capture import PrintCapture\ns.configure(level='info',enable_file=False,capture_prints=False)\noriginal=sys.stdout\nbuf=io.StringIO()\nwith contextlib.redirect_stdout(buf):\n    try:\n        with PrintCapture('owned.exception'):\n            s.getPlainConsole().emit('before-error')\n            raise ValueError('owned-control')\n    except ValueError:\n        pass\n    assert sys.stdout is buf\n    s.getPlainConsole().emit('after-error')\nassert sys.stdout is original\noriginal.write(json.dumps({'captured':buf.getvalue()})+'\\n')"
    # Act
    result = _run_plain_boundary(tmp_path, script)
    # Assert
    assert (json.loads(result.stdout), result.stderr) == (
        {"captured": "before-error\nafter-error\n"},
        "",
    )
