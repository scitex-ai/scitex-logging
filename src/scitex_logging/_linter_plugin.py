"""Linter adapter for the logging-owned mandatory output detector."""

from __future__ import annotations

import ast
from pathlib import Path

from ._output_auditor import _FIX_HINT, PRINT_FORBIDDEN_RULES, find_output_calls
from ._output_detector import source_repo


def get_plugin() -> dict:
    # SPI objects exist only at plugin activation, never at runtime import.
    from scitex_dev.linter.spi import Issue, Rule

    rule = Rule(
        id="PS-220",
        severity="error",
        category="logging",
        message=PRINT_FORBIDDEN_RULES[0][2],
        suggestion=_FIX_HINT,
        requires="",
    )

    class LoggingOutputChecker(ast.NodeVisitor):
        mandatory = True
        accepts_filepath = True
        category = "logging"

        def __init__(self, source_lines, config, *, filepath="<stdin>"):
            del config
            self.source_lines = source_lines
            self.filepath = filepath
            self.issues = []

        def visit(self, tree):
            del tree
            repo = source_repo(self.filepath)
            if repo is None:
                return
            text = "\n".join(self.source_lines)
            for site in find_output_calls(
                text, repo=repo, filepath=Path(self.filepath).absolute()
            ):
                line = site.call.lineno
                source = (
                    self.source_lines[line - 1]
                    if line <= len(self.source_lines)
                    else ""
                )
                self.issues.append(
                    Issue(
                        rule=rule,
                        line=line,
                        col=site.call.col_offset,
                        source_line=source,
                    )
                )

    return {
        "rules": [rule],
        "call_rules": {},
        "axes_hints": {},
        "checkers": [LoggingOutputChecker],
    }
