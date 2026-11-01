# Output streams and configuration

Choose the writer according to what the output means:

| Writer | Destination | Format and filtering |
| --- | --- | --- |
| `getLogger(name)` | Root diagnostics: stderr and the log file by default | Level prefix; logger and configured handler thresholds apply |
| `getConsole(name)` | Current stdout | Same level prefix; a new console inherits the root threshold unless an explicit level is supplied |
| `getPlainConsole(name).emit(text)` | Current stdout, or the supplied `stream` | Exact text plus one newline; no prefix, diagnostic capture, or level filtering |

An embedding application's configured diagnostic handlers remain in control.
For example, a root handler deliberately writing to stdout will continue to do
so. SciTeX's default stderr destination applies when SciTeX configures the root.

## Diagnostic and console names are independent

`getLogger("app")` and `getConsole("app")` return separate objects. Acquiring
a console does not change the diagnostic logger's handlers, threshold, or
propagation. Repeated console acquisition with the same name returns the same
console and does not add duplicate stdout handlers. Console records keep the
requested name, but do not propagate into root diagnostics or file logging.

A new console with no explicit level follows `set_level()` and the root logger's
level. `getConsole("app", level=DEBUG)` selects an independent threshold;
reacquiring it without a level preserves that choice. `console.setLevel()` also
works. Standard `logging.disable()` and `console.disabled` remain effective.
Exact protocol results should use the plain writer so quiet diagnostic levels
cannot suppress them or add a prefix.

## Caller-owned output

```python
import scitex_logging as slog

with open("result.jsonl", "w", encoding="utf-8") as destination:
    slog.getPlainConsole().emit('{"ok": true}', stream=destination, flush=False)
```

The existing default remains stdout with immediate flushing. Both `stream` and
`flush` are optional keyword arguments; the `write` and `print` method aliases
have the same behavior. The writer does not open, close, or otherwise take
ownership of the supplied stream. Write and flush errors propagate to the
caller. Foreign wrappers retain their own behavior, even if they expose an
attribute named `original_stdout`.

## Import and explicit configuration

Import installs default console/file handlers only when root has no handlers.
An already configured root retains its handlers, handler thresholds, root
threshold, and current stdout capture. The root still gains SciTeX's
`success()`/`fail()` methods, preserving `getLogger()` without a name.

An explicit `configure(...)` call opts into replacing the process-wide root
configuration. Replaced handlers are closed, including their open file streams.
`capture_prints=True` enables SciTeX's stdout capture; `capture_prints=False`
disables its global capture. An explicit configuration call is consequently
best placed in the application's entry point rather than an imported library.

## Capture and redirects

SciTeX's print capture forwards raw stdout and also creates diagnostic records.
Both formatted and plain console writers bypass every SciTeX capture wrapper,
so a result reaches stdout without being copied into diagnostics. They resolve
the current destination on each write and preserve caller-owned redirects.

Capture refreshes its forwarding destination whenever it is activated again.
Stopping capture restores stdout only if that capture currently owns stdout;
it never replaces another active redirect. A redirect can later restore an
inactive capture wrapper. That wrapper forwards bytes without creating records,
and can be safely stopped or restarted. Distinct nested captures and repeated
contexts using the same capture restore the appropriate outer destination.

Capture operates on the process-wide `sys.stdout`, not a thread-local stream.
Coordinate capture and redirects in the application, and stop a capture that
targets a temporary stream before closing that stream. Captured raw writes are
recorded as write fragments, rather than assembled complete lines; distinct
nested active captures each record the raw writes that pass through them.

## Remaining formatting limits

The console formatter currently checks stdout's terminal status even when the
diagnostic handler writes to stderr. A terminal stdout paired with redirected
stderr can therefore put ANSI color codes into the redirected diagnostic
stream. The existing force-color environment settings also take precedence
without implementing `NO_COLOR`. The plain writer remains prefix-free and
color-free regardless of these formatter settings.

The console formatter modifies its input record's message when applying
indentation. Multiple console formatters handling the same record can therefore
accumulate indentation, and a later foreign handler can observe that modified
message. These formatting limitations are separate from console destination
isolation and capture ownership; they are not changed by this update.
