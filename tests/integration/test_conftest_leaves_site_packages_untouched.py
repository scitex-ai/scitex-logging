"""Importing tests/conftest.py must not touch site-packages or caller env."""

import subprocess
import sys
from pathlib import Path


def test_conftest_leaves_site_packages_untouched():
    # Arrange
    conftest_path = Path(__file__).resolve().parents[1] / "conftest.py"
    code = (
        "import os, runpy, site\n"
        "os.environ['COVERAGE_PROCESS_START'] = 'SENTINEL_START'\n"
        "os.environ['COVERAGE_FILE'] = 'SENTINEL_FILE'\n"
        "def _snapshot():\n"
        "    snap = {}\n"
        "    dirs = list(site.getsitepackages())\n"
        "    try:\n"
        "        dirs.append(site.getusersitepackages())\n"
        "    except Exception:\n"
        "        pass\n"
        "    import os as _os\n"
        "    for d in dirs:\n"
        "        try:\n"
        "            snap[d] = sorted(_os.listdir(d))\n"
        "        except OSError:\n"
        "            snap[d] = []\n"
        "    return snap\n"
        "before = _snapshot()\n"
        f"runpy.run_path({str(conftest_path)!r})\n"
        "after = _snapshot()\n"
        "assert before == after, 'conftest modified site-packages'\n"
        "assert os.environ.get('COVERAGE_PROCESS_START') == 'SENTINEL_START'\n"
        "assert os.environ.get('COVERAGE_FILE') == 'SENTINEL_FILE'\n"
    )
    # Act
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    # Assert
    assert result.returncode == 0, result.stderr
