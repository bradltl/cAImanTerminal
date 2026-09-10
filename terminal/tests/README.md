# Runtime LLM harness

The desktop, `--ask`, and these tests use `worker::process`: deterministic host
hints, structured prompt, JSON contract, one shared repair, installed command
validation, intent checks, and final risk assessment. Tests never execute model
suggestions. Stale tickets are rejected before and after inference; GTK also
checks the ticket before displaying or staging a suggestion.

Run deterministic regressions:

```sh
cargo test --offline
```

Run the actual default GGUF (currently Qwen v2) (CPU inference):

```sh
cargo test --offline --test llm_harness default_model_harness -- --ignored --nocapture
```

This writes `/tmp/cayman-model-harness.json`, including the model path, case outcomes,
actual answers, latency, and tokenizer-budget result. A failed semantic case fails
the command even when the host safely rejected the answer. This is a small runtime
regression suite, not evidence of general model accuracy. The broader scenario
benchmarks in the repository remain necessary when evaluating model quality.

For the real GTK/Bash context and staging flow:

```sh
GDK_BACKEND=x11 CAYMAN_TEST_X11_KEYS=1 cargo test --offline --lib ui::tests::desktop_flow -- --ignored --nocapture
```

## Context policy

- `terminal/resources/default-model.txt` is shared by the app, installer, and harness.
- Each tab owns its journal, live terminal snapshot, and conversation. Every model
  inference starts with fresh KV state; only model weights are shared.
- Fields are redacted before entering a typed JSON envelope. The renderer retains
  SFT section labels and quotes external data so text cannot create real sections.
  This reduces boundary confusion; it is not a guarantee against prompt injection.
- The real model tokenizer counts the complete chat template and system prompt.
  Input is capped at 3700 tokens in a 4096-token context, reserving generation space.
- Compaction drops old conversation, older command history, then reduces terminal
  text and remaining history, and finally documentation. The current request,
  current input, latest command/exit observation, and repair reason are preserved.
  If these alone exceed the budget, the request fails explicitly.
- Context truncation is marked in the envelope. Read-only file/editor guidance
  still bypasses inference while crossing host validation.
- Malformed output, tone errors, and invalid commands share one repair budget.
  Risk rejection is final. Cancellation and a 45-second inference deadline apply
  during prompt evaluation and output generation.

Coverage includes stale results, tab isolation, redaction, hostile section text,
context overflow, invalid schema, repair limits, wrong-host commands, unknown flags,
critical commands, and terminal output overriding stale assistant suggestions.

## Observed v5 limitation

The initial v5 runtime check failed `terminal_over_stale_chat`: it proposed a
pacman README search instead of answering which filename the terminal printed.
The response-type gate now rejects this unrelated command, including a repeated
bad repair. The live semantic test exposes that model-quality limitation when v5 is selected;
tokenizer compaction passes. The default is now v2 at the user’s request. Do not interpret safe rejection as a
correct answer, or remove this regression to make the suite green.
