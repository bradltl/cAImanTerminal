# Open issues, risks and backlog

> Scope: terminal application. Reviewed 2026-09-10 for the split workspace.
> Code is in `terminal/`; commands run from the repository root unless stated otherwise.
> Model research is documented in [llm/README.md](../../llm/README.md).

This iteration is a working engineering slice, not the full PRD MVP or a safety-
certified release.

## Required before wider dogfood

- Extend shell integration beyond Emacs Readline; test custom prompts, nested
  shells, key bindings, history execution, multiline commands and bracketed paste.
- Bound/replace append-only private shell IPC and remove stale directories after
  crashes. Raw commands in IPC may contain secrets despite redacted model context.
- Resolve actual session executables, aliases and functions. Current executable
  checks use trusted system paths and cannot certify the meaning of a shadowed
  command in the user's shell.
- Expand CLI metadata beyond fixed cached help routes: argument arity, short
  options with attached values, exhaustive subcommands, man pages, and package
  existence. Unknown option evidence currently fails closed.
- The 0.5B model can still misread intent or fail its one repair. Host checks now
  reject foreign package managers and irrelevant searches for a system update,
  but general semantic correctness and prose accuracy are not guaranteed.
- Expand semantic risk analysis. Current unknown commands receive Caution, not a
  claim of safety. Critical regression coverage is finite and not a sandbox for
  arbitrary user commands or a hostile local process.
- Full raw-model versus final-system benchmark reports, model identity metadata,
  and the PRD's complete critical safety release gate.
- Cursor-aligned ghost rendering; the initial UI uses a suggestion strip.
- Remote prompt integration and remote `@`/staging. Current SSH handling pauses
  local assistance and marks the session remote.
- Explicit file context with a reviewed secret policy and source disclosure.
- Verify close-window behavior with foreground jobs; tab close currently refuses
  while a command is running.
- Measure release-mode request latency and memory on target hardware. The PRD's
  sub-1.5-second target is not yet established.

## Deferred product decisions

Packaging/model distribution, stronger secret detection, broader shell grammar,
optional GPU backends, persistent memory, richer undo, and non-Arch adapters.
