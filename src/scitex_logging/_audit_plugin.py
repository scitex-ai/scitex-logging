"""Project-audit entry point owned by scitex-logging."""


def get_plugin() -> dict:
    from ._output._auditor import PRINT_FORBIDDEN_RULES, check_ps220_no_print

    return {"rules": PRINT_FORBIDDEN_RULES, "checks": [check_ps220_no_print]}
