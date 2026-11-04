"""Authored source discovery follows Git without weakening output policy."""

import subprocess
from types import SimpleNamespace

import pytest

from scitex_logging._output._auditor import check_ps220_no_print
from scitex_logging._output._detector import _src_files, find_output_calls
from scitex_logging._output._hook import check_payload
from scitex_logging._output._inventory import git_paths


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True
    )


def _write(repo, relative):
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("print('authored')\n")
    return path


def _init(repo):
    _git(repo, "init", "-q")
    _commit(repo, "baseline", "--allow-empty")


def _commit(repo, message, *args):
    _git(
        repo,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        *args,
        "-qm",
        message,
    )


def test_git_inventory_excludes_dependencies_but_keeps_all_authored_source(tmp_path):
    # Arrange
    _init(tmp_path)
    (tmp_path / ".gitignore").write_text("node_modules/\nignored.py\n")
    tracked = _write(tmp_path, "src/pkg/ignored.py")
    hidden_tracked = _write(tmp_path, "src/.private/ignored.py")
    _git(tmp_path, "add", "-f", str(tracked), str(hidden_tracked))
    hidden_untracked = _write(tmp_path, "src/pkg/.authored/script.py")
    ordinary = _write(tmp_path, "src/pkg/scripts/tool.py")
    _write(tmp_path, "src/pkg/frontend/node_modules/katex/generate_fonts.py")
    (tmp_path / "src/pkg/.gitignore").write_text("generated/\n")
    _write(tmp_path, "src/pkg/generated/output.py")
    _write(tmp_path, "scripts/outside.py")
    deleted = _write(tmp_path, "src/pkg/deleted.py")
    _git(tmp_path, "add", str(deleted))
    deleted.unlink()
    # Act
    files = _src_files(tmp_path)
    # Assert
    findings = []
    check_ps220_no_print(
        tmp_path, lambda *args: args, findings, config=SimpleNamespace()
    )
    assert (
        files == sorted([tracked, hidden_tracked, hidden_untracked, ordinary])
        and len(findings) == 4
        and {item[1].rsplit(":", 1)[0] for item in findings}
        == {str(path) for path in files}
    )


@pytest.mark.parametrize(
    "name",
    [
        "space name.py",
        "tab\tname.py",
        "line\nname.py",
        'quote"name.py',
        "back\\name.py",
        "日本語.py",
        "byte\udcff.py",
    ],
)
def test_git_paths_preserve_unusual_filenames_and_deduplicate(tmp_path, name):
    # Arrange
    _init(tmp_path)
    path = _write(tmp_path, "src/pkg/" + name)
    _git(tmp_path, "add", str(path))
    path.write_text("print('modified')\n")
    # Act
    files = _src_files(tmp_path)
    findings = check_payload({"cwd": str(tmp_path), "tool_name": "Bash"})
    # Assert
    assert files == [path] and len(findings) == 1 and str(path) in findings[0]


def test_linked_worktree_and_nested_project_use_the_actual_source_subtree(tmp_path):
    # Arrange
    repo = tmp_path / "repo"
    repo.mkdir()
    _init(repo)
    authored = _write(repo, "leaf/src/pkg/.hidden.py")
    _write(repo, "src/other.py")
    _git(repo, "add", ".")
    _commit(repo, "sources")
    worktree = tmp_path / "linked worktree"
    _git(repo, "worktree", "add", "--detach", str(worktree))
    # Act
    files = _src_files(worktree / "leaf")
    # Assert
    assert (worktree / ".git").is_file() and files == [
        worktree / authored.relative_to(repo)
    ]


def test_changed_hook_does_not_audit_unchanged_tracked_source(tmp_path):
    # Arrange
    _init(tmp_path)
    unchanged = _write(tmp_path, "src/pkg/old.py")
    _git(tmp_path, "add", ".")
    _commit(tmp_path, "existing source")
    changed = _write(tmp_path, "src/pkg/.new.py")
    # Act
    files = _src_files(tmp_path)
    findings = check_payload({"cwd": str(tmp_path), "tool_name": "Bash"})
    # Assert
    assert (
        files == sorted([unchanged, changed])
        and len(findings) == 1
        and str(changed) in findings[0]
    )


def test_lexical_symlink_does_not_grant_backend_ownership(tmp_path):
    # Arrange
    _init(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "other"\n')
    target = _write(tmp_path, "foreign.py")
    path = tmp_path / "src/scitex_logging/_logger.py"
    path.parent.mkdir(parents=True)
    path.symlink_to(target)
    # Act
    files = _src_files(tmp_path)
    sites = find_output_calls(
        "import logging; logging.getLogger(__name__)",
        repo=tmp_path,
        filepath=files[0],
    )
    # Assert
    assert files == [path] and files[0] != target and len(sites) == 1


def test_git_enumeration_errors_cannot_silently_omit_source(tmp_path):
    # Arrange
    repo = tmp_path
    # Act
    # Assert
    with pytest.raises(OSError, match="enumerate Git source"):
        git_paths(repo, "ls-files", "-z")
