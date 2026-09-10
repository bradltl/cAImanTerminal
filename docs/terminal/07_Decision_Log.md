# Decision log

> Scope: terminal application. Reviewed 2026-09-10 for the split workspace.
> Code is in `terminal/`; commands run from the repository root unless stated otherwise.
> Model research is documented in [llm/README.md](../../llm/README.md).

## 2026-09-09 — Native first slice

Use Rust/GTK4/VTE as specified, rather than extending the Python research harness
into the desktop application. Cargo is a separate workspace alongside Python.

## 2026-09-09 — In-process CPU llama.cpp

Pin `llama-cpp-2` to 0.1.156 and commit Cargo.lock because the upstream bindings
track a rapidly changing C API. No external daemon, public port, runtime downloads,
or cloud fallback. Model weights remain resident on one worker; fresh request KV
contexts provide a simple isolation boundary. Performance tuning comes after
correctness measurement.

## 2026-09-09 — Default SFT v2

The saved `artifacts/results/qwen_comparison_v2_suite.json` ranks v2 at 71.9%, ahead of v1
(70.3%) and v3 (68.7%). Choose v2 by default and keep `--model` override. Do not
retrain against this holdout suite during app development.

## 2026-09-09 — Readline data staging

A private file plus a fixed Readline widget is used instead of injecting generated
bytes into the PTY. Command bytes cannot contain control characters; the widget
checks that the user's current input has not changed. Enter remains a separate
user action. The first implementation selects Emacs mode and documents that limit.

## 2026-09-09 — Fail closed on unsupported shell constructs

Use tree-sitter Bash for structure and shlex for literal argv. Initially support
simple commands and foreground pipelines. Reject command lists, redirects,
expansions, wrappers/interpreters, and other unclassified constructs. This trades
coverage for a reviewable staging boundary; it does not constrain manually typed
Bash commands.

## 2026-09-09 — Conservative remote boundary

Pause terminal assistance during direct SSH rather than treating local package
metadata as remote facts. Full remote prompt integration is a later slice.

## 2026-09-09 — Verification-driven fixes

The real PTY test exposed Ctrl-S/XOFF consuming the initial staging shortcut; the
widget now uses Ctrl-X followed by `s`. Native inference exposed double acceptance
of a sampled token: this pinned sampler's `sample()` already accepts tokens, so
calling `accept()` again advanced the grammar twice and threw a C++ exception.
The redundant call was removed and real GGUF inference succeeded.

The initial JSON-only user context format reduced this tiny model's answer
relevance. The host now preserves the training corpus's section labels and `@`
request convention while still building values from structured session events.

Raw regression replay exposed unsafe system-file mutations and password arguments.
The host rejects protected system-tree mutations (including `/var` cache trees),
critical package removal, password arguments, disk writers, and init/process-group
signals. These are general operation/path rules, not model-provided risk labels.

## 2026-09-09 — Minimal terminal-style UI

User feedback supersedes the initial sidebar treatment: make the experience feel
like tmux with Konsole-style tab management. Replace the sidebar labels/cards with
a selectable, read-only monospace text pane; match VTE colors and typography.
Remove branding, onboarding prose, stage buttons, switches, and routine metrics
from the main surface. Keep only `Ready..` when idle after loading. Tab accepts
suggestions; a small menu holds optional controls. Preserve actual risk messages
for Caution/Elevated commands and show documentation only when used.

## 2026-09-09 — Idle observation and ordered host pipeline

Replace per-key Readline callbacks with one idle snapshot; reserve the ghost strip
height to prevent PTY resize/reflow. Observe failures and suggested-command results
once per completion, retaining intent separately from the bounded transcript.
Retry a full worker mailbox without marking the request delivered.

Infer first, validate against host facts, obtain fixed installed help when needed,
allow one repair, revalidate, then apply deterministic risk. Native package-manager
checks include ID_LIKE. Lookup commands cannot recheck a known missing or
incompatible tool. A narrow system-update operation check addresses irrelevant
package searches observed in real-model tests. Failed repairs produce host
feedback without a ghost. Model weights are unchanged; semantic limits remain.

## 2026-09-09 — Direct known-fact guidance and response tone

The reported rhetorical clarification exposed a gap: command validation alone
does not validate assistant prose. Add bounded tone/agency checks and share the
one-repair budget across prose and commands. Route known package-manager errors
and common find input through deterministic guidance, with the same downstream
CLI/risk checks. This deliberately avoids inference for facts already established
by the host. Broaden the idle trigger to include bare find and short find options.

## 2026-09-09 — Appearance and local desktop package

Create original caiman artwork as a scalable character-grid SVG and separate
ASCII CLI mascot. Embed the SVG for runtime window icons and install the same
asset for desktop integration. Preserve the minimal Ready.. startup state.

Bundle five established Gogh terminal palettes plus cAIman rather than claim a
universal popularity ranking. Apply the entire terminal palette and surrounding
UI together; persist only menu selections, with --theme as a window override.
Ship the upstream palette license and author credits.

Install a separate desktop executable under the user's local prefix. This makes
the app-menu launcher independent of core-only Cargo builds, which previously
replaced the development executable with a non-desktop version. Model weights
remain external and the launcher uses an absolute existing model path.

## 2026-09-10 — Provider boundaries and consolidated settings

Restore Qwen SFT v2 as default at the user's request. Separate model, terminal
surface, shell integration and host operations behind compiled interfaces, and
move audited help routes to their own module. Register only current implementations;
do not add speculative OS/model/terminal data. Introduce versioned, atomically
saved preferences and a central Settings window. Runtime changes take effect on
relaunch; appearance theme can apply immediately without disturbing active shells.

## 2026-09-10 — Split workspace and display rename

Adopt the display name cAIman Terminal. Keep existing executable, desktop and
configuration IDs to avoid breaking installations. Separate the Rust app under
`terminal/` from Python model work under `llm/`. Move generated local assets to
`artifacts/`, retain Git history and source-controlled datasets, and archive the
original research-only brief rather than presenting it as current app scope.
