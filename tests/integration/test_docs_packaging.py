"""Installed documentation must include its HTML and local assets."""

import posixpath
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from hatchling.builders.wheel import WheelBuilder


class _References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.references.append(value)


def test_real_wheel_contains_complete_bundled_documentation(tmp_path):
    # Arrange
    project = Path(__file__).resolve().parents[2]
    prefix = "scitex_logging/_sphinx_html/"
    missing = []
    # Act
    wheel = next(WheelBuilder(str(project)).build(directory=str(tmp_path)))
    with zipfile.ZipFile(wheel) as archive:
        members = set(archive.namelist())
        if prefix + "index.html" not in members:
            missing.append("documentation entry page")
        for name in sorted(members):
            if not name.startswith(prefix):
                continue
            if "/.doctrees/" in name or name.endswith("/.buildinfo"):
                missing.append((name, "build cache must not ship"))
            if not name.endswith((".html", ".css")):
                continue
            text = archive.read(name).decode("utf-8")
            if name.endswith(".html"):
                parser = _References()
                parser.feed(text)
                references = parser.references
            else:
                references = re.findall(r"url\(\s*['\"]?([^'\")\s]+)", text)
            for reference in references:
                parts = urlsplit(reference)
                if parts.scheme or parts.netloc or not parts.path:
                    continue
                target = posixpath.normpath(
                    posixpath.join(posixpath.dirname(name), unquote(parts.path))
                )
                if parts.path.endswith("/"):
                    target = posixpath.join(target, "index.html")
                if target.startswith(prefix) and target not in members:
                    missing.append((name, reference, target))
    # Assert
    assert missing == [], missing
