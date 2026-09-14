# Runtime LLM harness

See [security hardening](../../docs/terminal/13_Security_Hardening.md) for the
authoritative current policy and new conformance/mutation/CI commands.

The desktop, `--ask`, and these tests use `worker::process`: deterministic host
hints, structured prompt, JSON contract, deterministic alpha correction, audited CLI
validation, intent/secret checks, and final risk assessment. Tests never execute model
suggestions. Stale tickets are rejected before and after inference; GTK also
checks the immutable session/request/prompt/CWD/input binding at completion and
acceptance. Bash independently rejects stale prompt generation, CWD and input.
Production also routes authorized task alternatives and verified literals without
inference. Adversarial/model tests select `process_model_candidate` to exercise
the same production model branch and final gates, without that shortcut. The
live-model regression still performs actual generation.

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
  current input, latest command/exit observation, provenance and host feedback are preserved.
  If these alone exceed the budget, the request fails explicitly.
- Context truncation is marked in the envelope. Read-only file/editor guidance
  still bypasses inference while crossing host validation.
- Malformed output, tone errors and unverifiable commands end the first inference.
  A separate Retry suggestion action permits one new inference with unchanged
  context. Safety/secret rejection and passive requests never retry or stage.
  Unknown intent and unsupported CLI coverage fail closed.
  Risk rejection is final. Cancellation and a 45-second inference deadline apply
  during prompt evaluation and output generation.

Coverage includes stale results, tab isolation, redaction, hostile section text,
context overflow, invalid schema, explicit retry limits, wrong-host commands, unknown flags,
critical commands, and terminal output overriding stale assistant suggestions.

The [alpha gate guide](../../docs/terminal/14_Alpha_Conformance.md) supplies exact
Rust/Python conformance, recording-boundary tests, proptest, libFuzzer, mutation,
real-PTY lifecycle and release latency commands. A native Unicode scanner crash
found by proptest is covered by ASCII-only command preflight and retained inputs.
The first full three-by-200 latency run failed; passing tests is not alpha approval.

## Observed v5 limitation

The initial v5 runtime check failed `terminal_over_stale_chat`: it proposed a
pacman README search instead of answering which filename the terminal printed.
The response-type gate now rejects this unrelated command, including a repeated
bad repair. The live semantic test exposes that model-quality limitation when v5 is selected;
tokenizer compaction passes. The default is now v2 at the user’s request. Do not interpret safe rejection as a
correct answer, or remove this regression to make the suite green.

## Assistive alpha verification update

Latency is diagnostic, not an alpha release requirement. The model generation
contract now requires an explanation for suggestions; the live-model regression
checks that field as well as command validity. `assistance_quality` verifies that
useful unverified advice is retained without becoming a staged command;
`assistive_policy` covers audited file operations and exact operand authorization.

The desktop/lifecycle tests exercise inline ghost text, real Tab acceptance and
a distinct physical Enter execution marker. Optional `gpu_runtime` verifies CPU
and requested-GPU paths with the verified model; actual offload requires a real
device and compatible build. See [GPU verification](../../docs/terminal/16_GPU_Acceleration.md).
