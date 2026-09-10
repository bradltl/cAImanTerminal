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

## Next slices

1. Reliable Bash integration across editing modes, completion systems, and
   multiline/pasted input; bounded IPC; trusted executable/alias metadata.
2. CLI-specific subcommand and short/long flag validation from installed help,
   with evidence-scoped repair and final-system benchmark reporting.
3. Remote shell integration and explicit file context with stronger secret policy.
4. Performance profiling, packaging, and complete PRD dogfood acceptance review.

Review responsibilities: inspect execution boundaries, lifecycle/cancellation,
context isolation, malformed model output, and unintended filesystem/network
activity. Verification remains required before a milestone is marked complete.

## Current priorities

Maintain the `terminal/` and `llm/` projects independently. Preserve provider
contracts and versioned settings, grow held-out runtime/model evaluations, and
address the shell integration and model-quality gaps listed in the backlog.
The workspace cleanup changes locations and branding, not model training data.
