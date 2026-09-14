# Open issues, risks and backlog

> Scope: terminal application. Reviewed 2026-09-10 for the split workspace.
> Code is in `terminal/`; commands run from the repository root unless stated otherwise.
> Model research is documented in [llm/README.md](../../llm/README.md).

This iteration is a working engineering slice, not the full PRD MVP or a safety-
certified release.

## Required before wider dogfood

Alpha is blocked: each of three 200-request runs had 40 unstageable responses,
p50 3.10–3.12 s and p95 3.57–3.73 s. Required limits remain ≤750/1500 ms.
See [evidence and release gates](14_Alpha_Conformance.md). Passing finite safety
regressions does not waive correctness or latency. V4 stays deferred.

- Extend shell integration beyond Emacs Readline; test custom prompts, nested
  shells, key bindings, history execution, multiline commands and bracketed paste.
- Remove stale temporary directories after crashes. Authenticated bounded FIFO
  transport has replaced the append-only shell log; stage data is transient.
- Resolve actual session executables, aliases and functions. Current executable
  checks use trusted system paths and cannot certify the meaning of a shadowed
  command in the user's shell.
- Broader CLI metadata is deferred. Alpha uses audited arity/flag/subcommand
  profiles and cannot stage unknown commands; help cannot expand coverage.
- The 0.5B model can still misread intent or fail an explicitly requested retry. Host checks now
  reject foreign package managers and irrelevant searches for a system update,
  but general semantic correctness and prose accuracy are not guaranteed.
- Expand semantic risk analysis. Unknown CLI coverage is unstaged regardless of
  the legacy risk score. Critical regression coverage is finite and not a sandbox for
  arbitrary user commands or a hostile local process.
- Full raw-model versus final-system benchmark reports, model identity metadata,
  and the PRD's complete critical safety release gate.
- Cursor-aligned ghost rendering; the initial UI uses a suggestion strip.
- Remote prompt integration and remote `@`/staging. Current SSH handling pauses
  local assistance and marks the session remote.
- Explicit file context with a reviewed secret policy and source disclosure.
- Verify close-window behavior with foreground jobs; tab close currently refuses
  while a command is running.
- Improve release-mode latency and model correctness without weakening gates;
  repeat the isolated target-hardware acceptance run after optimization.
- Restore non-ASCII command staging only after native Bash scanner Unicode
  safety is established. Unicode terminal text/evidence remains supported.

## Deferred product decisions

Packaging/model distribution, stronger secret detection, broader shell grammar,
optional GPU backends, persistent memory, richer undo, and non-Arch adapters.
