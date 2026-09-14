# Development plan

> Scope: terminal application. Reviewed 2026-09-10 for the split workspace.
> Code is in `terminal/`; commands run from the repository root unless stated otherwise.
> Model research is documented in [llm/README.md](../../llm/README.md).

Consumed inputs: project overview, PRD, `docs/development/patterns/`, existing Python model harness,
model registry, and the saved unseen-suite comparison. The first slice follows
the native Rust/GTK4/VTE direction; the benchmark harness remains separate.

## Iteration 1 — implemented foundation

- Build native tabs, shell integration, and the assistant pane.
- Embed resident CPU inference with a strict response contract.
- Establish non-executing staging and a conservative host validation boundary.
- Test core invariants and exercise the actual GTK/Bash integration.
- Record implementation limits instead of treating the full MVP checklist as done.

## Current alpha delivery and next slices

1. Maintain the implemented authenticated FIFO, immutable staging snapshot,
   fixed-key boundary, narrow alpha CLI policy and explicit single-retry action.
2. Keep exact Rust/Python conformance, mutation, property, PTY and PR/nightly fuzz
   gates passing; retain discovered failures as regression cases.
3. Resolve measured model correctness and latency failures. Every release run
   must satisfy p50 ≤750 ms and p95 ≤1500 ms before alpha dogfood.
4. Keep v2/v3 regressions; defer v4 and broader remote/CLI/file capabilities.
   No new training corpus from automatic session capture.

Review responsibilities: inspect execution boundaries, lifecycle/cancellation,
context isolation, malformed model output, and unintended filesystem/network
activity. Verification remains required before a milestone is marked complete.

## Current priorities

Maintain the `terminal/` and `llm/` projects independently. Preserve provider
contracts and versioned settings, grow held-out runtime/model evaluations, and
address the shell integration and model-quality gaps listed in the backlog.
The workspace cleanup changes locations and branding, not model training data.
