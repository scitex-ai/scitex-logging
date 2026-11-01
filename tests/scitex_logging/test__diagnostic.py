"""Dedicated diagnostics preserve canonical formatting and stdout protocols."""

import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "format_name,expected",
    [("default", "INFO: diagnostic"), ("detailed", "INFO: [embedded] diagnostic")],
)
def test_diagnostic_does_not_inherit_an_embedding_stdout_handler(
    tmp_path, format_name, expected
):
    # Arrange: an embedding app owns its root output destination.
    env = dict(
        os.environ,
        HOME=str(tmp_path),
        SCITEX_LOGGING_FORMAT=format_name,
        SCITEX_LOGGING_FORCE_COLOR="0",
        SCITEX_LOGGING_LEVEL="INFO",
    )
    code = "import logging,sys; import scitex_logging as s; logging.root.handlers[:]=[logging.StreamHandler(sys.stdout)]; a=s.getDiagnostic('embedded'); b=s.getDiagnostic('embedded'); assert a is b; b.info('diagnostic')"
    # Act
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    # Assert
    assert (result.stdout, result.stderr.strip()) == ("", expected)
