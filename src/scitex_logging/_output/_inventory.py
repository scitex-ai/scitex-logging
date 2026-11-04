"""Logging-owned, lexical Git source inventory shared by audit and hooks."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def git_paths(repo: Path, *args: str) -> set[str]:
    """Read NUL-delimited paths without losing whitespace or filename bytes."""
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if result.returncode:
        raise OSError("cannot enumerate Git source")
    return {os.fsdecode(path) for path in result.stdout.split(b"\0") if path}


def source_files(repo: Path) -> list[Path]:
    """Include tracked and nonignored untracked Python, including hidden files."""
    src = Path(repo) / "src"
    if not src.is_dir():
        return []
    try:
        inside = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
        )
    except FileNotFoundError:
        inside = None
    if inside is None or inside.returncode or inside.stdout.strip() != b"true":
        return sorted(path for path in src.rglob("*.py") if path.is_file())
    paths = git_paths(
        repo,
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
        "--",
        "src/",
    )
    return sorted(
        repo / path
        for path in paths
        if Path(path).suffix == ".py" and (repo / path).is_file()
    )
