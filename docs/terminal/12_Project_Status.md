# Project status

## Performance/correctness review — 2026-09-14

Implemented validated review fixes and deterministic routing for already-authorized
commands. The unchanged 600-request command corpus now validates 600/600 without
inference; per-run worker p95 is below 0.3 ms. This is not keyboard-to-render
latency or improved model quality. A separate 20-request model-path pilot remains
at p50 3.14 s / p95 3.43 s with four unstageable responses. Alpha is not approved.
Exact conformance now has 101 cases, with zero differences. Worker delivery is
event-driven; the shell polling optimization was rejected after real PTY tests
showed premature output capture. See [review and evidence](15_Performance_Correctness_Review.md).

The earlier alpha-hardening measurements below are retained as history.

## Current alpha-hardening status — 2026-09-11

Engineering preview only: **not alpha-ready**. The latest conformance suite has
98 paired cases with zero discrepancies/exceptions. New coverage includes the
production output adapter, request/prompt generations, real-PTY lifecycle races,
explicit retry, quoted prompt injection, proptest and coverage-guided fuzzing.
The verified live-model regression passes. Numeric session metrics remain local
and memory-only. Work is delivered as focused Conventional Commits on the
hardening branch; main is not changed.

The three-by-200 target-workstation run failed: p50 3.10–3.12 s, p95 3.57–3.73 s,
and 40/200 unstageable responses in every run. A property-test native Unicode
scanner crash was contained by ASCII-only command preflight, with regressions.
No pilot or failed response counts as an acceptance pass.
See [current evidence and limits](14_Alpha_Conformance.md).
Older results below are historical, not the current alpha acceptance state.

> Scope: terminal application. Reviewed 2026-09-10 for the split workspace.
> Code is in `terminal/`; commands run from the repository root unless stated otherwise.
> Model research is documented in [llm/README.md](../../llm/README.md).

## Current snapshot — 2026-09-10

The public app name is **cAIman Terminal**. App source, runtime tests and packaging
are in `terminal/`; Python evaluation, training and datasets are in `llm/`.
Existing local models, checkpoints and reports have moved to `artifacts/` and
remain untracked. Product documents are in `docs/terminal/`; initial research
briefs are explicitly archived under `docs/research/archive/`.

The app includes centralized settings, provider interfaces, token-aware context
management and the host validation harness. Qwen SFT v2 remains the default.
The executable and manual are `caiman-terminal`. The installer forwards the old
`cayman-terminal` command to the new launcher. The existing configuration directory
and `io.cayman.Terminal` desktop ID remain compatible. New operating-system and
terminal providers are not shipped.

## Implementation history

**2026-09-09 — First native application iteration built and verified.**

Implemented: Rust/GTK4/VTE application, independent Bash tabs, collapsible assistant
pane, `@` interception, Readline staging without submission, bounded per-tab
journals, exit status/cwd capture, passive eligibility, input revision cancellation,
embedded resident llama.cpp, constrained JSON, AST/risk validation, fixed local
help routes, one bounded repair, and a headless final-pipeline entry point.

Default model: local SFT v2 GGUF, restored at the user’s request.
No new training or model artifact changes are part of this work.

Inputs reviewed: `01_Project_Overview.md`, `02_Product_PRD.md`, all `docs/development/patterns/`
documents, existing model runtime/configuration, and saved benchmark comparison.
Assumptions: Linux/Arch first, Emacs Readline for this slice, local preinstalled
GGUF, conservative unsupported-syntax rejection, and no remote shell integration
yet. The complete MVP acceptance checklist remains open.

Verification results are recorded below. Known gaps and next steps are tracked
in `11_Open_Issues_Risks_and_Backlog.md`.

## Completed verification

- Native debug executable built successfully and opened on the desktop.
- 13 Rust host regression tests passed.
- Real GTK/Bash PTY integration test passed (two tabs, @ interception, staging
  versus Enter, exit status, clear/history retention, and stale suggestions).
- Actual GTK capture: `/tmp/cayman-terminal-smoke.png`.
- Rust formatting and Clippy with warnings denied passed.
- 15 existing Python harness tests passed. One stale domain-filter test was
  corrected to verify the current scenario IDs instead of assuming eight files.
- Real local SFT v2 inference returned a validated log-file `find` recommendation.
  A cold headless request took 8.594 seconds; this is not a p50/p95 measurement
  and does not meet the PRD latency target.
- Full 100-scenario unseen raw regression reproduced the existing 71.9% score and
  27% strict command correctness. Raw critical safety violations remain in the
  model output; no model training was changed.
- Static host replay blocked all seven raw critical candidates, with zero still
  stageable. 66 of 100 scenarios had a candidate accepted by static validation;
  acceptance does not establish semantic command correctness.

Evidence:
`artifacts/results/qwen2.5-0.5b-sft-v2-1788982432-86563b.json`,
`artifacts/results/cayman-host-audit-iteration1.json`.

This completes iteration 1 as an engineering preview. Full CLI validation,
remote assistance, file context, crash-safe/bounded IPC, and latency targets remain
open. The earlier preview window must be restarted to load the final safety fixes.

## UI revision

Replaced the initial sidebar UI with a compact tmux-like terminal split. The
assistant now uses terminal typography/colors and says only `Ready..` when loaded.
Removed the branded header, welcome copy, stage button, and inference footer.
Added reorderable tabs, Ctrl+Shift+T/W, Shift+Left/Right, Ctrl+PageUp/PageDown, and
Ctrl+Shift+A to hide/show AI. Optional AI controls are in the compact tab-bar menu.
All 13 Rust host tests, the real GTK/Bash staging test, formatting, and Clippy pass.
Updated screenshot: `/tmp/cayman-terminal-smoke.png`.

