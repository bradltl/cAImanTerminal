# Data structures and storage

> Scope: terminal application. Reviewed 2026-09-10 for the split workspace.
> Code is in `terminal/`; commands run from the repository root unless stated otherwise.
> Model research is documented in [llm/README.md](../../llm/README.md).

## Response v1

The grammar permits one object:

```json
{"action":"suggest_command","command":"df -h"}
```

Alternatives: `explain` with `explanation`, or `clarify` with `question`.
The parser rejects unknown fields, execution/tool actions, missing required text,
and commands attached to explanation-only responses. Risk is produced separately
by the host. The parser accepts optional explanation/plan prose; the compact
generation grammar emits command-only suggestions, with only one next command.

## Session

Each tab owns an ID, request ID, authenticated prompt generation, cwd, prompt state, input revision, remote state, pending
suggestion, cancellation counter, up to eight command records, and four recent
conversation entries. A command record has command, cwd, exit code, bounded
combined output, timestamp, and AI-origin marker. Output is limited to 2,500
characters per record. Model context includes the last three records.

`clear` changes VTE's display, not the journal. No database or cross-session memory
is created. Redaction runs before model context construction; it is heuristic,
not a guarantee against every secret format. The active terminal text is captured for each request, including file text already
printed there. Arbitrary files are not automatically read into context.

## Private shell IPC

A 0700 temporary directory per tab contains `bashrc`, a private `nonce`, the
`events` FIFO, and transient `stage` data. Events contain six NUL-terminated
fields: nonce, sequence, kind, exit status, cwd, text. The host reads at most
8192 bytes per poll and rejects records/buffers over 4096 bytes, forged nonces,
out-of-order sequences and explicit shell overflow. There is no append-only
command log. Temporary files are removed on orderly cleanup; crash cleanup and
malicious same-user access remain limitations.

The atomically replaced staging file contains prompt generation, expected CWD,
expected input and one printable ASCII candidate on four lines. Original Bash
checks all bindings before assigning `READLINE_LINE`; it never evaluates the file.

The immutable host staging snapshot also binds session/request IDs, context
generation and local prompt state. Fixed-size memory-only metric counters export
only numeric aggregates by explicit clipboard action. No content, paths, hashes,
free-form errors or persistent session IDs are retained in that metrics schema.

## Preferences and artifacts

`settings.json` is versioned, validated and written atomically under the stable
`cayman-terminal` XDG config directory. It stores theme, model selection, provider
IDs, inference limits and terminal/assistant preferences. Unknown extension fields
survive saves; future schema versions are rejected. The visible AI transcript is
separate from the bounded model conversation and lasts for the tab lifetime.

Source defaults are in `terminal/resources/default-model.txt`. Shared local
models, checkpoints and reports are under `artifacts/`, outside source control.
Research registry and datasets remain under `llm/`; see the workspace index.
