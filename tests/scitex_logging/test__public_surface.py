#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pin the module's public surface.

`__all__` governs `from scitex_logging import *`. It does NOT govern what a
user discovers: IPython/Jupyter tab-completion and `dir()` read the module
namespace. Those two surfaces drifted apart — imports (`os`, `annotations`)
and import-time scratch (`level`, `level_by_env`, `level_map`) appeared as
public API without ever being exported.

These tests pin the two surfaces to agree, so the drift cannot return
silently. That is the point: the previous state had no failing check, only a
confusing `dir()`.
"""

import scitex_logging


def _public(names):
    return {n for n in names if not n.startswith("_")}


class TestPublicSurface:
    def test_dir_exposes_nothing_beyond_all(self):
        """Nothing is discoverable that was not deliberately exported."""
        # Arrange
        module = scitex_logging
        # Act
        leaked = _public(dir(module)) - _public(module.__all__)
        # Assert
        assert leaked == set()

    def test_every_exported_name_is_reachable(self):
        """__all__ promises nothing it cannot deliver."""
        # Arrange
        module = scitex_logging
        # Act
        missing = [n for n in module.__all__ if not hasattr(module, n)]
        # Assert
        assert missing == []

    def test_module_defines_dir(self):
        """PEP 562 __dir__ is what makes tab-completion match __all__."""
        # Arrange
        module = scitex_logging
        # Act
        has_dir = "__dir__" in vars(module)
        # Assert
        assert has_dir

    def test_stdlib_import_not_advertised(self):
        """`os` is an implementation detail, not part of the logging API."""
        # Arrange
        module = scitex_logging
        # Act
        discoverable = "os" in dir(module)
        # Assert
        assert not discoverable

    def test_import_time_scratch_not_advertised(self):
        """Level-resolution scratch is setup, not API."""
        # Arrange
        scratch_names = {"level", "level_by_env", "level_map"}
        # Act
        still_public = scratch_names & set(dir(scitex_logging))
        # Assert
        assert still_public == set()

    def test_narrowing_discovery_did_not_remove_access(self):
        """__dir__ narrows what is LISTED, never what is reachable."""
        # Arrange
        module = scitex_logging
        # Act
        still_there = hasattr(module, "_os")
        # Assert
        assert still_there


# EOF
