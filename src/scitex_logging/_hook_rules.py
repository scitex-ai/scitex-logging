"""Logging-owned agent hooks; scitex-dev only discovers and dispatches."""


def provide():
    try:
        from scitex_dev.hooks import HookRule
    except ImportError as exc:
        raise ImportError("Logging hook activation requires scitex-logging[dev]") from exc

    return [
        HookRule(
            id="scitex-logging.output-policy",
            event="pre-tool-use",
            severity="deny",
            matches=(
                "Write",
                "Edit",
                "MultiEdit",
                "write_file",
                "patch",
                "Bash",
                "terminal",
                "apply_patch",
            ),
            rule="Reject Python source edits that bypass scitex-logging output policy.",
            reason="Raw output and hand-built console handlers cause mixed formats and duplicate lifecycle messages.",
            script="hooks/enforce_output.sh",
            check="scitex_logging._output._hook:check_payload",
            provider="scitex-logging",
            owner_module="scitex_logging",
        ),
        HookRule(
            id="scitex-logging.output-policy-after-shell",
            event="post-tool-use",
            severity="deny",
            matches=("Bash", "terminal", "apply_patch"),
            rule="Audit changed Python source after shell or patch operations using the logging-owned output detector.",
            reason="A source edit through shell or patch must not bypass the same logging policy enforced for native edits.",
            script="hooks/enforce_output_after.sh",
            check="scitex_logging._output._hook:check_payload",
            provider="scitex-logging",
            owner_module="scitex_logging",
        ),
    ]
