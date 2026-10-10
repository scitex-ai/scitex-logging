"""Individual stdlib backend operations in the owning logging distribution.

Distribution name, public API wiring, logger subclass and setup statements
must all match. An allowance applies to one full statement in one lexical
scope, never to a file, package, print call, or diagnostic acquisition.
"""

from __future__ import annotations

import ast
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python 3.9/3.10: declared conditional runtime dependency
    import tomli as tomllib


_BACKEND_STATEMENTS = {
    ("_logger.py", ("setup_logger_class",)): ("root = logging.getLogger()",),
    ("_config.py", ("set_level",)): (
        "logging.getLogger().setLevel(level)",
        "_GLOBAL_LEVEL = logging.getLogger().level",
        "for handler in logging.getLogger().handlers:\n    handler.setLevel(level)",
    ),
    ("_config.py", ("get_level",)): (
        "return _GLOBAL_LEVEL or logging.getLogger().level",
        "return _GLOBAL_LEVEL if _GLOBAL_LEVEL is not None else logging.getLogger().level",
    ),
    ("_config.py", ("configure",)): ("root_logger = logging.getLogger()",),
    ("_config.py", ("get_log_path",)): (
        "for handler in logging.getLogger().handlers:\n"
        "    if hasattr(handler, 'baseFilename'):\n"
        "        return handler.baseFilename",
    ),
    ("_context.py", ("log_to_file",)): ("root_logger = _logging.getLogger()",),
    ("_console.py", ("getConsole",)): (
        "console = logging.getLogger(name or DEFAULT_CONSOLE_NAME)",
        "console.parent = logging.getLogger()",
    ),
    ("_print_capture.py", ("PrintCapture", "__init__")): (
        "self.logger = logging.getLogger(logger_name)",
    ),
    ("__init__.py", ()): (
        "if _logging.getLogger().handlers:\n"
        "    _setup_logger_class()\n"
        "else:\n"
        "    configure(level=_level, enable_file=True, enable_console=True, capture_prints=False)",
    ),
}


def _shape(node: ast.AST) -> str:
    return ast.dump(node, include_attributes=False)


def _statement(text: str) -> str:
    return _shape(ast.parse(text).body[0])


_BACKEND_SHAPES = {
    key: frozenset(_statement(text) for text in statements)
    for key, statements in _BACKEND_STATEMENTS.items()
}


def _read_tree(path: Path, repo: Path) -> ast.Module | None:
    try:
        # Foreign symlink targets cannot establish ownership.
        if path.resolve() != repo.resolve() / path.relative_to(repo):
            return None
        return ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, RuntimeError, SyntaxError, UnicodeError):
        return None


def owns_logging_backend(repo: Path) -> bool:
    """Prove the actual public stdlib-based logger without importing source."""
    repo = Path(repo).absolute()
    try:
        project = tomllib.loads((repo / "pyproject.toml").read_text()).get("project")
    except (OSError, ValueError, UnicodeError):
        return False
    if not isinstance(project, dict) or project.get("name") != "scitex-logging":
        return False
    package = repo / "src" / "scitex_logging"
    init = _read_tree(package / "__init__.py", repo)
    logger = _read_tree(package / "_logger.py", repo)
    if init is None or logger is None:
        return False
    if not {
        _statement("import logging as _logging"),
        _statement("getLogger = _logging.getLogger"),
        _statement("from ._logger import setup_logger_class as _setup_logger_class"),
    } <= {_shape(node) for node in init.body}:
        return False
    classes = [
        node
        for node in logger.body
        if isinstance(node, ast.ClassDef) and node.name == "SciTeXLogger"
    ]
    if len(classes) != 1 or not any(
        _shape(base) == _shape(ast.parse("logging.Logger", mode="eval").body)
        for base in classes[0].bases
    ):
        return False
    setup = [
        node
        for node in logger.body
        if isinstance(node, ast.FunctionDef) and node.name == "setup_logger_class"
    ]
    return len(setup) == 1 and {
        _statement("logging.setLoggerClass(SciTeXLogger)"),
        _statement("root = logging.getLogger()"),
        _statement("root.__class__ = SciTeXLogger"),
    } <= {_shape(node) for node in setup[0].body}


def is_logging_backend_call(
    repo: Path, path: Path, tree: ast.AST, call: ast.Call
) -> bool:
    """Match one exact module, scope and statement; ownership is separate."""
    package = Path(repo).absolute() / "src" / "scitex_logging"
    path = Path(path).absolute()
    if path.parent != package or path.resolve() != package.resolve() / path.name:
        return False
    parents = {
        child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)
    }
    ancestors = []
    node = call
    while node in parents:
        node = parents[node]
        ancestors.append(node)
    scope = tuple(
        node.name
        for node in reversed(ancestors)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    )
    shapes = _BACKEND_SHAPES.get((path.name, scope), ())
    # The iter expression belongs to For; statements inside its body have
    # their own nearest statement and never inherit a loop's allowance.
    statement = next((node for node in ancestors if isinstance(node, ast.stmt)), None)
    return statement is not None and _shape(statement) in shapes
