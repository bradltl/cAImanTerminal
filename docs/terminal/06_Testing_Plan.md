# Testing plan

Performance-review regressions cover nested sudo, kill signal/PID positions,
secret labels outside retained tails, Unicode quoting equivalence, incremental
JSON framing, request-scoped timings and ordered UI event delivery. Generated
candidate tests explicitly use `process_model_candidate` so a deterministic
fast answer cannot mask rejection tests. See [measurements and retained limits](15_Performance_Correctness_Review.md).

## Alpha release gates

Use [Alpha Hardening / Harness Conformance](14_Alpha_Conformance.md) for the current
commands, finding-to-test matrix, fixture schema and latency protocol. PRs require
exact conformance, parser properties, guard mutants, real GTK/Bash lifecycle and
bounded coverage-guided fuzzing. Longer fuzzing runs daily. Verified-model and
three-by-200 latency checks run only on an explicitly dispatched trusted runner;
they are not permission to run untrusted PR code on that runner. A green ordinary
PR does not certify alpha performance or permit an alpha release.

> Scope: terminal application. Reviewed 2026-09-10 for the split workspace.
> Code is in `terminal/`; commands run from the repository root unless stated otherwise.
> Model research is documented in [llm/README.md](../../llm/README.md).

## Deterministic host suite

`cargo test --no-default-features` exercises Bash AST parsing, quoting, pipeline
boundaries, hidden execution constructs, critical commands, risk classification,
response validation, sparse passive eligibility, remote evidence separation,
redaction, context bounds, partial shell event records, and staging control bytes.
These tests require no model or display.

## Real GTK / PTY test

`cargo test --lib desktop_flow -- --ignored --nocapture` opens a test window with
two real Bash sessions. It checks that an `@` request does not execute, staging
does not execute, a separate Enter creates the temporary marker, tab state stays
isolated, exit status is captured, `clear` preserves the journal, and stale
suggestions cannot be accepted. It also checks idle snapshot coalescing, passive
requests, failure output capture, suggested-command success follow-up, and full
worker mailbox retries. The test captures the actual GTK window to PNG.

## Model smoke and benchmark

`--ask` uses the same host pipeline as the UI, with the actual GGUF and SHA-256
reported. The Python project lives under `llm/`; run its tests from that directory.
Full final-system benchmark aggregation and the PRD's critical safety release
gate remain future work; passing the focused host tests is not a shipping claim.

## Manual acceptance

- Bash history, ordinary Tab completion, resize, scrolling, copy/paste, Ctrl-C.
- vim/less/top: keystrokes must go to the foreground program, without AI snapshots.
- AI disabled/missing weights: Bash remains usable; no download/network fallback.
- Rapid typing while inference runs: stale suggestion never appears or stages.
- New/closed tabs: no context crossover, no model reload per tab.
- Direct SSH: remote indicator; local assistance resumes only after local prompt.
- Close a running tab: require stopping the foreground work first.

Not yet certified: vi Readline, nested/local subshells, customized accept-line
bindings, multiline/bracketed paste edge cases, shell aliases, remote `@`, and
complete PRD performance/critical-safety acceptance.

## Static host audit

`--audit-report` replays each saved `parsed_command` through AST/risk validation.
It deliberately skips local executable availability so a missing binary cannot
hide a semantic safety failure. The report separates raw overall score, raw
critical cases, and critical candidates still stageable. This is narrower than
full final-system benchmarking. It returns a failing exit code if any recorded
raw critical candidate remains stageable.

`cargo test --test context_model -- --ignored --nocapture` loads the local GGUF
and supplies the apt/which failure sequence without an explicit request. The
current contract requires a useful validated system-update command and zero model
generations for these known host errors; a withheld candidate is no longer a pass.

`GDK_BACKEND=x11 CAYMAN_TEST_X11_KEYS=1 cargo test --lib desktop_flow -- --ignored
--nocapture` additionally uses XTest to type `find` into the dedicated verification
window. It exercises actual GTK key dispatch, Bash input capture, idle triggering,
and validated completion. No Enter is injected by that keyboard helper.

The X11 keyboard test also types `ps -`, checks request arrival under 650 ms
including typing overhead, verifies installed ps flag descriptions without model
inference, and checks that old assistant text clears. Flag contract tests cover
short commands, long prefixes, clusters, multiline help descriptions, pipelines,
end-of-options, remote suppression, and missing documentation.

## Split-workspace verification

From the root, run Cargo formatting, Clippy and both default/core test suites.
From `llm/`, run `../.venv/bin/python -m pytest tests` and `bench validate`.
The settings window is tested separately with
`cargo test --lib settings_ui::tests::settings_window -- --ignored --nocapture`.
Do not run GTK tests concurrently in the same test process.

The optional live-model regression and token-budget checks are documented in
[the runtime harness](../../terminal/tests/README.md). CI does not download model
weights or run expensive SFT jobs. Research `--system` scoring is implemented in
Python and must not be confused with proof of parity with the Rust app pipeline.
