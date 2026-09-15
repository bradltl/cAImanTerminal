# cAIman Terminal — Deep Review Report

Current assistive-alpha pilot and regression counts are recorded in
[the September 14 aggregate](evidence/assistive-alpha-20260914.json). Historical
performance requirements and command-only response recommendations below are
superseded by the current PRD: explanations are required and latency is diagnostic.

> Superseded requirement: the user has removed alpha's fixed p50/p95 latency
> thresholds. The review and measurements below are historical evidence, not
> current latency acceptance criteria. Benchmarks now retain timing diagnostics
> and fail on incorrect command responses, not elapsed time. Correctness,
> completeness, explanations and explicit user submission remain priorities.
> See [current alpha acceptance](14_Alpha_Conformance.md#acceptance).

## Implementation review

The supplied analysis below is retained as a proposal, not verified evidence.
In particular, a closed JSON object cannot be extended by appending fields after
its closing brace, timed IPC waits wake immediately on readiness, and truncating
before secret detection can expose values whose labels were removed. The original
≤750 ms p50 / ≤1500 ms p95 release gates remain unchanged. Implementation results
and measured comparisons follow.

### Verified disposition

| Finding | Result |
| --- | --- |
| P1 / C1, JSON completion | Incremental, quote/escape-aware framing replaces full parsing after every token; the completed object must pass the production response schema. The proposed closed-object truncation mechanism was not valid JSON and was not reproduced. |
| P2, tokenization | Generation reuses the exact prepared tokens and the verified model's cached chat template. Compaction still uses exact full tokenization: BPE deltas and monotonic token counts cannot safely be assumed. |
| P3, model hashing | Not a warm-path cost. The supervised helper already verifies/seals once per resident model, off GTK. No mutable-file digest cache or skipped integrity check was introduced. |
| P4 / P7 / P8, context/redaction | Tail extraction scans backward; clean redaction borrows its input, allocates only for replacements, and private-key detection no longer builds a whole compacted copy. Detection remains before truncation to preserve secret labels and PEM headers. |
| P5, GTK polling | Worker results now wake a GLib future through an event stream; tab cleanup is event-driven. The per-tab 60 ms shell poll is retained: a readiness-only prototype reproducibly captured output before VTE rendered it, even at idle priority. That optimization was rejected and the original PTY tests pass again. |
| P6 / C5, IPC | Existing waits already wake on readiness and supervise cancellation. Receive timeouts are clamped to the deadline; a scope guard restores stdin flags on success and failure. Socket send timeouts are not a replacement for supervised pipe writes. |
| P9, prompt escaping | Single-buffer escaping preserves the previous bytes exactly, tested against serde plus the old delimiter escapes with generated Unicode inputs. |
| C2, kill arguments | Signals are distinguished from PID operands. Init, nonpositive/group targets, missing operands and unparseable PIDs fail closed. `kill` remains outside alpha CLI staging coverage. |
| C3 / C4, nested sudo | Nested sudo is rejected by risk and host checks; observed update classification recognizes repeated sudo without authorizing it. The alpha CLI manifest already blocked these candidates, so this was a lower-layer gap, not a demonstrated production escape. |
| C6, OS release | Cached for process lifetime in diagnostic model context; remote context remains empty. |
| C7, tabs | No change: tabs are ASCII, and the separate control-byte check intentionally rejects them in command candidates. Normal terminal typing is unaffected. |
| C8, validation metrics | RAII measurement scopes reset and restore thread-local state, including nested measurements. Calls outside a worker measurement do not accumulate timings. |

### Larger optimization: deterministic contract routing

The existing narrow intent registry already knows the authorized alternatives for
disk/memory usage, file listing, CWD, Git status and supported updates. Exact
literal commands also need validation, not inference. Production now tries those
candidates deterministically through the same parser, CLI, intent, secret, risk,
previous-failure and context gates, then revalidates and binds the final result.
It does not add commands, guess operands or use terminal evidence as authority.

`process_model_candidate` and `CAYMAN_BENCH_MODEL_PATH=1` retain the actual model
branch with all the same gates. Adversarial tests, malformed-response tests and
live-model regression explicitly exercise this branch, so deterministic answers
cannot hide dangerous candidates or erase model failures. The trusted-runner CI
job separately gates and retains three-by-200 reports for both routes.

### Measured results (release build, i7-1355U, two threads)

The original frozen corpus and thresholds were not changed:

| Route | Measured requests | p50 | p95 | Unstageable |
| --- | ---: | ---: | ---: | ---: |
| Production, run 1 | 200 | 0.113 ms | 0.195 ms | 0 |
| Production, run 2 | 200 | 0.085 ms | 0.158 ms | 0 |
| Production, run 3 | 200 | 0.102 ms | 0.258 ms | 0 |
| Model-candidate diagnostic pilot | 20 | 3140 ms | 3434 ms | 4 |

All 600 production cases used the deterministic route. Those figures measure
enqueue through completed worker validation, not keyboard-to-render latency or
faster inference. The production cold sample was 4.65 ms and did not load model
weights. The model pilot used the pinned verified v2 weights and retained fresh
per-request KV state. Median preparation was 1.15 ms, prefill 2395 ms, decode
734 ms, with approximately 372 input and 20 output tokens—not the review's
estimated 2K input / 200 output tokens. Some local compilation overlapped the
pilot; it is diagnostic evidence, not a fresh release certification.

The software cleanups did not recover the proposed 5–10% model failures. The
material production improvement comes from avoiding unnecessary inference.
The frozen supported-command corpus now passes; broader model-response quality,
model-path latency and end-to-end desktop acceptance remain open. Do not declare
alpha ready or relax its targets based on this deterministic corpus alone.
See [numeric evidence](evidence/performance-review-20260914.json).

### Regression coverage

`performance_correctness`, `response_stream`, prompt escaping properties, metric
scope tests and supervised-process tests cover these fixes. The exact conformance
corpus now has 101 cases. Real Bash/VTE desktop and lifecycle tests cover the
retained shell poll, explicit retry and physical-Enter staging boundary. The
worker event-stream test verifies ordered main-context delivery and closure.
The final 30-second instrumented fuzz smoke completed 119,875 inputs without a
failure. It ran outside the local sandbox because LeakSanitizer cannot perform
its shutdown check under that sandbox's tracing restriction; sanitizers remained
enabled. PR and scheduled CI retain their normal sanitizer configuration.

## Supplied review (unverified estimates and recommendations)

> [!IMPORTANT]
> Alpha dogfooding is blocked by **latency** (p50 ~3.1s vs. target ≤750ms) and **correctness** (40/200 unstageable responses). This review identifies root causes in both areas plus a goal-achievability assessment.

---

## 1. Performance Issues

### 🔴 Critical — Directly Contributing to Latency Miss

#### P1: O(N²) JSON parsing in generation loop
**File:** [inference.rs](../../terminal/src/inference.rs)

```rust
result.push_str(&self.model.token_to_piece(token, &mut decoder, true, None)?);
if serde_json::from_str::<serde_json::Value>(&result).is_ok() {
    return Ok(result);
}
```

On **every decoded token**, the entire accumulated result is re-parsed as JSON. For a 200-token response, this is ~200 parse attempts on a growing string — O(N²) total work. This also causes the **eager termination bug** (see Correctness section below).

**Fix:** Track brace/bracket depth with a simple counter. Only attempt a full parse when `depth == 0` and the last character is `}`.

#### P2: Repeated tokenization in prompt compaction loop
**File:** [inference.rs](../../terminal/src/inference.rs)

The `prepare_prompt` loop calls `apply_chat_template` + `str_to_token` on every iteration of `compact()`. Each trim step re-tokenizes the *entire* prompt string. If 5 compactions are needed, 6 full tokenizations occur.

**Fix:** Binary search on context budget, or cache the token count delta from what was removed rather than re-tokenizing everything.

#### P3: Synchronous model file hashing on the worker thread
**File:** [inference.rs](../../terminal/src/inference.rs)

`VerifiedModel::open` reads and SHA-256-hashes the entire model file (potentially hundreds of MB) synchronously. This delays first-request readiness significantly.

**Fix:** Hash in a background thread during startup, or cache the hash after first verification.

#### P4: Redaction before truncation — processing megabytes to keep 2,500 chars
**File:** [context.rs](../../terminal/src/context.rs)

```rust
record.output = bounded(&redact(&record.output), 2500);
```

`redact()` runs 6 regex replacements against the **full unbounded output** (which could be megabytes of `make` or `cargo build` output), and only afterward is it truncated to 2,500 chars.

**Fix:** Truncate *first* (to e.g. 3000 chars to account for redaction text expansion), *then* redact.

### 🟡 Moderate — Latency/CPU Contributors

#### P5: Two 60ms polling loops on the GTK main thread
**Files:** [ui.rs L843](../../terminal/src/ui.rs) and [ui.rs L1138](../../terminal/src/ui.rs)

Two independent `glib::timeout_add_local(60ms)` timers continuously poll:
1. Each tab's `poll()` method (per-tab timer)
2. The `worker.events` channel via `try_recv()` (per-window timer)

Both fire continuously regardless of activity, consuming CPU and battery.

**Fix:** Replace the worker event poll with `glib::MainContext::channel()` for event-driven wakeup. For the tab poll, use VTE signals to trigger state checks instead of blind polling.

#### P6: IPC spin-polling with 20ms timeout loops
**Files:** [model_process.rs L108](../../terminal/src/model_process.rs) and [model_process.rs L146-L154](../../terminal/src/model_process.rs)

Both `receive()` and `send()` use tight loops with 20ms sleeps/polls, adding up to 20ms of wasted latency per IPC round-trip.

**Fix:** Use blocking `recv()` with a deadline for receive. For send, use blocking I/O with `SO_SNDTIMEO` instead of `O_NONBLOCK` + poll loop.

#### P7: `bounded()` iterates chars twice
**File:** [context.rs](../../terminal/src/context.rs)

```rust
let n = text.chars().count();        // O(N) iteration
text.chars().skip(n - chars).collect() // O(N) iteration + allocation
```

For large inputs this is two full UTF-8 scans plus a new allocation.

**Fix:** Use `text.char_indices()` to find the byte offset of the Nth-from-last char, then slice directly with `&text[offset..]`.

### 🟢 Minor

#### P8: `secrets::redact` always allocates 6 string clones
**File:** [secrets.rs](../../terminal/src/secrets.rs)

The `.fold()` calls `.into_owned()` on every pattern, even when no match occurs (and `replace_all` returns a `Cow::Borrowed`).

**Fix:** Check `Cow::Borrowed` before calling `.into_owned()`, or use a single pass that only allocates when a match is found.

#### P9: `prompt::render()` quote closure creates 5 intermediate strings
**File:** [prompt.rs](../../terminal/src/prompt.rs)

`serde_json::to_string` followed by 4 chained `.replace()` calls allocates 5 `String`s per quoted section.

**Fix:** Write to a single `String` buffer with a custom escaper.

---

## 2. Correctness Issues

### 🔴 Critical — Affects Staging Correctness

#### C1: Eager JSON stop condition truncates model output
**File:** [inference.rs](../../terminal/src/inference.rs)

The JSON parse check on every token means generation aborts as soon as a *syntactically valid* partial JSON object is formed. If the model outputs `{"action": "suggest_command"}` before appending `"command": "ls -la"`, generation stops prematurely with a structurally valid but semantically incomplete response.

**Impact:** This directly contributes to the 40/200 unstageable response rate — the model may be producing correct responses that are cut off.

**Fix:** Only terminate on brace-depth == 0 AND encountering an EOG token or the grammar's root acceptance state.

#### C2: `kill` signal false positive
**File:** [host.rs](../../terminal/src/host.rs)

```rust
if exe == "kill" && args.iter().any(|a| ["-1", "0", "1"].contains(&a.as_str())) {
```

`kill -1 <PID>` sends SIGHUP (signal 1) to a specific process — a perfectly valid command. But this rule blocks it because `-1` appears in the args list. The check conflates signal numbers with PID arguments.

**Fix:** Parse `kill` arguments positionally: distinguish `-<signal>` flags from PID arguments. Alternatively, only block bare `kill -1` (no further PID arguments) or `kill -- -1`.

#### C3: Nested `sudo` bypasses validation
**Files:** [command_validation.rs L73-L81](../../terminal/src/command_validation.rs) and [host.rs L187-L194](../../terminal/src/host.rs)

Both `unwrap_sudo()` and `assess_risk()` strip only one layer of `sudo`. A command like `sudo sudo rm -rf /` passes through with `exe = "sudo"`, which isn't in the `rm` blocklist.

**Mitigating factor:** `sudo` is not in the interpreter/wrapper blocklist in `assess_risk()`, but `host.rs:207` *does* block `su`, `doas`, `pkexec`. The `sudo` case specifically slips through because it's handled as a prefix strip rather than a blocked wrapper.

**Fix:** After stripping `sudo`, reject `words[0]` if it is also `sudo`, `su`, `doas`, etc. Or loop the strip.

### 🟡 Moderate

#### C4: `is_system_update` fails on nested sudo
**File:** [command_validation.rs](../../terminal/src/command_validation.rs)

Same single-unwrap issue: `sudo sudo apt update` → inner exe is `"sudo"` → not in the package manager list → fails to be identified as a system update → follow-up intent handling breaks.

#### C5: O_NONBLOCK not restored after `send()`
**File:** [model_process.rs](../../terminal/src/model_process.rs)

`send()` sets `O_NONBLOCK` on the child's stdin fd but never restores the original flags. Currently safe because the fd is used exclusively for sequential writes, but fragile if the code evolves.

#### C6: `model_context()` reads `/etc/os-release` on every call
**File:** [context.rs](../../terminal/src/context.rs)

```rust
"platform": if self.remote { String::new() } else { std::fs::read_to_string("/etc/os-release").unwrap_or_default() },
```

This performs synchronous filesystem I/O every time `model_context()` is called. Should be cached at startup.

### 🟢 Minor

#### C7: Tab character (`\t`) rejection
**File:** [host.rs](../../terminal/src/host.rs)

The ASCII-only check on L128 means tabs never reach L131 in practice (tabs are ASCII), but `c.is_control()` would reject tabs if the ASCII gate were ever relaxed. Currently a latent issue, not a live bug.

#### C8: Thread-local metric leak across non-worker contexts
**File:** [worker.rs](../../terminal/src/worker.rs)

`CANDIDATE_VALIDATION_MS` is a thread-local that accumulates timing. Only the worker thread resets it. If `check_candidate` is called from tests or benchmarks on other threads, the metric accumulates incorrectly.

---

## 3. Goals Assessment

### Original Goals vs. Reality

| Goal | Target | Current State | Status |
|------|--------|---------------|--------|
| Local CPU inference | p50 ≤ 750ms | p50 ~3,100ms | ❌ **4.1× over** |
| Stageable responses | High acceptance | 160/200 (80%) | ⚠️ 20% rejected |
| Deterministic safety | Fail-closed | Working, tested | ✅ |
| GTK4/VTE terminal | Tabs, themes | Functional | ✅ |
| User-only execution | @ + Enter | Implemented | ✅ |
| Settings/packaging | Desktop install | Working | ✅ |
| Privacy (local-only) | No network | Achieved | ✅ |

### What's Working Well
- **Architecture is sound.** Clean separation: VTE terminal ↔ host validation ↔ worker thread ↔ model backend. Each layer is testable independently.
- **Safety pipeline is thorough.** Tree-sitter parsing, risk classification, credential detection, package manager awareness, and alpha conformance testing are all implemented.
- **The modular model backend** (direct `llama.cpp` vs. process model) is a good design for future GPU/API expansion.

### What's Blocking Alpha

> [!CAUTION]
> The two blocking issues — latency and response accuracy — are **partially the same bug**. The eager JSON termination (C1) both truncates valid responses (hurting correctness) and wastes generation time on responses that will be rejected downstream (hurting latency).

**Latency breakdown estimate** for a typical request:
- Model file hash (first request): ~500-2000ms (P3)
- Prompt tokenization loop: ~200-800ms extra from re-tokenization (P2)
- Prefill (CPU, 0.5B model, ~2K tokens): ~1000-1500ms (hardware bound)
- Decode (~200 tokens): ~500-1000ms (hardware bound)
- O(N²) JSON parsing during decode: ~200-500ms (P1)
- IPC overhead: ~40-100ms (P6)
- Redaction of large outputs: ~50-200ms (P4)

The hardware-bound prefill+decode is ~1500-2500ms. The software overhead adds another ~1000-3500ms on top. **Fixing P1-P4 alone could bring the p50 from ~3.1s to ~1.5-2.0s** — still above the 750ms target, but much closer.

### Are the Goals Achievable?

**Yes, with caveats:**

1. **The 750ms p50 target on CPU is extremely ambitious** for a 0.5B model with 2K-token contexts. Even with all software fixes, you're likely looking at ~1.5s minimum for a full inference round-trip on CPU. Options:
   - ✅ Accept ~1.5s as the CPU baseline and call it "good enough for alpha"
   - ✅ Explore GPU acceleration (`n_gpu_layers > 0`) — likely gets you to <500ms
   - ✅ Smaller/more-quantized model (Q4_0 instead of Q5 or whatever is current)
   - ✅ Expand deterministic host guidance to handle more cases without inference

2. **The 80% acceptance rate can be improved to ~90%+** by:
   - Fixing the eager JSON termination (C1) — likely recovers 5-10% of failures
   - Expanding `IntentContract` and `guidance.rs` deterministic paths
   - Fine-tuning the model on the specific failure patterns from the conformance suite

3. **Scope risks:**
   - Shell state coupling (CWD, prompt detection) is inherently brittle for complex workflows
   - The validation strictness that provides safety also limits usefulness — every unknown subcommand is rejected
   - Cross-platform (beyond Linux/GTK/Bash) remains far away

### Recommended Priority Order

```mermaid
flowchart LR
    A["Fix C1: JSON termination"] --> B["Fix P1: O(N²) parsing"]
    B --> C["Fix P4: Redact after truncate"]
    C --> D["Fix P2: Tokenization caching"]
    D --> E["Fix P6: IPC blocking I/O"]
    E --> F["Fix C2: kill signal parsing"]
    F --> G["Measure again"]
    G --> H{"p50 ≤ 1.5s?"}
    H -->|Yes| I["Ship alpha with relaxed target"]
    H -->|No| J["Enable GPU layers"]
```

> [!TIP]
> Fixes C1 + P1 + P4 are high-impact, low-risk changes that could be done in a day. They address both the latency and correctness blockers simultaneously. I'd recommend starting there and re-benchmarking before tackling the architectural changes (event-driven UI, IPC rework).
