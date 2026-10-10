"""Owned project/linter adapters and runtime dependency boundaries."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from scitex_logging._audit_plugin import get_plugin
from scitex_logging._output.auditor import PRINT_FORBIDDEN_RULES, check_ps220_no_print


def _dev_linter_spi() -> bool:
    # scitex-dev>=0.62.4.dev0 promotes Issue/ProviderReplacement to the
    # public linter SPI; older releases raise ImportError at plugin load
    # (the Dev loader warns and continues without our rules).
    try:
        from scitex_dev.linter.spi import Issue, Rule  # noqa: F401
    except ImportError:
        return False
    return True


_requires_dev_linter_spi = pytest.mark.skipif(
    not _dev_linter_spi(),
    reason="needs scitex-dev>=0.62.4.dev0 linter SPI (Issue)",
)


@dataclass
class Finding:
    rule: str
    where: str
    detail: str


def _source(repo, relative, text):
    path = repo / "src" / "pkg" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_project_factory_exposes_the_shared_error_rule():
    # Arrange
    expected_checker = check_ps220_no_print
    # Act
    plugin = get_plugin()
    # Assert
    assert (
        plugin == {"rules": PRINT_FORBIDDEN_RULES, "checks": [expected_checker]}
        and plugin["rules"][0][3] == "E"
    )


def test_project_adapter_reports_all_nested_prints_without_importing(tmp_path):
    # Arrange
    for label in ("ordinary", "tests", "scripts", "examples", "docs"):
        _source(
            tmp_path,
            label + "/output.py",
            "raise RuntimeError('never import')\nprint('{}')\n",
        )
    findings = []
    # Act
    check_ps220_no_print(tmp_path, Finding, findings, config=SimpleNamespace())
    # Assert
    assert len(findings) == 5 and all(
        item.rule == "PS-220" and "builtin print" in item.detail for item in findings
    )


@pytest.mark.parametrize("setting", ["off", "warning", "error"])
def test_legacy_severity_and_skip_settings_never_weaken_source_rule(tmp_path, setting):
    # Arrange
    _source(tmp_path, "output.py", "print('{}')\n")
    config = SimpleNamespace(enforce_logging=setting, skip={"PS-220"})
    findings = []
    # Act
    check_ps220_no_print(tmp_path, Finding, findings, config=config)
    # Assert
    assert (
        len(findings) == 3
        and sum("builtin print" in item.detail for item in findings) == 1
    )


@pytest.mark.parametrize("text", ["print(\n", "\udcff"])
def test_unparseable_or_unreadable_source_fails_closed(tmp_path, text):
    # Arrange
    path = tmp_path / "src" / "pkg" / "output.py"
    path.parent.mkdir(parents=True)
    path.write_bytes(text.encode("utf-8", errors="surrogateescape"))
    findings = []
    # Act
    check_ps220_no_print(tmp_path, Finding, findings, config=SimpleNamespace())
    # Assert
    assert (
        len(findings) == 1
        and findings[0].rule == "PS-220"
        and "Cannot" in findings[0].detail
    )


def test_runtime_and_project_factory_imports_do_not_import_dev(tmp_path):
    # Arrange
    source = Path(__file__).resolve().parents[2] / "src"
    script = (
        f"import sys, json, logging; sys.path.insert(0, {str(source)!r})\n"
        "logging.basicConfig()\n"
        "import scitex_logging\n"
        "from scitex_logging._audit_plugin import get_plugin\n"
        "get_plugin()\n"
        "sys.stdout.write(json.dumps([name for name in sys.modules if name.startswith('scitex_dev')]))\n"
    )
    env = dict(os.environ, HOME=str(tmp_path))
    # Act
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    # Assert
    assert json.loads(result.stdout) == [] and result.stderr == ""


@_requires_dev_linter_spi
def test_linter_adapter_uses_public_spi_and_shared_detector(tmp_path):
    # Arrange
    from scitex_logging._linter_plugin import get_plugin as get_linter_plugin

    path = _source(tmp_path, "scripts/output.py", "print('{}')  # noqa: PS-220\n")
    source_lines = path.read_text().splitlines()
    plugin = get_linter_plugin()
    checker_class = plugin["checkers"][0]
    checker = checker_class(
        source_lines, SimpleNamespace(disable=["PS-220"]), filepath=str(path)
    )
    # Act
    checker.visit(ast.parse(path.read_text()))
    # Assert
    assert (
        checker_class.mandatory,
        checker_class.accepts_filepath,
        plugin["rules"][0].id,
        plugin["rules"][0].severity,
        [(item.rule.id, item.line) for item in checker.issues],
    ) == (True, True, "PS-220", "error", [("PS-220", 1)])


@_requires_dev_linter_spi
def test_project_and_linter_report_identical_primitive_locations(tmp_path):
    # Arrange
    from scitex_logging._linter_plugin import get_plugin as get_linter_plugin

    path = _source(
        tmp_path,
        "output.py",
        "import builtins as b\nb.print('{}')\nimport logging\nlogging.info('status')\n",
    )
    findings = []
    checker_class = get_linter_plugin()["checkers"][0]
    checker = checker_class(path.read_text().splitlines(), None, filepath=str(path))
    # Act
    check_ps220_no_print(tmp_path, Finding, findings, config=SimpleNamespace())
    checker.visit(ast.parse(path.read_text()))
    # Assert
    assert (
        [int(item.where.rsplit(":", 1)[1]) for item in findings]
        == [item.line for item in checker.issues]
        == [2, 4]
    )


@_requires_dev_linter_spi
def test_linter_adapter_keeps_repository_tests_outside_source_scope(tmp_path):
    # Arrange
    from scitex_logging._linter_plugin import get_plugin as get_linter_plugin

    path = tmp_path / "tests" / "test_output.py"
    checker_class = get_linter_plugin()["checkers"][0]
    checker = checker_class(["print('fixture')"], None, filepath=str(path))
    # Act
    checker.visit(ast.parse("print('fixture')"))
    # Assert
    assert checker.issues == []


def test_declared_entry_points_target_owned_factories():
    # Arrange
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    root = Path(__file__).resolve().parents[2]
    # Act
    points = tomllib.loads((root / "pyproject.toml").read_text())["project"][
        "entry-points"
    ]
    # Assert
    assert (
        points["scitex_dev.audit.project"]["scitex-logging"],
        points["scitex_dev.linter.plugins"]["scitex-logging"],
    ) == (
        "scitex_logging._audit_plugin:get_plugin",
        "scitex_logging._linter_plugin:get_plugin",
    )
