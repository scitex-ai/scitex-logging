"""Real coverage subprocesses write separate, populated package data files."""

import os
import subprocess
import sys
from pathlib import Path

from coverage import CoverageData


def test_subprocesses_preserve_separate_coverage_records(tmp_path):
    # Arrange
    root = Path(__file__).resolve().parents[2]
    environment = dict(
        os.environ,
        HOME=str(tmp_path),
        COVERAGE_PROCESS_START=str(root / "pyproject.toml"),
        COVERAGE_FILE=str(tmp_path / ".coverage"),
    )
    # This fixture explicitly tests the package configuration file.
    environment.pop("COVERAGE_PROCESS_CONFIG", None)
    command = [
        sys.executable,
        "-I",
        "-c",
        "import scitex_logging; scitex_logging.getDiagnostic('coverage-child')",
    ]
    children = [
        subprocess.Popen(
            command,
            env=environment,
            cwd=tmp_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(2)
    ]
    # Act
    streams = [child.communicate(timeout=20) for child in children]
    shards = sorted(tmp_path.glob(".coverage.*"))
    measured = []
    for shard in shards:
        data = CoverageData(basename=str(shard))
        data.read()
        measured.append(
            any(
                data.lines(name)
                for name in data.measured_files()
                if Path(name).name == "_diagnostic.py"
            )
        )
    # Assert
    assert (
        [child.returncode for child in children],
        streams,
        len(shards),
        measured,
    ) == (
        [0, 0],
        [("", ""), ("", "")],
        2,
        [True, True],
    )
