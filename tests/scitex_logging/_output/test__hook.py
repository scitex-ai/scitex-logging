"""Hooks, linter, and audit share a logging-owned source policy."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scitex_logging._hook_rules import provide
from scitex_logging._output._detector import find_output_calls
from scitex_logging._output._hook import check_payload


@pytest.mark.parametrize(
    "source",
    [
        "import logging as log; log.basicConfig()",
        "from logging import StreamHandler as Handler; Handler()",
        "print('raw')",
        "import logging; logging.getLogger(__name__)",
    ],
)
def test_native_write_rejects_shared_output_primitives(tmp_path, source):
    # Arrange
    path = tmp_path / "src/pkg/module.py"
    path.parent.mkdir(parents=True)
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Write",
        "tool_input": {"file_path": str(path), "content": source},
    }
    # Act
    findings = check_payload(payload)
    # Assert
    assert findings and len(findings) == len(find_output_calls(source))


def test_native_edit_checks_the_complete_proposed_source(tmp_path):
    # Arrange
    path = tmp_path / "src/pkg/module.py"
    path.parent.mkdir(parents=True)
    path.write_text("import logging\nvalue = 1\n")
    # Act
    findings = check_payload(
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(path),
                "old_string": "value = 1",
                "new_string": "logging.StreamHandler()",
            },
        }
    )
    # Assert
    assert len(findings) == 1 and path.read_text().endswith("value = 1\n")


def test_shell_hook_checks_untracked_source_without_executing_it(tmp_path):
    # Arrange
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "--allow-empty",
            "-qm",
            "baseline",
        ],
        check=True,
    )
    path = tmp_path / "src/pkg/module.py"
    path.parent.mkdir(parents=True)
    path.write_text(
        "import logging\nlogging.StreamHandler()\nraise RuntimeError('must not execute')\n"
    )
    # Act
    findings = check_payload(
        {"cwd": str(tmp_path), "tool_name": "Bash", "tool_input": {"command": "true"}}
    )
    # Assert
    assert len(findings) == 1 and "logging.StreamHandler" in findings[0]


def test_hook_binding_returns_deny_for_bad_source(tmp_path):
    # Arrange
    package = Path(__file__).resolve().parents[3]
    path = tmp_path / "src/pkg/module.py"
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": str(path), "content": "print('raw')"},
    }
    env = dict(os.environ, HOME=str(tmp_path), PYTHONPATH=str(package / "src"))
    # Act
    result = subprocess.run(
        [sys.executable, "-m", "scitex_logging._output._hook"],
        input=json.dumps(payload),
        env=env,
        capture_output=True,
        text=True,
    )
    # Assert
    assert result.returncode == 2 and "PS-220" in result.stderr


def test_leaf_provider_ships_both_hook_bindings():
    # Arrange
    rules = provide()
    root = Path(__file__).resolve().parents[3] / "src/scitex_logging"
    # Act
    bindings = [(r.provider, r.severity, (root / r.script).is_file()) for r in rules]
    # Assert
    assert bindings == [("scitex-logging", "deny", True)] * 2
