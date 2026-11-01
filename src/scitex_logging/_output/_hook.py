"""Native edit and changed-source hooks sharing PS-220's exact detector."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

from ._detector import find_output_calls, source_repo


def _inspect(path, text):
    repo = source_repo(str(path))
    if repo is None:
        return []
    try:
        ast.parse(text)
    except SyntaxError:
        return [f"PS-220: cannot parse proposed source: {path}"]
    return [
        f"PS-220: {path}:{site.call.lineno}: {site.kind}; use scitex-logging"
        for site in find_output_calls(text, repo=repo, filepath=path)
    ]


def check_payload(payload):
    """Return source violations; never import or execute the edited module."""
    cwd = Path(payload.get("cwd") or Path.cwd()).resolve()
    tool = payload.get("tool_name", "")
    data = payload.get("tool_input") or payload.get("arguments") or {}
    filename = data.get("file_path") or data.get("path")
    if tool in ("Write", "write_file", "Edit", "MultiEdit", "patch") and filename:
        path = Path(filename)
        path = path if path.is_absolute() else cwd / path
        if path.suffix != ".py":
            return []
        if tool in ("Write", "write_file"):
            text = data.get("content", "")
        else:
            text = path.read_text()
            edits = data.get("edits", [data])
            for edit in edits:
                old, new = edit.get("old_string", ""), edit.get("new_string", "")
                if not old or old not in text:
                    return [f"PS-220: cannot verify proposed edit: {path}"]
                text = text.replace(old, new, -1 if edit.get("replace_all") else 1)
        return _inspect(path, text)
    if tool not in ("Bash", "terminal", "apply_patch"):
        return []
    root = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if root.returncode:
        return []
    repo = Path(root.stdout.strip())
    paths = set()
    for args in (
        ["diff", "--name-only", "--diff-filter=ACMR", "-z", "HEAD"],
        ["ls-files", "--others", "--exclude-standard", "-z"],
    ):
        result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
        if result.returncode:
            return ["PS-220: cannot enumerate changed source"]
        paths.update(result.stdout.decode().rstrip("\0").split("\0"))
    findings = []
    for relative in sorted(paths):
        path = repo / relative
        if relative.startswith("src/") and path.suffix == ".py" and path.is_file():
            findings.extend(_inspect(path, path.read_text()))
    return findings


def main():
    import scitex_logging as slogging

    try:
        findings = check_payload(json.load(sys.stdin))
    except (ValueError, OSError, TypeError) as exc:
        findings = [f"PS-220: could not verify tool source ({type(exc).__name__})"]
    for finding in findings:
        slogging.getLogger(__name__).error(finding)
    return 2 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
