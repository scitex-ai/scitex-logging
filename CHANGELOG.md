# Changelog

All notable changes to `scitex-logging` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.6] - 2026-11-09

### Fixed

- Include the canonical logging policy and stream guide in bundled web docs;
  distinguish application handlers from isolated stderr diagnostics.
- Give coverage subprocesses independent data files and a valid single-line
  startup binding, preventing SQLite collisions under parallel tests.
- Enforce PS-220 for native edits and linter checks through source aliases,
  including legacy `apps` paths pointing into `src`. Keep the original path
  for strict logging-backend ownership checks and refuse unresolved aliases.

- Isolate the file-logging gate in configuration tests so a disable control
  cannot change later handler/path controls under distributed scheduling.

## [0.2.5] - 2026-11-05

### Fixed

- Audit Git-owned Python source after frontend dependency installation without
  treating ignored third-party code as package-authored code. Preserve tracked,
  hidden and nonignored untracked source checks and targeted hook enforcement.
- Require published Dev 0.62.16 for the optional development toolchain and
  replace obsolete bootstrap instructions with actual installation guidance.
- Ship bundled HTML documentation and its local assets in the wheel; omit
  build caches. Build the docs from actual dependencies and current source.
- Pin the generated audit gate to its checkout and guard against partial runs
  silently omitting the gate.

## [0.2.4] - 2026-11-01

- Enforce PS-220 through logging-owned native edit/shell hooks plus the shared auditor and linter detector.
- Reject ad hoc `logging.basicConfig` and direct stdlib console handlers outside proved backend operations.
- Add `getDiagnostic()` for canonical, non-propagating stderr output in embedded protocol producers.


## [0.2.2] - 2026-10-02

### Fixed

- Keep PlainConsole results on the current stdout stream without routing
  them through logger-owned PrintCapture wrappers. Preserve redirected and
  foreign streams, nested capture and restoration, and ordinary diagnostics.
- Route requested LLM CLI JSON, diagrams and artifact acknowledgements
  through PlainConsole independently of diagnostic thresholds.
- Acquire the canonical public logger lazily in Tee and warnings. Preserve
  Tee's original stderr fallback when its file sink or logger fails.

### Changed

- Require the genuinely published Dev 0.62.1 auditor in contributor
  environments so the canonical backend passes PS-220 without suppressions.
- Verify the CI image digest before release execution, give Logger tests,
  builds and publishing owned scratch and caches, and require the complete
  declared test environment with RUN_E2E enabled.

## [0.2.0]

### Added

- feat(console): `getConsole(name)` — a logger that writes to **stdout**,
  formatted identically to `getLogger()`. `getLogger()` is unchanged and
  still writes every level to stderr.

  Why it exists: a mechanical `print(...)` → `log.info(...)` migration
  silently moves output off stdout, and the consumer then reads an empty
  stdout as a valid answer rather than an error. stdout carries the
  deliverable (JSON payloads, completion scripts, piped values); stderr
  carries the commentary. Two destinations, one appearance.

### Fixed

- fix(console): console output no longer duplicates onto stderr when
  `configure(capture_prints=True)` — the default. Print capture replaces
  `sys.stdout` with a tee that writes stdout *and* logs what it sees, so
  a stdout handler resolving `sys.stdout` per emit wrote every line
  twice, on two streams. `propagate = False` could not prevent it: the
  second copy re-enters through `sys.stdout`, never through the logger
  hierarchy.
- fix(logging): multi-line records are now lexically distinct from fresh
  ones. Continuation lines carry `LEVEL| ` instead of repeating
  `LEVEL: `, so a consumer counting `^WARN:` counts events rather than
  paragraphs.
- fix(ci): the CLA workflow passes only the one secret its callee
  requires, instead of forwarding every repository secret into a job
  startable by any outsider via `issue_comment` / `pull_request_target`.

### Changed

- `dir(scitex_logging)` now reports exactly the declared public surface
  (PEP 562 `__dir__`): 65 discoverable, 65 declared, nothing leaked.
  This narrows **discovery**, not availability — every name remains
  reachable by explicit attribute access, and a test pins that.

## [0.1.7]

- fix(workflows): resync integrated release pipeline from scitex-dev v0.11.20
- fix(workflows): standardize to scitex-dev canonical CI set

## [0.1.6]

- fix(tests): clear test-quality violations (PA-306, PA-307)
- docs(branding): two-row shields badge block, author email update
- chore(gitignore): exclude .venv, .coverage, .csh, .dat, build artifacts
- fix(handlers): LazyStderrStreamHandler — resolve sys.stderr per emit

## [0.1.5]

- test(llm): coverage lift (10% → 97-100%, +87 tests)
- refactor(llm): __main__.py split (reverted)
- chore(deps): bump scitex-dev>=0.11.14

## [0.1.4]

- chore(deps): bump scitex-dev pin floor to 0.11.7
- docs(readme): add ## Architecture and ## Demo sections (PS141/PS142)
- fix(release-safety): opt-in publish-pypi.yml (workflow_dispatch only)

## [0.1.3]

- Initial CHANGELOG entry — see git log for prior history.
