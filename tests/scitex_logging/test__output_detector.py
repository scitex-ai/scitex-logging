"""Strict primitive detection and individually scoped backend ownership."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from scitex_logging._output_auditor import _output_calls, _src_files, find_output_calls
from scitex_logging._output_backend import owns_logging_backend


@pytest.mark.parametrize(
    "source",
    [
        "print('status')",
        "import json; print(json.dumps({'ok': True}))",
        "import sys; print('error', file=sys.stderr)",
        "def render_content(content, stream):\n    print(content, file=stream)",
        "print('status')  # noqa: PS-220",
        "import builtins; builtins.print('status')",
        "import builtins as b; b.print('status')",
        "from builtins import print as emit; emit('status')",
        "emit = print; output = emit; output('status')",
        "import builtins as b; emit = b.print; emit('status')",
        "emit, other = print, None; emit('status')",
        "import builtins as b; getattr(b, 'print')('status')",
        "__import__('builtins').print('status')",
        "__builtins__['print']('status')",
        "import builtins; builtins.__dict__['print']('status')",
        "import pprint as p; p.pprint({'ok': True})",
        "from pprint import pp as emit; emit({'ok': True})",
        "import logging as log; log.getLogger(__name__)",
        "from logging import getLogger as acquire; acquire(__name__)",
        "import logging; acquire = logging.getLogger; acquire('status')",
        "import logging; logging.info('status')",
        "from logging import warning as warn; warn('status')",
        "import logging; logging.Logger('status')",
        "from rich.console import Console; Console().print('status')",
        "from rich.console import Console as C; term = C(); term.print('status')",
        "import rich.console as rc; rc.Console().print('status')",
        "import rich; term = rich.console.Console(); term.print('status')",
        "from rich.console import Console; term = Console(); emit = term.print; emit('status')",
        "from rich.console import Console; Console.print(None, 'status')",
        "from rich.console import Console\ndef show(term: Console):\n    term.print('status')",
        "from rich import print as emit; emit('status')",
        "from builtins import print as emit\ndef show():\n    emit('status')",
        "def show():\n    from builtins import print as emit\n    emit('status')",
        "def show(emit=print):\n    emit('status')",
        "def show(*, emit=print):\n    emit('status')",
        "emit = lambda output=print: output('status')",
        "for emit in [print]:\n    emit('status')",
        "[emit('status') for emit in [print]]",
        "[item for item in print('iterable')]",
        "def show(value=print('default')):\n    pass",
        "def show(*, value=print('default')):\n    pass",
        "@decorate(print('decorator'))\ndef show():\n    pass",
        "def show(value: print('annotation')):\n    pass",
        "def show() -> print('result'):\n    pass",
        "emit = lambda value=print('default'): value",
        "class Widget(print('base')):\n    pass",
        "class Widget(metaclass=print('metaclass')):\n    pass",
        "@decorate(print('decorator'))\nclass Widget:\n    pass",
    ],
)
def test_forbidden_aliases_and_transports_are_reported(source):
    # Arrange
    text = source + "\n"
    # Act
    sites = find_output_calls(text)
    # Assert
    assert len(sites) == 1


@pytest.mark.parametrize(
    "source",
    [
        "import scitex_logging as logging; logging.getLogger(__name__).info('status')",
        "import scitex_logging as slogging; slogging.getConsole(__name__).info('result')",
        "import scitex_logging as slogging; slogging.getPlainConsole(__name__).emit('{}')",
        "import scitex_logging as slogging; console = slogging.getPlainConsole(); console.print('{}')",
        "class Widget:\n    def print(self, value):\n        return value\nWidget().print('value')",
        "import logging\ndef show(logging):\n    logging.getLogger('status')",
        "from builtins import print as emit\ndef show(emit):\n    emit('value')",
        "def show(print):\n    print('value')",
        "import logging\ndef show():\n    for logging in adapters:\n        logging.getLogger('value')",
        "import logging\ndef show():\n    with adapter() as logging:\n        logging.getLogger('value')",
        "import logging\ndef show():\n    try:\n        pass\n    except Exception as logging:\n        logging.getLogger('value')",
        "import logging\n[logging.getLogger('value') for logging in adapters]",
        "import logging\ndef show():\n    import scitex_logging as logging\n    logging.getLogger('status')",
        "import logging; logging.basicConfig()",
        "'print(\"example\")'",
    ],
)
def test_scitex_streams_and_unrelated_methods_are_allowed(source):
    # Arrange
    text = source + "\n"
    # Act
    sites = find_output_calls(text)
    # Assert
    assert sites == []


def test_assignment_alias_closure_retains_unsafe_origins():
    # Arrange
    source = "from builtins import print as emit\noutput = emit\nemit = lambda x: x\noutput('status')\n"
    # Act
    sites = find_output_calls(source)
    # Assert
    assert [(site.kind, site.call.lineno) for site in sites] == [("builtin print", 4)]


def test_definition_expression_aliases_use_the_enclosing_scope():
    # Arrange
    source = "from builtins import print as emit\ndef show(emit=emit('default')):\n    emit('value')\n"
    # Act
    sites = find_output_calls(source)
    # Assert
    assert [(site.kind, site.call.lineno) for site in sites] == [("builtin print", 2)]


def test_comprehension_binding_does_not_shadow_later_enclosing_calls():
    # Arrange
    source = (
        "import logging\ndef show():\n"
        "    values = [logging for logging in adapters]\n"
        "    logging.getLogger('status')\n"
    )
    # Act
    sites = find_output_calls(source)
    # Assert
    assert [(site.kind, site.call.lineno) for site in sites] == [
        ("stdlib logging.getLogger", 4)
    ]


@pytest.mark.parametrize(
    "setup",
    [
        "    def __init__(self):\n        self.console = Console()\n",
        "    console = Console()\n",
        "    def __init__(this):\n        this.console = Console()\n",
    ],
)
def test_proved_rich_fields_are_followed_between_class_methods(setup):
    # Arrange
    source = (
        "from rich.console import Console\nclass Widget:\n"
        + setup
        + "    def show(self):\n        self.console.print('status')\n"
    )
    # Act
    sites = find_output_calls(source)
    # Assert
    assert len(sites) == 1 and sites[0].kind == "Rich Console.print"


def test_rich_fields_do_not_classify_another_class_print_method():
    # Arrange
    source = (
        "from rich.console import Console\nclass RichWidget:\n"
        "    def __init__(self):\n        self.console = Console()\n"
        "class PlainWidget:\n    def show(self):\n        self.console.print('value')\n"
    )
    # Act
    sites = find_output_calls(source)
    # Assert
    assert sites == []


def test_builtin_function_fields_are_followed_between_class_methods():
    # Arrange
    source = (
        "class Widget:\n    def __init__(self):\n        self.emit = print\n"
        "    def show(self):\n        self.emit('status')\n"
    )
    # Act
    sites = find_output_calls(source)
    # Assert
    assert len(sites) == 1 and sites[0].kind == "builtin print"


def test_nested_source_directories_remain_in_scope(tmp_path):
    # Arrange
    expected = []
    for label in ("tests", "scripts", "docs", "examples", "ordinary", "__pycache__"):
        path = tmp_path / "src" / "pkg" / label / "output.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("print('status')\n")
        expected.append(path)
    outside = tmp_path / "scripts" / "output.py"
    outside.parent.mkdir()
    outside.write_text("print('development-only')\n")
    # Act
    files = _src_files(tmp_path)
    # Assert
    assert files == sorted(expected)


_INIT = (
    "import logging as _logging\n"
    "from ._logger import setup_logger_class as _setup_logger_class\n"
    "getLogger = _logging.getLogger\n"
    "raise RuntimeError('audit must never import source')\n"
)
_LOGGER = (
    "import logging\nclass SciTeXLogger(logging.Logger):\n    pass\n"
    "def setup_logger_class():\n"
    "    logging.setLoggerClass(SciTeXLogger)\n"
    "    root = logging.getLogger()\n"
    "    root.__class__ = SciTeXLogger\n"
)


def _owner(repo: Path):
    (repo / "pyproject.toml").write_text('[project]\nname = "scitex-logging"\n')
    package = repo / "src" / "scitex_logging"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(_INIT)
    (package / "_logger.py").write_text(_LOGGER)
    return package


@pytest.mark.parametrize(
    ("filename", "source"),
    [
        ("_logger.py", _LOGGER),
        (
            "_config.py",
            "import logging\ndef set_level(level):\n"
            "    logging.getLogger().setLevel(level)\n"
            "    _GLOBAL_LEVEL = logging.getLogger().level\n"
            "    for handler in logging.getLogger().handlers:\n        handler.setLevel(level)\n",
        ),
        (
            "_config.py",
            "import logging\ndef get_level():\n"
            "    return _GLOBAL_LEVEL if _GLOBAL_LEVEL is not None else logging.getLogger().level\n",
        ),
        (
            "_context.py",
            "import logging as _logging\ndef log_to_file():\n"
            "    root_logger = _logging.getLogger()\n",
        ),
        (
            "_console.py",
            "import logging\ndef getConsole():\n"
            "    console.parent = logging.getLogger()\n",
        ),
        (
            "_print_capture.py",
            "import logging\nclass PrintCapture:\n"
            "    def __init__(self, logger_name):\n        self.logger = logging.getLogger(logger_name)\n",
        ),
        (
            "__init__.py",
            _INIT.replace("raise RuntimeError('audit must never import source')\n", "")
            + "if _logging.getLogger().handlers:\n    _setup_logger_class()\nelse:\n"
            "    configure(level=_level, enable_file=True, enable_console=True, capture_prints=False)\n",
        ),
    ],
)
def test_exact_owner_backend_operations_are_allowed(tmp_path, filename, source):
    # Arrange
    package = _owner(tmp_path)
    path = package / filename
    path.write_text(source)
    # Act
    sites = find_output_calls(source, repo=tmp_path, filepath=path)
    # Assert
    assert sites == []


@pytest.mark.parametrize(
    ("filename", "source"),
    [
        (
            "_console.py",
            "import logging\ndef getConsole():\n    log = logging.getLogger('diagnostic')\n",
        ),
        ("_logger.py", _LOGGER + "\ndef status():\n    print('status')\n"),
        (
            "_config.py",
            "import logging\ndef set_level(level):\n"
            "    for handler in logging.getLogger().handlers:\n        print('status')\n",
        ),
        (
            "_config.py",
            "import logging\ndef get_level():\n    return logging.getLogger('diagnostic').level\n",
        ),
        (
            "_config.py",
            "import logging\ndef diagnostic():\n    root_logger = logging.getLogger()\n",
        ),
    ],
)
def test_known_backend_modules_do_not_exempt_other_output(tmp_path, filename, source):
    # Arrange
    package = _owner(tmp_path)
    path = package / filename
    path.write_text(source)
    # Act
    sites = find_output_calls(source, repo=tmp_path, filepath=path)
    # Assert
    assert sites


@pytest.mark.parametrize("change", ["name", "wiring", "subclass", "setup"])
def test_partial_owner_identity_cannot_claim_backend_allowances(tmp_path, change):
    # Arrange — one intent (break the named ownership link); a dispatch table
    # selects the mutation so the parametrized body holds no branches.
    package = _owner(tmp_path)
    mutations = {
        "name": lambda: (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "scitex-other"\n'
        ),
        "wiring": lambda: (package / "__init__.py").write_text(
            _INIT.replace("getLogger = _logging.getLogger", "getLogger = None")
        ),
        "subclass": lambda: (package / "_logger.py").write_text(
            _LOGGER.replace("logging.Logger", "object")
        ),
        "setup": lambda: (package / "_logger.py").write_text(
            _LOGGER.replace("root.__class__ = SciTeXLogger", "pass")
        ),
    }
    mutations[change]()
    # Act
    owner = owns_logging_backend(tmp_path)
    # Assert
    assert not owner


def test_foreign_symlink_cannot_establish_logger_ownership(tmp_path):
    # Arrange
    package = _owner(tmp_path)
    original = package / "_logger.py"
    foreign = tmp_path / "foreign.py"
    foreign.write_text(original.read_text())
    original.unlink()
    original.symlink_to(foreign)
    # Act
    owner = owns_logging_backend(tmp_path)
    # Assert
    assert not owner


def test_raw_detector_exposes_compatibility_ast_and_source_locations():
    # Arrange
    text = "import builtins as b\nb.print('status')\n"
    # Act
    tree, sites = _output_calls(text)
    # Assert
    assert isinstance(tree, ast.Module) and [
        (site.kind, site.call.lineno) for site in sites
    ] == [("builtin print", 2)]
