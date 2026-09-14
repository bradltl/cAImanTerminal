# Alpha Hardening / Harness Conformance

Alpha is gated, not released. The target is `alpha-v1`: independent Rust and
Python decisions against the same host facts, request context and candidates.
Broader research results are not production conformance results.
The [subsequent performance review](15_Performance_Correctness_Review.md) adds
validated deterministic routing and separate model-path measurements. The old
three-by-200 failure table below is historical, not the current deterministic
route's latency. Model-response quality and model-path latency remain unresolved.

## Executable review and trust boundaries

Keyboard → VTE/PTY → original Bash → authenticated events → per-tab snapshot →
quoted prompt → supervised native model → response parser → alpha gates → bound
suggestion → private stage file + fixed widget key → Readline. Only a separate
user submission runs the resulting command. The worker has no terminal handle.
GTK completion and acceptance reject stale state; Bash independently checks
prompt generation, CWD and current input.

Concrete cases live in `terminal/tests/adversarial.json` (62 baseline controls),
`alpha-conformance.json`, and `prompt-injection.json`. They are executable
expectations, not model-generated gold. A finite corpus is not a general proof.

| Failure class / review result | Enforcement and regression |
| --- | --- |
| AI submission bytes, bracketed paste, alternate key paths | `execution_boundary`: recording adapter, fixed enum, source capability guard |
| Prompt renewal made an @ request immediately stale (confirmed, fixed) | `lifecycle_boundary`: request published after fresh prompt |
| Old stage file matched a later identical prompt (confirmed, fixed) | Bash generation check and real-PTY stale-file rejection |
| Tab close reentered a borrowed tab (confirmed, fixed) | Actual close-button lifecycle test |
| Delayed/duplicate callbacks, changed CWD/input, closed tabs | Snapshot dimensions, completion replay guard, lifecycle/boundary suites |
| Blocked replacement retained ghost text; passive acceptance; automatic repair | Production completion tests and single-inference assertions |
| LOCAL→SSH/wrapper/unknown program and return | Desktop pauses all running programs; original authenticated prompt resumes |
| Forged OSC7/133/52, FIFO replay/overflow | Desktop clipboard/OSC checks and authenticated-channel tests |
| Bash/parser differences: chains, substitutions, redirects, wrappers, quotes | Adversarial corpus, shrinking properties, parse-only Bash checks, libFuzzer |
| Native Bash scanner crashed on Unicode lookahead (confirmed, contained) | ASCII-only command preflight before native parsing; seed-18 regression |
| Filename prefix authorized a different file (confirmed, fixed) | Exact filename-token binding and supported read positive controls |
| Chat delimiters survived JSON quoting (confirmed, fixed) | Angle/bracket escaping across evidence sources and compaction |
| Untrusted help extended CLI coverage | Manifest-only capabilities and hostile-help conformance |
| Negative intent test was masked by CLI rejection (mutation gap, fixed) | Supported-command negative controls and intent mutant |
| Correction invented operands or retained stale explanation | Canonical task correction, final gates, host-owned replacement explanation |
| Model replacement, malformed GGUF, hang/crash/cancellation | Sealed-model, bounded-process and verified live-model tests |
| Secrets reached prompts/staging/export | Secret corpus, final stage scan, numeric-only export schema |
| Research replay silently changed meaning or holdout status | Existing provenance/replay tests and dataset audit |
| Pinned disagreements were called conformance (confirmed, replaced) | Exact alpha comparison without baseline-record mode |
| First-token latency substituted for a completed valid answer | Supervised-worker benchmark from enqueue through final validation |

Limits: malicious same-UID configuration is outside this boundary; secret
detection is heuristic; remote commands and passive staging remain unsupported.
PTY coverage uses real local Bash and running/unknown transitions, not production
SSH credentials. Native isolation contains crashes; it is not an OS sandbox.

## Versioned policy

`terminal/resources/alpha-policy.json` defines audited CLI coverage. Installed
executable presence alone does not prove CLI validity. Unknown commands, options,
subcommands and unsupported operand shapes fail closed. Documentation remains
untrusted evidence and cannot add capabilities to this manifest. Literal requests
authorize only their exact candidate, subject to every remaining gate.
Command staging is printable ASCII only: property testing found a native scanner
`isdigit` call on a wide Unicode code point. The preflight rejects non-ASCII
before entering native code. Unicode terminal input and quoted evidence remain
supported; users may type unsupported commands manually.

The deterministic trace records the contract, context validity, initial and final
parser/CLI/intent/safety/secret/risk decisions, correction rule, final command and
stageability. Unknown and skipped checks are not successes. The sole automatic
candidate correction chooses the first approved alternative for a known task
after invalid CLI options, and rechecks every gate; syntax/safety/secret failures
never enter correction. No literal-command operands are invented.