## Idle assistance and host pipeline revision

Removed per-key Readline redraw requests and reserved the suggestion strip height.
One snapshot follows 350 ms idle; eligible inference follows 650 ms. Added automatic
follow-up on failures and completed suggested commands, durable per-tab intent,
visible thinking status, and retry after a full worker mailbox.

Implemented distro/native-manager checks, redundant missing-tool lookup rejection,
pacman privilege checks, cached fixed local help, long/short option evidence, one
repair followed by revalidation, and final deterministic risk assessment. Added
an initial system-update intent check to reject irrelevant pacman searches.

Verification: 25 deterministic Rust tests pass in core and full builds; the real
GTK/Bash test passes with idle reads, failure-output capture, automatic follow-up,
mailbox retry and existing staging/tab-isolation checks. All 15 Python tests pass.

The actual SFT v2 model still failed to repair both recorded apt/which failures
usefully; the host correctly withheld both invalid repaired candidates and
returned a visible explanation. The two-request local-model test took 68.63 s
including repair inferences. This verifies rejection and context plumbing, not
model usefulness or the PRD latency target. Improving model quality and latency
remains necessary. Restart existing preview windows to load this build.

## Known-error and find-trigger correction

The reported sarcastic clarification was model-generated prose, which previously
bypassed command validation. Known package-manager errors now receive direct host
explanations and validated native-update suggestions, including the explicit
`@ explain the error` path. Common `find` input also receives direct guidance;
bare `find` and short find options now pass the idle trigger. Other model responses
have bounded tone/agency checks sharing the existing one-repair budget.

The recorded `apt update`, `apt get upgrade`, and `which apt` sequence now produces
`sudo pacman -Syu` in every case, with zero model generations. Host response times
in the integration check were 45, 3, and 1 ms, excluding the idle debounce and UI
polling. The model-loaded test completed in 0.95 s. This supersedes the earlier
68-second failed-repair result for these known cases; general model limitations
still apply to other requests.

30 deterministic Rust tests and the real GTK/Bash test pass. The GTK test now
also exercises actual X11 keyboard events: type bare `find`, wait for idle, obtain
`find . -type f`, and clear the line without executing it. Formatting, Clippy and
the native build pass. Restart the application to use this revision.

## Flag guidance and shorter idle delay

Added command-independent flag triggers, including the four-character `ps -`
case, short options, long prefixes and the last command in a pipeline. Direct
installed-help descriptions use ps's complete help and bounded man-page fallback.
No inference or automatic flag selection is involved. Missing documentation is
reported without invented options. Previous assistant text clears on editing.

Idle thresholds are now 150 ms for the Readline snapshot and 250 ms for assistance,
down from 350/650 ms. The real X11 keyboard test produced the `ps -` request in
440.8 ms including typing and test overhead, and verified installed descriptions.
All 34 deterministic Rust tests and the GTK/Bash keyboard test pass. Clippy passes.
The final build must explicitly include desktop and inference after core tests.

## Caiman icon, terminal themes, and man page

Added original character-grid caiman artwork as an embedded SVG/window icon and
freedesktop launcher icon, plus an ASCII mascot in CLI help. Added Dracula, Nord,
Gruvbox Dark, Catppuccin Mocha, and Tokyo Night alongside cAIman. The Theme menu
updates both panes and all terminal palette/cursor/selection colors immediately;
new tabs inherit the choice. Preferences persist atomically in XDG configuration.
Added --theme, --list-themes, --version, and a full caiman-terminal(1) manual.

The local installer was staged and validated, then installed under ~/.local.
`caiman-terminal --version` and `man -w caiman-terminal` resolve correctly.
The installed binary is separate from Cargo's development/test target.

Verification: 36 deterministic Rust tests, 15 Python tests, Clippy, formatting,
and the real GTK/Bash/X11 test pass. GTK parsed all six themes without CSS errors;
both terminal backgrounds and retained session context were checked. Icon lookup,
all six palette captures, SVG rendering, desktop-file validation, and man-page
formatting passed. Palette previews are /tmp/cayman-theme-<id>.png and the icon
preview is /tmp/cayman-icon-preview.png. Theme sources and licenses are bundled.

## 2026-09-10 — Maintainability and settings

Default restored to Qwen SFT v2. Added versioned settings and a central GTK settings
window; model precedence now respects saved choices ahead of the launcher fallback.
Introduced compiled provider boundaries for models, terminal surfaces, shells and
host operations. Existing command-help routes live in `command_profiles`; help
cache entries expire and track executable changes. Current platform support remains
Linux/Bash/VTE/llama.cpp. See the architecture document for remaining porting work.

## Split-workspace verification — 2026-09-10

After relocation: 49 deterministic Rust tests pass with default features and with
core-only features; 34 Python tests pass from `llm/`; 157 default scenarios validate.
The mock `bash-001` benchmark completes with a passing score. Rust formatting and
Clippy pass, the real GTK/Bash desktop flow passes, Python sources compile, and
checked local Markdown file links resolve. The temporary desktop installation
validates and displays cAIman Terminal with the relocated v2 fallback model path.
No SFT job or broad live-model quality evaluation was rerun for this cleanup.
