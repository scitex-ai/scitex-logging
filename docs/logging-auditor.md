# Logging output auditor

SciTeX logging owns PS-220, the mandatory error rule for output in package
source. SciTeX dev discovers the provider, invokes it, and reports findings.
The rule definition and detector live in this package, so project audits and
the AST linter apply the same policy.

The wheel advertises two entry points:

| Group | Name | Factory |
| --- | --- | --- |
| `scitex_dev.audit.project` | `scitex-logging` | `scitex_logging._audit_plugin:get_plugin` |
| `scitex_dev.linter.plugins` | `scitex-logging` | `scitex_logging._linter_plugin:get_plugin` |

The project factory supplies rule five-tuples and a checker accepting
`(repo, violation_class, out, *, config=None)`. The linter factory constructs
`Rule` and `Issue` through the public `scitex_dev.linter.spi` only when the
plugin activates. Its checker opts into filepath metadata with
`accepts_filepath=True`; existing two-argument plugins retain their interface.
Importing SciTeX logging or its project factory does not import SciTeX dev.

Every Python file under `src/` is in scope, including bundled directories
named `tests`, `scripts`, `examples`, or `docs`. Repository directories outside
`src/` are outside this source policy. Builtin `print`, `pprint`, Rich console
printing, stdlib logger acquisition, and direct stdlib diagnostic calls fail.
JSON payloads, explicit `file=` streams, and content-rendering function names
do not exempt raw print. `noqa`, severity settings, category overrides,
disabled rules, and skip lists cannot weaken the error tier.

Choose the logging primitive that matches the destination:

| Destination | Primitive |
| --- | --- |
| Diagnostics on stderr | `scitex_logging.getLogger(__name__)` and level methods |
| Human results on stdout | `scitex_logging.getConsole(__name__)` and level methods |
| Exact protocol stdout | `scitex_logging.getPlainConsole(__name__).emit(payload)` |
| Caller-owned protocol stream | `scitex_logging.getPlainConsole(__name__).emit(payload, stream=stream)` |

`emit` preserves a message without level prefixes and propagates write and
flush failures. Transport callers remain responsible for serialization.
See [stream behavior](stream-behavior.md) for destination, capture, and
configuration behavior.

The detector parses source without importing it. It follows import and
assignment aliases, literal `builtins.print` access, literal `getattr`, and
Rich console constructor/method aliases within lexical scopes. Definition-time
expressions are scanned in their enclosing scope; comprehensions and local
bindings shadow outer aliases. Proved output fields are followed between
methods of the same class. Unrelated
methods named `print`, including the SciTeX plain-console adapter, are not
classified as builtin or Rich printing. Nonliteral dynamic imports, computed attribute
names, and runtime call-graph behavior are outside this static proof.

The logging implementation needs stdlib logging to implement its public API.
That is the sole backend allowance. It requires the declared distribution
name, the actual public `getLogger` wiring, the `SciTeXLogger` subclass, and
the logger setup statements. Each allowed call must then match an exact module,
lexical scope, and complete AST statement. Foreign symlink targets, copied
folder names, and diagnostics added to an allowed module do not acquire an
exemption. Backend code remains subject to the raw-print ban.

Older developer tooling cannot enforce mandatory filepath-aware plugins.
Install the compatible logging/dev release pair when enabling this provider;
missing or broken mandatory providers must fail visibly, rather than report a
successful audit that skipped logging checks.
