"""Requested LLM CLI output survives thresholds and owned print capture."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scitex_logging.llm import actions_to_jsonl, actions_to_log, extract_actions, load, to_mermaid


def _run(tmp_path, argv, level, capture):
    import scitex_logging

    env = {
        "PATH": str(Path(sys.executable).parent) + os.pathsep + os.defpath,
        "SCITEX_DIR": str(tmp_path / "state"),
        "TMPDIR": str(tmp_path),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "SCITEX_LOGGING_LEVEL": level,
        "PYTHONPATH": str(Path(scitex_logging.__file__).resolve().parents[1]),
        "PYTHONDONTWRITEBYTECODE": "1",
        "NO_COLOR": "1",
    }
    script = (
        "import sys\n"
        "def guard(event,args):\n"
        "    if event in {'socket.bind','socket.connect','socket.getaddrinfo'}:\n"
        "        raise RuntimeError('CLI fixture validation must remain offline')\n"
        "sys.addaudithook(guard)\n"
        "import scitex_logging as s\n"
        f"s.configure(level={level!r},enable_file=False,capture_prints={capture!r})\n"
        "from scitex_logging.llm.__main__ import main\n"
        f"sys.argv=['scitex_logging.llm',*{argv!r}]\n"
        "sys.exit(main())\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=tmp_path, env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return result


def _payload(command, rich_session):
    if command == "summary":
        argv = [command, str(rich_session)]
        expected = json.dumps(load(rich_session).summary(), indent=2)
    elif command == "dag":
        argv = [command, str(rich_session)]
        expected = to_mermaid(load(rich_session))
    else:
        fmt = command.removeprefix("actions-")
        argv = ["actions", str(rich_session), "--format", fmt]
        actions = extract_actions(rich_session)
        expected = {
            "log": lambda: actions_to_log(actions),
            "jsonl": lambda: actions_to_jsonl(actions),
            "json": lambda: json.dumps([action.to_dict() for action in actions], indent=2),
        }[fmt]()
    return argv, expected


@pytest.mark.parametrize("level", ["info", "critical"])
@pytest.mark.parametrize("capture", [False, True])
@pytest.mark.parametrize("command", ["summary", "dag", "actions-log", "actions-jsonl", "actions-json"])
def test_requested_payload_is_exact_uncaptured_and_independent_of_level(
    tmp_path, rich_session, level, capture, command,
):
    # Arrange
    argv, expected = _payload(command, rich_session)
    # Act
    result = _run(tmp_path, argv, level, capture)
    # Assert
    assert (result.stdout, result.stderr) == (expected + "\n", "")


def _artifact(command, tmp_path, rich_session, claude_dir):
    target = tmp_path / ("artifacts" if command == "scripts" else f"{command}.out")
    if command in {"spa", "dashboard"}:
        argv = [command, "--output", str(target), "--claude-dir", str(claude_dir)]
    else:
        argv = [command, str(rich_session), "--output", str(target)]
    prefix = {"render": "Rendered", "scripts": "Scripts", "dashboard": "Dashboard",
              "spa": "SPA", "actions": "Written"}[command]
    suffix = f" ({len(extract_actions(rich_session))} actions)" if command == "actions" else ""
    return argv, target, f"{prefix}: {target}{suffix}\n"


@pytest.mark.parametrize("level", ["info", "critical"])
@pytest.mark.parametrize("capture", [False, True])
@pytest.mark.parametrize("command", ["render", "scripts", "dashboard", "spa", "actions"])
def test_requested_artifact_result_remains_visible_without_diagnostic_duplication(
    tmp_path, rich_session, claude_dir, level, capture, command,
):
    # Arrange
    argv, target, expected = _artifact(command, tmp_path, rich_session, claude_dir)
    # Act
    result = _run(tmp_path, argv, level, capture)
    # Assert
    assert (result.stdout, result.stderr, target.exists()) == (expected, "", True)


def test_default_scripts_path_is_a_requested_artifact_result(tmp_path, rich_session):
    # Arrange
    expected = Path(str(rich_session.with_suffix("")) + "_scripts")
    # Act
    result = _run(tmp_path, ["scripts", str(rich_session)], "critical", True)
    # Assert
    assert (result.stdout, result.stderr, (expected / "index.html").is_file()) == (
        f"Scripts: {expected}\n", "", True,
    )
