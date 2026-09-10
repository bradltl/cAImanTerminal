# Data structures and storage

> Scope: terminal application. Reviewed 2026-09-10 for the split workspace.
> Code is in `terminal/`; commands run from the repository root unless stated otherwise.
> Model research is documented in [llm/README.md](../../llm/README.md).

## Response v1

The grammar permits one object:

```json
{"action":"suggest_command","command":"df -h","explanation":"Show filesystem usage."}
```

Alternatives: `explain` with `explanation`, or `clarify` with `question`.
The parser rejects unknown fields, execution/tool actions, missing required text,
and commands attached to explanation-only responses. Risk is produced separately
by the host. A plan is currently prose in `explanation`, with only one next command.

## Session

Each tab owns an ID, cwd, prompt state, input revision, remote state, pending
suggestion, cancellation counter, up to eight command records, and four recent
conversation entries. A command record has command, cwd, exit code, bounded
combined output, timestamp, and AI-origin marker. Output is limited to 2,500
characters per record. Model context includes the last three records.

`clear` changes VTE's display, not the journal. No database or cross-session memory
is created. Redaction runs before model context construction; it is heuristic,
not a guarantee against every secret format. The active terminal text is captured for each request, including file text already
printed there. Arbitrary files are not automatically read into context.

## Private shell IPC

A 0700 temporary directory per tab contains `bashrc`, `events`, and transient
`stage` data. Events contain four NUL-terminated fields: kind, exit status, cwd,
text. Individual shell text fields are bounded to 16,384 characters; the host
reads at most 64 KiB per poll. The event file is currently append-only during the
session and may contain sensitive raw command text. It is removed on orderly tab
cleanup; see the backlog for crash cleanup and bounded IPC transport work.

The staging file is atomically renamed, with expected input on the first line
and a single printable candidate on the second. Bash compares input before
assigning `READLINE_LINE`. It never sources or evaluates this file.

## Preferences and artifacts

`settings.json` is versioned, validated and written atomically under the stable
`cayman-terminal` XDG config directory. It stores theme, model selection, provider
IDs, inference limits and terminal/assistant preferences. Unknown extension fields
survive saves; future schema versions are rejected. The visible AI transcript is
separate from the bounded model conversation and lasts for the tab lifetime.

Source defaults are in `terminal/resources/default-model.txt`. Shared local
models, checkpoints and reports are under `artifacts/`, outside source control.
Research registry and datasets remain under `llm/`; see the workspace index.
