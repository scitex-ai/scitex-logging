"""Logging linter source scope follows aliases without executing source."""

import ast

import pytest

from scitex_logging._linter_plugin import get_plugin

from ._source_alias import _alias


@pytest.mark.parametrize("kind", ["directory", "file"])
def test_linter_uses_same_source_scope_for_aliases(tmp_path, kind):
    # Arrange
    alias, source = _alias(tmp_path, kind)
    checker = get_plugin()["checkers"][0](["print('raw')"], None, filepath=str(alias))
    # Act
    checker.visit(ast.parse("print('raw')"))
    # Assert
    assert ([issue.rule.id for issue in checker.issues], source.read_text()) == (
        ["PS-220"],
        "value = 1\n",
    )
