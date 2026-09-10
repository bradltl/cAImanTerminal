# Module specifications

> Scope: terminal application. Reviewed 2026-09-10 for the split workspace.
> Code is in `terminal/`; commands run from the repository root unless stated otherwise.
> Model research is documented in [llm/README.md](../../llm/README.md).

| Module | Responsibility | Boundary |
|---|---|---|
| `terminal/src/ui.rs` | GTK window/tabs, VTE lifecycle, suggestion display | Only fixed Readline keys enter PTY from AI UI |
| `terminal/src/shell.rs` | Event decoder and atomic staging | Reject controls and multiline candidates |
| `terminal/resources/bash-integration.bash` | Prompt, input, execution and request events | Reads staged data; never evaluates it |
| `terminal/src/context.rs` | Bounded journals and request redaction | Per-tab state; no persistent conversation |
| `terminal/src/host.rs` | Schema, AST, risk, passive/follow-up gates, bounded probes | Never executes candidates |
| `terminal/src/command_validation.rs` | Distro/executable/CLI evidence and update-intent checks | Fixed help argv, bounded, executable-aware cache with five-minute expiry |
| `terminal/src/flag_help.rs` | Local flag-prefix descriptions | Installed documentation only; no inference or staged guesses |
| `terminal/src/guidance.rs` | Direct known-host/find guidance and prose checks | Commands still require CLI and risk validation |
| `terminal/src/worker.rs` | Bounded request queue and one-repair pipeline | Worker receives snapshots, never PTY handles |
| `terminal/src/inference.rs` | Resident GGUF, grammar sampling, token/time bounds | In-process CPU inference; no network |
| `terminal/src/theme.rs` | Bundled palettes, generated CSS, preference persistence | Atomic writes; window override separate from saved preference |
| `terminal/build.rs` | Embedded GLib icon resource | Desktop builds only |
| `terminal/packaging/install.py` | Per-user desktop package installation | No model download or shell-configuration changes |
| `terminal/src/main.rs` | Desktop or headless entry | `--ask` uses the same final pipeline |

Documentation probes use absolute `/usr/bin` paths, fixed argv, cleared
environment, null stdin, a two-second deadline, and process-group cleanup. Current
routes cover common system utilities, operation-specific pacman help, and selected
nested gh/gcloud commands. No model-provided argument vector is executed as a
probe. Unreviewed nested commands and missing option evidence fail closed.
Exhaustive man-page parsing, option argument arity, arbitrary nested CLIs and
positional semantics remain open.

Generation is capped at 256 output tokens and checks a 45-second deadline between
decode steps. Cancellation is checked between prompt batches and generated tokens.
A running native decode cannot be preempted immediately. Context overflow produces
an explicit error rather than silently dropping the user's request.

## Configuration and extension modules

| Module | Responsibility |
| --- | --- |
| `terminal/src/settings.rs` | Versioned preference validation, migration, atomic persistence and model resolution |
| `terminal/src/settings_ui.rs` | Central settings window and visible validation errors |
| `terminal/src/adapters.rs` | Compiled model/shell provider contracts and registry |
| `terminal/src/platform.rs` | Current Linux host facts, trusted executables and bounded probes |
| `terminal/src/terminal_backend.rs` | Terminal surface contract, implemented by VTE |
| `terminal/src/command_profiles.rs` | Existing audited command-help routes |
| `terminal/src/prompt.rs` | Structured context envelope, rendering and compaction policy |

Research modules are maintained independently in `llm/src/terminal_ai_bench/`.