Versioned `--policy-check` accepts a candidate or raw response, session context,
and host facts. It invokes the worker's shared deterministic candidate boundary
and production response parser. It does not invoke a model, execute commands,
or certify broader Python research preflight behavior. Python independently
resolves and validates the same data. Legacy unversioned checks are diagnostics,
not conformance evidence. There is no automatic exception approval.

## Running the gates

```sh
cargo fmt --all -- --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
cargo build --locked
.venv/bin/python -m pytest llm/tests
.venv/bin/python llm/tools/conformance.py
.venv/bin/python llm/tools/mutation_check.py
cargo +nightly fuzz run shell_boundary -- -max_total_time=60 -max_len=4096 -timeout=5
```

CI runs GTK tests individually under Xvfb: `desktop_flow`, `lifecycle_boundary`,
`disabled_ai_hides_pane`, and `settings_window`. Desktop flow includes physical
key synthesis; lifecycle emits a machine-readable summary. PR fuzzing is bounded;
scheduled runs use 15 minutes and retain failures. The local 30-second instrumented
smoke test completed 186,192 inputs without failure; a post-containment rerun
with the retained Unicode seed completed another 128,177 inputs in 31 seconds.
All four guard mutants died in the final rerun.

## Performance protocol

Build with `cargo build --release --locked`, then run
`./target/release/caiman-terminal --alpha-benchmark > alpha-latency.json`.
Defaults: three runs of 200 requests from the frozen short-command corpus, using
the desktop's bounded queue, worker and supervised model. Commands never execute.
The cold request is separate; no mutable KV/prefix state crosses requests.
Numeric timings cover prompt preparation, prefill, decoding, first token and token
counts. `load_ms` is the model's one-time load, not a cost repeated every request.
Worker diagnostics also retain failed-generation timings, inference IPC round-trip,
host processing (including prompt/evidence work), candidate-gate validation, and
queue-plus-delivery overhead. They contain only numeric measurements.

`CAYMAN_BENCH_THREADS` permits explicit tuning; `CAYMAN_BENCH_SAMPLES` and
`CAYMAN_BENCH_RUNS` permit pilots. Pilots cannot pass release acceptance. Reports
separate model, deterministic, correction and rejected paths. Invalid/unverified
responses fail the gate regardless of latency.
`CAYMAN_BENCH_MODEL_PATH=1` skips the canonical-command fast path while retaining
the production model branch and every gate. Always report this separately from
normal routing; fast deterministic responses are not evidence of model speed or
model accuracy. The expected model digest is configuration metadata until model
generation actually loads and verifies the weights.
Explicit `CAYMAN_BENCH_RETRY=1` profiles a simulated single Retry suggestion action
after eligible verification failures. These measurements remain separate and
never replace first-attempt failures in the acceptance distribution.
A separate 20-request named-file calibration uses a temporary synthetic README
through the same worker, then removes the fixture. It reports the deterministic
path independently; it does not dilute the frozen model corpus's latency gate.
The final diagnostics pilot exercised one eligible explicit retry and 20/20
validated deterministic calibrations (p50 0.083 ms, p95 0.145 ms). It confirms
instrumentation and path separation only, not latency acceptance.

Portable-release pilots (20 requests): baseline p50/p95 8098/8826 ms, 6 failures;
compact policy/command-only output 4200/4816 ms, 6 failures; explicit contract
hints with two threads 3156/3905 ms, 4 failures. These are exploratory results,
not acceptance certification. The strict gate remains closed.

The full target-workstation run completed with the frozen corpus and verified v2
model, two threads, and 200 warm requests per run:

| Run | p50 | p95 | Unstageable responses |
| --- | ---: | ---: | ---: |
| 1 | 3102.6 ms | 3725.3 ms | 40/200 |
| 2 | 3124.0 ms | 3573.4 ms | 40/200 |
| 3 | 3118.5 ms | 3682.0 ms | 40/200 |

Cold completion: 3726.0 ms. Every run fails both latency and correctness gates.
Other local regression work overlapped some measurements; these are failed
engineering measurements, not an isolated release certification. The measured
release preceded the final diagnostic extensions and Unicode parser containment;
the ASCII corpus and inference settings were unchanged. Numeric evidence is in
[the aggregate report](evidence/alpha-latency-20260911.json). A fresh isolated
three-by-200 run on the release candidate remains mandatory before dogfood.

## Acceptance

Zero deterministic discrepancies and observed dangerous escapes; passing boundary,
property/fuzz and real-PTY suites; all final staging gates satisfied. Three release
benchmark runs of at least 200 warm explicit requests must each achieve p50 ≤750 ms
and p95 ≤1500 ms on the i7-1355U target with the verified current model. Invalid
responses are failures, not fast successes. No daily dogfood before these pass.

Dogfood measurement is memory-only with manual aggregate export. Never export
requests, commands, output, paths, content hashes or persistent session IDs.
V2/v3 remain regression suites; v4 is deferred until production stabilization and
deliberate sanitized contributions from real dogfood experience.
