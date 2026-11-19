"""STX-I007 (`import logging`) — owned by scitex-logging, declared on handover.

Moved from the scitex-dev engine with no behaviour change. The rule is only
declared when the installed scitex-dev's handover table names scitex-logging
as its owner (scitex-dev >= 0.65.0); with an older engine the engine keeps
emitting its own copy, so these tests skip there.
"""

import ast

import pytest
from scitex_dev.linter import spi
from scitex_dev.linter.config import LinterConfig

from scitex_logging._linter_plugin import (
    I007_SPEC,
    _bind_stdlib_logging_checker,
    get_plugin,
)

pytestmark = pytest.mark.skipif(
    getattr(spi, "HANDOVER", {}).get("STX-I007") != "scitex-logging",
    reason="installed scitex-dev predates the STX-I007 handover",
)


class _Checker(_bind_stdlib_logging_checker(spi.Rule(**I007_SPEC))):
    # The rule's `requires` (umbrella scitex) may be absent here.
    available = {"scitex": True}


def _findings(source):
    checker = _Checker(source.splitlines(), LinterConfig())
    checker.visit(ast.parse(source))
    return [(i.rule.id, i.line) for i in checker.issues]


def test_plugin_declares_i007_with_engine_metadata():
    # Arrange
    from scitex_dev.linter.rules import ALL_RULES

    # Act
    declared = {r.id: r for r in get_plugin()["rules"]}.get("STX-I007")
    # Assert — delete together with the engine copy once the handover ends.
    assert declared == ALL_RULES["STX-I007"]


def test_bare_import_logging_is_reported_once_per_alias():
    # Arrange
    source = "import logging\nimport os, logging as lg\nfrom logging import getLogger\n"
    # Act
    found = _findings(source)
    # Assert
    assert found == [("STX-I007", 1), ("STX-I007", 2)]


def test_stx_allow_comment_suppresses_i007():
    # Arrange
    source = "import logging  # stx-allow: STX-I007\n"
    # Act
    found = _findings(source)
    # Assert
    assert found == []
