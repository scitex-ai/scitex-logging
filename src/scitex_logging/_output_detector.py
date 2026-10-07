"""Static output primitive detection shared by the project audit and linter.

No audited module is imported. Import and assignment aliases are followed
within lexical scopes; assignments retain every known origin, so a later
rebinding cannot hide a forbidden primitive. This is a source detector,
not a Python interpreter: dynamic imports and computed attribute names are
outside its proof.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class _OutputCall:
    kind: str
    call: ast.Call


_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
_SCOPES = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Lambda,
    *_COMPREHENSIONS,
)
_CONSOLE = "rich.console.Console"
_CONSOLE_INSTANCE = _CONSOLE + "()"
_FORBIDDEN = {
    "builtins.print": "builtin print",
    "pprint.pprint": "pprint",
    "pprint.pp": "pprint",
    "logging.getLogger": "stdlib logging.getLogger",
    "logging.Logger": "stdlib logging.Logger",
    "rich.print": "Rich Console.print",
    _CONSOLE + ".print": "Rich Console.print",
    _CONSOLE_INSTANCE + ".print": "Rich Console.print",
}
_FORBIDDEN.update(
    {
        "logging." + name: "stdlib logging." + name
        for name in (
            "debug",
            "info",
            "warning",
            "warn",
            "error",
            "critical",
            "fatal",
            "exception",
            "log",
        )
    }
)


def _reference(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        root = _reference(node.value)
        return root + "." + node.attr if root else None
    return None


def _scope_nodes(scope: ast.AST):
    """Walk one lexical body, leaving nested bodies to their own bindings."""

    def definition_expressions(node):
        # Definitions execute these expressions in their enclosing scope.
        # Nested body traversal must not drop them or inspect them twice.
        if isinstance(node, _COMPREHENSIONS):
            yield node.generators[0].iter
            return
        yield from getattr(node, "decorator_list", ())
        if isinstance(node, ast.ClassDef):
            yield from node.bases
            yield from (keyword.value for keyword in node.keywords)
        else:
            args = node.args
            yield from args.defaults
            yield from (value for value in args.kw_defaults if value is not None)
            for argument in [
                *args.posonlyargs,
                *args.args,
                *args.kwonlyargs,
                *([args.vararg] if args.vararg else []),
                *([args.kwarg] if args.kwarg else []),
            ]:
                if argument.annotation is not None:
                    yield argument.annotation
            if getattr(node, "returns", None) is not None:
                yield node.returns

    def walk(node):
        yield node
        if isinstance(node, _SCOPES):
            for expression in definition_expressions(node):
                yield from walk(expression)
            return
        for child in ast.iter_child_nodes(node):
            yield from walk(child)

    if isinstance(scope, _COMPREHENSIONS):
        body = []
        for index, generator in enumerate(scope.generators):
            body.append(generator.target)
            if index:
                body.append(generator.iter)
            body.extend(generator.ifs)
        body.extend(
            [scope.key, scope.value] if isinstance(scope, ast.DictComp) else [scope.elt]
        )
    else:
        body = scope.body if not isinstance(scope, ast.Lambda) else [scope.body]
    for node in body:
        yield from walk(node)


def _assignment_bindings(target, value):
    """Include ordinary tuple/list alias unpacking without evaluating code."""
    if isinstance(target, (ast.Tuple, ast.List)) and isinstance(
        value, (ast.Tuple, ast.List)
    ):
        for child, item in zip(target.elts, value.elts):
            yield from _assignment_bindings(child, item)
    else:
        name = _reference(target)
        if name:
            yield name, value


def _target_names(target):
    return [
        node.id
        for node in ast.walk(target)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    ]


class _Bindings:
    def __init__(self, scope: ast.AST, parent: _Bindings | None):
        self.is_class = isinstance(scope, ast.ClassDef)
        self.parent = parent
        self.origins: dict[str, set[str]] = {}
        self.parameters: set[str] = set()
        self.nodes = list(_scope_nodes(scope))
        assignments = []
        annotations = []
        if isinstance(scope, _COMPREHENSIONS):
            for generator in scope.generators:
                for name in _target_names(generator.target):
                    self.origins.setdefault(name, set())
                    self.parameters.add(name)
                    if isinstance(generator.iter, (ast.List, ast.Tuple)) and parent:
                        for item in generator.iter.elts:
                            self.origins[name].update(parent.resolve(item))
        if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            args = scope.args
            for argument in [
                *args.posonlyargs,
                *args.args,
                *args.kwonlyargs,
                *([args.vararg] if args.vararg else []),
                *([args.kwarg] if args.kwarg else []),
            ]:
                self.origins.setdefault(argument.arg, set())
                self.parameters.add(argument.arg)
                if argument.annotation:
                    annotations.append((argument.arg, argument.annotation))
            positional = [*args.posonlyargs, *args.args]
            for argument, default in zip(
                positional[-len(args.defaults) :], args.defaults
            ):
                if parent:
                    self.origins[argument.arg].update(parent.resolve(default))
            for argument, default in zip(args.kwonlyargs, args.kw_defaults):
                if default is not None and parent:
                    self.origins[argument.arg].update(parent.resolve(default))
            if parent and parent.is_class and positional:
                receiver = positional[0].arg
                for name, origins in parent.origins.items():
                    if name.startswith("__instance__."):
                        self.origins[receiver + name[len("__instance__") :]] = set(
                            origins
                        )
        for node in self.nodes:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    origin = alias.name if alias.asname else alias.name.split(".")[0]
                    self.origins.setdefault(name, set()).add(origin)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                for alias in node.names:
                    self.origins.setdefault(alias.asname or alias.name, set()).add(
                        node.module + "." + alias.name
                    )
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                targets = (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                )
                for target in targets:
                    for name, value in _assignment_bindings(target, node.value):
                        self.origins.setdefault(name, set())
                        if value is not None:
                            assignments.append((name, value))
                        if isinstance(node, ast.AnnAssign):
                            annotations.append((name, node.annotation))
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                for name in _target_names(node.target):
                    self.origins.setdefault(name, set())
                    if isinstance(node.iter, (ast.List, ast.Tuple)):
                        assignments.extend((name, item) for item in node.iter.elts)
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    if item.optional_vars is not None:
                        for name in _target_names(item.optional_vars):
                            self.origins.setdefault(name, set())
            elif isinstance(node, ast.ExceptHandler) and node.name:
                self.origins.setdefault(node.name, set())
            elif isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                self.origins.setdefault(node.name, set())
        # Finite alias closure: each pass can add only origins found in this
        # body or its parent. Cap passes by the number of binding equations.
        for _ in range(len(assignments) + len(annotations) + 1):
            changed = False
            for name, value in assignments:
                before = len(self.origins[name])
                self.origins[name].update(self.resolve(value))
                changed |= len(self.origins[name]) != before
            for name, annotation in annotations:
                if _CONSOLE in self.resolve(annotation):
                    before = len(self.origins[name])
                    self.origins[name].add(_CONSOLE_INSTANCE)
                    changed |= len(self.origins[name]) != before
            if not changed:
                break

    def lookup(self, name: str) -> set[str]:
        # Parameters do not resolve to an unrelated outer import alias.
        if name in self.parameters:
            return self.origins[name]
        # An undecidable bare print remains forbidden; known assignment aliases
        # retain their unsafe origin even after another possible rebinding.
        if name == "print":
            return {"builtins.print"} | self.origins.get(name, set())
        if name == "__builtins__":
            return {"builtins"}
        if name in self.origins:
            return self.origins[name]
        return self.parent.lookup(name) if self.parent else set()

    def resolve(self, node: ast.AST) -> set[str]:
        name = _reference(node)
        if name:
            origins = self.lookup(name)
            if origins:
                return origins
        if isinstance(node, ast.Name):
            return self.lookup(node.id)
        if isinstance(node, ast.Attribute):
            return {value + "." + node.attr for value in self.resolve(node.value)}
        if isinstance(node, ast.Call):
            origins = self.resolve(node.func)
            if _CONSOLE in origins:
                return {_CONSOLE_INSTANCE}
            # A literal getattr(builtins, 'print') is a statically known alias.
            if isinstance(node.func, ast.Name) and node.func.id == "getattr":
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                    attribute = node.args[1].value
                    if isinstance(attribute, str):
                        return {
                            value + "." + attribute
                            for value in self.resolve(node.args[0])
                        }
            if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                if node.args and isinstance(node.args[0], ast.Constant):
                    module = node.args[0].value
                    if isinstance(module, str):
                        return {module}
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            attribute = node.slice.value
            if isinstance(attribute, str):
                return {
                    value.removesuffix(".__dict__") + "." + attribute
                    for value in self.resolve(node.value)
                    if value == "builtins" or value.endswith(".__dict__")
                }
        if isinstance(node, ast.IfExp):
            return self.resolve(node.body) | self.resolve(node.orelse)
        return set()


def _class_output_attributes(bindings: _Bindings) -> None:
    """Carry proved primitive/Rich fields between methods of this class only."""

    def relevant(origins):
        return {
            origin
            for origin in origins
            if origin in _FORBIDDEN or origin in {_CONSOLE, _CONSOLE_INSTANCE}
        }

    for name, origins in tuple(bindings.origins.items()):
        values = relevant(origins)
        if "." not in name and values:
            bindings.origins["__instance__." + name] = values
    methods = [
        node
        for node in bindings.nodes
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    for _ in range(len(methods) + 1):
        changed = False
        for method in methods:
            if any(
                isinstance(decorator, ast.Name) and decorator.id == "staticmethod"
                for decorator in method.decorator_list
            ):
                continue
            positional = [*method.args.posonlyargs, *method.args.args]
            if not positional:
                continue
            receiver = positional[0].arg + "."
            local = _Bindings(method, bindings)
            for name, origins in local.origins.items():
                values = relevant(origins)
                if name.startswith(receiver) and values:
                    target = "__instance__." + name[len(receiver) :]
                    known = bindings.origins.setdefault(target, set())
                    before = len(known)
                    known.update(values)
                    changed |= len(known) != before
        if not changed:
            break


def _output_calls(text: str) -> tuple[ast.AST | None, list[_OutputCall]]:
    """Return the parsed tree and raw primitive sites in source order."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None, []
    hits = []

    def inspect(scope, parent):
        bindings = _Bindings(scope, parent)
        if bindings.is_class:
            _class_output_attributes(bindings)
        for node in bindings.nodes:
            if isinstance(node, ast.Call):
                kinds = {
                    _FORBIDDEN[origin]
                    for origin in bindings.resolve(node.func)
                    if origin in _FORBIDDEN
                }
                if kinds:
                    hits.append(_OutputCall(sorted(kinds)[0], node))
            elif isinstance(node, _SCOPES):
                inspect(node, bindings)

    inspect(tree, None)
    return tree, sorted(hits, key=lambda site: (site.call.lineno, site.call.col_offset))


def _src_files(repo: Path) -> list[Path]:
    """Every Python file under src, including bundled scripts and examples."""
    src = Path(repo) / "src"
    if not src.is_dir():
        return []
    return sorted(src.rglob("*.py"))


def source_repo(filepath: str | Path) -> Path | None:
    """Locate source scope lexically, preserving symlinks for ownership proof."""
    if str(filepath).startswith("<"):
        return None
    path = Path(filepath).absolute()
    for parent in path.parents:
        if parent.name == "src":
            return parent.parent
    return None


def find_output_calls(
    text: str,
    *,
    repo: Path | None = None,
    filepath: Path | None = None,
    backend_owner: bool | None = None,
) -> list[_OutputCall]:
    """Shared strict detector, with individually proved logger backend calls."""
    from ._output_backend import is_logging_backend_call, owns_logging_backend

    tree, calls = _output_calls(text)
    if tree is None or repo is None or filepath is None:
        return calls
    if backend_owner is None:
        backend_owner = owns_logging_backend(repo)
    return [
        site
        for site in calls
        if not (
            site.kind == "stdlib logging.getLogger"
            and backend_owner
            and is_logging_backend_call(repo, filepath, tree, site.call)
        )
    ]
