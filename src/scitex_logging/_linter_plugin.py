"""Linter adapter for the logging-owned mandatory output detector."""

from __future__ import annotations

import ast
from pathlib import Path

from ._output._auditor import _FIX_HINT, PRINT_FORBIDDEN_RULES, find_output_calls
from ._output._detector import source_repo


def get_plugin() -> dict:
    # SPI objects exist only at plugin activation, never at runtime import.
    # Guarded: lean installs run without scitex-dev; the Dev loader warns
    # and continues without our rules when activation fails here.
    try:
        from scitex_dev.linter import spi
        from scitex_dev.linter.spi import Issue, Rule
    except ImportError as exc:
        raise ImportError(
            "logging linter plugin needs scitex-dev (install scitex-logging[dev])"
        ) from exc

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

    rules = [rule]
    checkers = [LoggingOutputChecker]
    i007 = _stdlib_logging_rule(spi)
    if i007 is not None:
        rules.append(i007)
        checkers.append(_bind_stdlib_logging_checker(i007, spi))
    return {
        "rules": rules,
        "call_rules": {},
        "axes_hints": {},
        "checkers": checkers,
    }


# STX-I007 — `import logging` (use scitex-logging / the session's injected
# `logger`). Moved from the scitex-dev engine with no behaviour change:
# engine metadata verbatim, one finding per `logging` alias of a bare
# `import`, emitted through `spi.add_issue` (the engine's own gate).
I007_SPEC = dict(
    id="STX-I007",
    severity="warning",
    category="import",
    message="Use `logger` (injected by @stx.session) instead of logging module",
    suggestion="Remove `import logging` and use `logger` from @stx.session injection.",
    requires="scitex",
)


def _stdlib_logging_rule(spi):
    """STX-I007, declared only when the installed engine yields it to us.

    scitex-logging does not pin scitex-dev, and an engine that predates the
    handover would reject the id as a collision — breaking the mandatory
    logging provider. So the rule is declared only when scitex-dev's
    handover table names scitex-logging as its owner; otherwise the engine
    keeps emitting its own copy (identical behaviour either way).
    """
    if getattr(spi, "HANDOVER", {}).get("STX-I007") != "scitex-logging":
        return None
    return spi.Rule(**I007_SPEC)


def _bind_stdlib_logging_checker(rule, spi):

    class StdlibLoggingImportChecker(ast.NodeVisitor):
        category = "import"
        # Package-availability map for the ``requires`` gate; None = detect.
        available = None

        def __init__(self, source_lines, config):
            self.source_lines = source_lines
            self.config = config
            self.issues = []

        def visit_Import(self, node):
            lineno = node.lineno
            source = (
                self.source_lines[lineno - 1].rstrip()
                if 1 <= lineno <= len(self.source_lines)
                else ""
            )
            for alias in node.names:
                if alias.name == "logging":
                    spi.add_issue(
                        self.issues,
                        rule,
                        lineno,
                        node.col_offset,
                        source,
                        self.config,
                        available=self.available,
                    )
            self.generic_visit(node)

    return StdlibLoggingImportChecker
