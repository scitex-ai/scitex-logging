"""Logging-owned mandatory PS-220 policy and project audit adapter.

Both auditor interfaces call the same detector. Developer tooling supplies
its result classes and config only when it activates this provider; importing
the runtime logging package never imports scitex-dev.
"""

from __future__ import annotations

import ast
from pathlib import Path

from ._backend import owns_logging_backend
from ._detector import (
    _output_calls as _output_calls,
)
from ._detector import (
    _OutputCall as _OutputCall,
)
from ._detector import (
    _src_files as _src_files,
)
from ._detector import (
    find_output_calls,
)

_DEFAULT_SEVERITY = "E"
_CONFIG_ERROR_SEVERITY = "E"
_FIX_HINT = (
    "Use scitex-logging: `import scitex_logging as slogging; "
    "log = slogging.getLogger(__name__)` for diagnostics on stderr, then "
    "`log.info(...)` / `log.warning(...)` / `log.error(...)` / `log.success(...)`. "
    "For human output on stdout use `slogging.getConsole(__name__)`; for "
    "prefix-free protocol stdout or caller-owned streams use "
    "`slogging.getPlainConsole(__name__).emit(payload, stream=stream)`. "
    "Omit stream for stdout. JSON and explicit file streams do not exempt "
    "builtin print. PS-220 has no configuration or comment bypass."
)

PRINT_FORBIDDEN_RULES = [
    (
        "PS-220",
        "§2",
        "Every Python file under src must use scitex-logging for output; "
        "builtin print/pprint, Rich Console.print and stdlib logger acquisition "
        "are forbidden, including JSON, caller-owned streams and bundled "
        "scripts/tests/examples/docs. Only individually proved stdlib operations "
        "in the owning logger backend are permitted. " + _FIX_HINT,
        _DEFAULT_SEVERITY,
        "source-uses-print-not-scitex-logging",
    ),
]


def resolve_ps220_severity(config) -> str:
    """Historical settings cannot weaken the mandatory error tier."""
    del config
    return _DEFAULT_SEVERITY


def should_flag(tree: ast.AST, call: ast.Call) -> tuple[bool, str]:
    """Compatibility discriminator: raw print has no transport exemptions."""
    del tree, call
    return True, "raw output bypasses the package-owned logging and stream APIs"


def _report_config_errors(repo: Path, config, violation_cls, out: list) -> None:
    # Activation-only integration: avoid a runtime dependency cycle.
    def emit(where, detail):
        out.append(violation_cls("PS-220", where, detail))

    where = str(repo / ".scitex/dev/config.yaml")
    if getattr(config, "exemption_errors", ()):
        try:
            from scitex_dev._cli.audit._project._exemption_config_errors import (
                report_exemption_config_errors,
            )
        except ImportError as exc:
            raise ImportError(
                "PS-220 exemption reporting needs scitex-dev "
                "(install scitex-logging[dev])"
            ) from exc

        report_exemption_config_errors(repo, config, "PS-220", emit)
    if getattr(config, "enforce_logging", None) is not None:
        emit(
            where,
            "`audit.enforce-logging` is retired: PS-220 is mandatory "
            "error tier and has no project-level severity switch. Remove the declaration.",
        )
    for notice in tuple(getattr(config, "enforce_logging_errors", ()) or ()):
        emit(
            where,
            f"Invalid `audit.enforce-logging` declaration — {notice} "
            "PS-220 remains at mandatory error severity (E).",
        )
    if "PS-220" in (getattr(config, "skip", ()) or ()):
        emit(where, "PS-220 cannot be skipped: remove it from audit.skip-rules.")


def check_ps220_no_print(
    repo: Path, violation_cls: type, out: list, *, config=None
) -> None:
    """Append error-tier source findings without importing audited code."""
    repo = Path(repo).absolute()
    if config is None:
        try:
            from scitex_dev._cli.audit._config import load_config
        except ImportError as exc:
            raise ImportError(
                "PS-220 config loading needs scitex-dev "
                "(install scitex-logging[dev])"
            ) from exc

        config = load_config(repo)
    _report_config_errors(repo, config, violation_cls, out)
    backend_owner = owns_logging_backend(repo)
    for path in _src_files(repo):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            out.append(
                violation_cls(
                    "PS-220",
                    str(path),
                    f"Cannot inspect source ({type(exc).__name__}).",
                )
            )
            continue
        try:
            ast.parse(text)
        except SyntaxError as exc:
            out.append(
                violation_cls(
                    "PS-220",
                    f"{path}:{exc.lineno or 0}",
                    "Cannot parse source to verify output discipline.",
                )
            )
            continue
        for site in find_output_calls(
            text, repo=repo, filepath=path, backend_owner=backend_owner
        ):
            line = site.call.lineno
            out.append(
                violation_cls(
                    "PS-220",
                    f"{path}:{line}",
                    f"{site.kind} in package source (line {line}): "
                    f"{should_flag(None, site.call)[1]}. {_FIX_HINT}",
                )
            )


__all__ = ["PRINT_FORBIDDEN_RULES", "check_ps220_no_print", "find_output_calls"]
