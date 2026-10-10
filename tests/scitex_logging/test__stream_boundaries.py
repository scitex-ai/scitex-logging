"""Real-pipe regressions for console routing and stream ownership."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _run(tmp_path, body, *, before_import=""):
    env = {
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.defpath,
        "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src"),
        "SCITEX_DIR": str(tmp_path / "state"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "NO_COLOR": "1",
    }
    script = (
        "import sys,io,json,logging,contextlib\n"
        "from pathlib import Path\n"
        "def offline(event,args):\n"
        "    if event in {'socket.bind','socket.connect','socket.getaddrinfo'}:\n"
        "        raise RuntimeError('stream tests must remain offline')\n"
        "sys.addaudithook(offline)\n"
        + before_import
        + "\nimport scitex_logging as s\n"
        + body
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


@pytest.mark.parametrize("console_first", [False, True])
def test_same_name_console_preserves_diagnostic_destination_and_file(
    tmp_path, console_first
):
    # Arrange
    acquisition = (
        "console=s.getConsole('shared'); logger=s.getLogger('shared')"
        if console_first
        else "logger=s.getLogger('shared'); console=s.getConsole('shared')"
    )
    # Act
    result = _run(
        tmp_path,
        "s.configure(log_file='records.log',capture_prints=False)\n"
        + acquisition
        + "\nassert logger is not console\n"
        "assert logger.handlers==[] and logger.propagate\n"
        "assert logger.level==logging.NOTSET\n"
        "logger.warning('DIAGNOSTIC')\nconsole.info('RESULT')\n"
        "record=Path('records.log').read_text()\n"
        "assert 'DIAGNOSTIC' in record and 'RESULT' not in record\n",
    )
    # Assert
    assert (result.stdout, result.stderr) == (
        "INFO: RESULT\n",
        "WARN: DIAGNOSTIC\n",
    )


def test_default_console_tracks_root_and_disable_after_enabled_queries(tmp_path):
    # Arrange
    # Act
    result = _run(
        tmp_path,
        "s.configure(enable_file=False,capture_prints=False)\n"
        "console=s.getConsole('inherited')\n"
        "assert console.level==logging.NOTSET\n"
        "assert console.isEnabledFor(logging.INFO)\nconsole.info('FIRST')\n"
        "s.set_level('error')\n"
        "assert not console.isEnabledFor(logging.INFO)\n"
        "console.info('SUPPRESSED')\nconsole.error('ERROR')\n"
        "logging.getLogger().setLevel(logging.DEBUG)\n"
        "assert console.isEnabledFor(logging.INFO)\nconsole.info('LOWERED')\n"
        "logging.disable(logging.CRITICAL)\n"
        "assert not console.isEnabledFor(logging.ERROR)\n"
        "console.error('DISABLED')\nlogging.disable(logging.NOTSET)\n"
        "assert console.isEnabledFor(logging.INFO)\nconsole.info('REENABLED')",
    )
    # Assert
    assert (result.stdout, result.stderr) == (
        "INFO: FIRST\nERRO: ERROR\nINFO: LOWERED\nINFO: REENABLED\n",
        "",
    )


def test_new_console_respects_quiet_global_level(tmp_path):
    # Arrange
    # Act
    result = _run(
        tmp_path,
        "s.configure(level='error',enable_file=False,capture_prints=False)\n"
        "s.getConsole('new-quiet').info('SUPPRESSED')",
    )
    # Assert
    assert (result.stdout, result.stderr) == ("", "")


def test_explicit_console_level_survives_reacquisition_and_global_changes(tmp_path):
    # Arrange
    # Act
    result = _run(
        tmp_path,
        "s.configure(level='critical',enable_file=False,capture_prints=False)\n"
        "console=s.getConsole('explicit',level=logging.INFO)\n"
        "console.info('EXPLICIT')\ns.set_level('debug')\n"
        "assert s.getConsole('explicit') is console\n"
        "assert console.level==logging.INFO\nconsole.debug('SUPPRESSED')\n"
        "console.setLevel(logging.DEBUG)\nconsole.debug('LOCAL')\n"
        "s.getConsole('explicit',level=logging.ERROR)\n"
        "console.info('SUPPRESSED_AGAIN')\nconsole.error('UPDATED')",
    )
    # Assert
    assert (result.stdout, result.stderr) == (
        "INFO: EXPLICIT\nDEBU: LOCAL\nERRO: UPDATED\n",
        "",
    )


def test_configure_false_releases_capture_and_reuse_refreshes_redirect(tmp_path):
    # Arrange
    # Act
    result = _run(
        tmp_path,
        "from scitex_logging._print_capture import is_print_capture_enabled\n"
        "original=sys.stdout\na=io.StringIO(); b=io.StringIO()\n"
        "with contextlib.redirect_stdout(a):\n"
        "    s.configure(enable_file=False,capture_prints=True)\n"
        "    s.getPlainConsole().emit('A')\n"
        "    s.configure(enable_file=False,capture_prints=False)\n"
        "    assert not is_print_capture_enabled() and sys.stdout is a\n"
        "    print('UNCAPTURED')\n"
        "first=a.getvalue(); a.close()\n"
        "with contextlib.redirect_stdout(b):\n"
        "    s.configure(enable_file=False,capture_prints=True)\n"
        "    s.getConsole('refresh').info('B')\n"
        "    s.configure(enable_file=False,capture_prints=False)\n"
        "    assert sys.stdout is b\n"
        "assert sys.stdout is original\n"
        "s.getPlainConsole().emit(json.dumps([first,b.getvalue()]))",
    )
    # Assert
    assert (json.loads(result.stdout), result.stderr) == (
        ["A\nUNCAPTURED\n", "INFO: B\n"],
        "",
    )


def test_stop_preserves_foreign_redirect_and_inactive_wrapper_can_restart(tmp_path):
    # Arrange
    # Act
    result = _run(
        tmp_path,
        "from scitex_logging._print_capture import PrintCapture\n"
        "s.configure(enable_file=False,capture_prints=False)\n"
        "original=sys.stdout\nforeign=io.StringIO()\n"
        "capture=PrintCapture(); capture.start_capture()\n"
        "with contextlib.redirect_stdout(foreign):\n"
        "    capture.stop_capture()\n"
        "    assert sys.stdout is foreign\nprint('INACTIVE')\n"
        "assert sys.stdout is capture and not capture.capturing\n"
        "capture.start_capture()\n"
        "assert capture.original_stdout is original\n"
        "s.getConsole('restarted').info('RESULT')\n"
        "capture.stop_capture()\nassert sys.stdout is original\n"
        "assert foreign.getvalue()==''",
    )
    # Assert
    assert (result.stdout, result.stderr) == ("INACTIVE\nINFO: RESULT\n", "")


def test_nested_console_and_out_of_order_capture_stop_preserve_stdout(tmp_path):
    # Arrange
    # Act
    result = _run(
        tmp_path,
        "from scitex_logging._print_capture import PrintCapture\n"
        "s.configure(enable_file=False,capture_prints=False)\n"
        "original=sys.stdout\nouter=PrintCapture(); outer.start_capture()\n"
        "inner=PrintCapture(); inner.start_capture()\n"
        "s.getConsole('nested').info('NESTED')\n"
        "outer.stop_capture()\nassert sys.stdout is inner\n"
        "inner.stop_capture()\nassert sys.stdout is original",
    )
    # Assert
    assert (result.stdout, result.stderr) == ("INFO: NESTED\n", "")


def test_reentering_same_capture_does_not_release_outer_context(tmp_path):
    # Arrange
    # Act
    result = _run(
        tmp_path,
        "from scitex_logging._print_capture import PrintCapture\n"
        "s.configure(enable_file=False,capture_prints=False)\n"
        "original=sys.stdout\ncapture=PrintCapture()\n"
        "with capture:\n"
        "    with capture:\n"
        "        s.getPlainConsole().emit('INNER')\n"
        "    assert sys.stdout is capture and capture.capturing\n"
        "    s.getConsole('same-context').info('OUTER')\n"
        "assert sys.stdout is original and not capture.capturing",
    )
    # Assert
    assert (result.stdout, result.stderr) == ("INNER\nINFO: OUTER\n", "")


@pytest.mark.parametrize("flush", [False, True])
def test_plain_console_caller_stream_and_flush_are_exact(tmp_path, flush):
    # Arrange
    # Act
    result = _run(
        tmp_path,
        "s.configure(level='critical',enable_file=False,capture_prints=True)\n"
        "class Foreign(io.StringIO):\n"
        "    flushes=0\n"
        "    def flush(self): self.flushes+=1\n"
        "    original_stdout=io.StringIO()\n"
        "stream=Foreign()\n"
        f"s.getPlainConsole().emit('Δ frame',stream=stream,flush={flush!r})\n"
        "s.getPlainConsole().emit(json.dumps([stream.getvalue(),"
        "stream.flushes,stream.original_stdout.getvalue()]))",
    )
    # Assert
    assert (json.loads(result.stdout), result.stderr) == (
        ["Δ frame\n", int(flush), ""],
        "",
    )


@pytest.mark.parametrize("failure", ["write", "flush"])
def test_plain_console_preserves_caller_stream_failures(tmp_path, failure):
    # Arrange
    # Act
    result = _run(
        tmp_path,
        "class Broken:\n"
        "    def write(self,text):\n"
        f"        if {failure!r}=='write': raise OSError('write-failed')\n"
        "        return len(text)\n"
        "    def flush(self): raise OSError('flush-failed')\n"
        "try:\n"
        "    s.getPlainConsole().emit('frame',stream=Broken())\n"
        "except OSError as exc:\n"
        f"    assert str(exc)=={failure + '-failed'!r}\n"
        "else:\n"
        "    raise AssertionError('output failure was suppressed')",
    )
    # Assert
    assert (result.stdout, result.stderr) == ("", "")


def test_import_preserves_preconfigured_root_and_stdout(tmp_path):
    # Arrange
    # Act
    result = _run(
        tmp_path,
        "assert logging.getLogger() is root and s.getLogger() is root\n"
        "assert callable(root.success) and callable(root.fail)\n"
        "assert root.handlers==[handler] and root.level==logging.ERROR\n"
        "assert handler.level==logging.WARNING and handler.close_calls==0\n"
        "assert sys.stdout is foreign\n"
        "root.success('SUPPRESSED_SUCCESS'); root.fail('SUPPRESSED_FAIL')\n"
        "root.error('DIAGNOSTIC')\n"
        "assert destination.getvalue()=='DIAGNOSTIC\\n'\n"
        "s.getLogger('application').success('SUPPRESSED')\n"
        "s.getPlainConsole().emit('RESULT')\n"
        "sys.stdout=original\n"
        "s.getPlainConsole().emit(json.dumps(foreign.getvalue()))",
        before_import=(
            "original=sys.stdout; foreign=io.StringIO(); sys.stdout=foreign\n"
            "root=logging.getLogger(); destination=io.StringIO()\n"
            "class TrackedHandler(logging.StreamHandler):\n"
            "    close_calls=0\n"
            "    def close(self):\n"
            "        self.close_calls+=1\n"
            "        super().close()\n"
            "handler=TrackedHandler(destination)\n"
            "handler.setLevel(logging.WARNING); root.addHandler(handler)\n"
            "root.setLevel(logging.ERROR)\n"
        ),
    )
    # Assert
    assert (json.loads(result.stdout), result.stderr) == ("RESULT\n", "")


def test_explicit_configuration_closes_replaced_file_handler(tmp_path):
    # Arrange
    # Act
    result = _run(
        tmp_path,
        "s.configure(enable_file=False,capture_prints=False)\n"
        "assert handler not in root.handlers\n"
        "assert handler.stream is None and old_stream.closed\n"
        "assert root.level==logging.INFO and len(root.handlers)==1",
        before_import=(
            "root=logging.getLogger(); handler=logging.FileHandler('old.log')\n"
            "old_stream=handler.stream\n"
            "root.addHandler(handler); root.setLevel(logging.WARNING)\n"
        ),
    )
    # Assert
    assert (result.stdout, result.stderr) == ("", "")
