# Alpha Hardening / Harness Conformance

Alpha is gated, not released. The target is `alpha-v1.1`: independent Rust and
Python decisions against the same host facts, request context and candidates.
Broader research results are not production conformance results.
Alpha has no fixed latency requirement. Correctness, completeness, useful
explanations and user-controlled command submission take priority; latency stays
observable so CPU/GPU choices and future optimizations can be compared honestly.
The [subsequent performance review](15_Performance_Correctness_Review.md) adds
validated deterministic routing and separate model-path measurements. The old
three-by-200 failure table below is historical, not the current deterministic
route's latency. Model-response quality remains unresolved; its recorded latency
is diagnostic, not an alpha blocker.

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
The additive `alpha-v1.1` profile includes bounded direct `rm`, `rmdir`, `mkdir`,
`cp` and `mv` filesystem operations. These operations are
not automatically run: explicit command identity, CLI validation and the
independent staging boundary still apply, and mutation risk is shown as a
warning. Critical protected-target and credential checks remain enforced where
applicable to the operation: creating a directory is not classified as deleting
or overwriting one, and an audited two-operand copy reads its source rather than
mutating it. Supported flags may follow copy operands; the destination is the
last parsed operand, not necessarily the last argument. Unsupported copy option
forms remain conservatively rejected.
Known path operands are resolved lexically against the bound CWD before checking
protected mutations and credential paths. A relative `fstab` mutation at `/etc`
cannot evade the absolute-path check; copying that non-secret source to `/tmp`
remains distinct from modifying it. `cat shadow` at `/etc` is credential access,
whereas an identically named file at `/tmp` or `echo shadow` is not inferred to be
the same path. These checks do not resolve filesystem symlinks or claim universal
secret detection; unknown path roles do not gain staging authority.
Historical `alpha-v1` reports describe their original, narrower policy, not this
expanded coverage.
An unstaged answer need not discard useful assistance: otherwise well-formed,
secret-free and risk-checked proposals outside audited CLI coverage may remain
as explicitly unverified, JSON-quoted explanatory data with the model's rationale
and plan. They carry no command field or staging authority. A supported command
that mismatches the request likewise retains explanatory guidance, without a
host-added command proposal. Missing-host and invalid audited-CLI results remain
verification failures eligible for the separate explicit retry action; secrets,
control bytes and unsupported execution constructs remain hard rejections.
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
Raw assistant suggestions must include a nonempty explanation, alongside the
command, and pass the existing respectful/actionable prose checks. The worker,
completed model stream and raw-response policy fixture all invoke that same
assistant-response parser; Python independently enforces the same contract.
Missing, blank or malformed explanations cannot become staging successes.
Candidate-only fixtures remain deterministic command-boundary tests and do not
pretend to certify an assistant explanation. The requirement is a concise,
user-facing rationale—not hidden chain-of-thought or proof that every model
explanation is correct; representative quality review still matters.

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

`CAYMAN_BENCH_THREADS` permits explicit tuning. `CAYMAN_BENCH_GPU_OFFLOAD=1`
opts in to available compiled GPU support; `CAYMAN_BENCH_GPU_LAYERS` sets the
requested layer count (1–256, default 32). Reports identify requested settings
and compiled capabilities, neither of which proves a GPU actually served a
request. Use the model-candidate route for device comparisons: deterministic
requests need not load a model at all. Unavailable devices fall back to CPU.
`CAYMAN_BENCH_SAMPLES` and
`CAYMAN_BENCH_RUNS` permit pilots. Three-by-200 remains the recommended reporting
protocol, not an acceptance gate. Reports separate model, deterministic,
correction and rejected paths. Invalid/unverified responses still fail this
command-response benchmark regardless of latency; an explanation alone does not
complete a case that specifically asks for a stageable command.
`CAYMAN_BENCH_MODEL_PATH=1` skips the canonical-command fast path while retaining
the production model branch and every gate. Always report this separately from
normal routing; fast deterministic responses are not evidence of model speed or
model accuracy. The expected model digest is configuration metadata until model
generation actually loads and verifies the weights. The dispatched trusted-runner
job independently checks production and model-candidate response correctness with
one 20-request smoke run per route, retaining both timing artifacts even on failure.
Full three-by-200 profiling remains a recommended deliberate CLI measurement,
not an automatic CI or alpha latency obligation.
A fast canonical route cannot hide unresolved model-response failures. No p50 or
p95 threshold can fail either job.
Explicit `CAYMAN_BENCH_RETRY=1` profiles a simulated single Retry suggestion action
after eligible verification failures. These measurements remain separate and
never replace first-attempt failures in the correctness statistics.
A separate 20-request named-file calibration uses a temporary synthetic README
through the same worker, then removes the fixture. It reports the deterministic
path independently; it does not dilute the frozen model corpus's results.
The final diagnostics pilot exercised one eligible explicit retry and 20/20
validated deterministic calibrations (p50 0.083 ms, p95 0.145 ms). It confirms
instrumentation and path separation only, not general assistance quality.

New reports use `report_version: "alpha-benchmark-v2"` and
`benchmark_validation_passed`, scoped to this frozen command corpus, cold sample
and deterministic calibration. `latency_requirement_ms` is `null`.
`recommended_sampling_complete` records whether all three runs include at least
200 samples; small pilots may pass command validation without making a
representative quality claim. The process exits unsuccessfully for invalid
answers or measurement errors, never merely because valid responses are slow or
the pilot is small. The supervised request deadline remains a bounded-operation
and cancellation safeguard, not a percentile-based product latency requirement.
Historical evidence retains its original `alpha_latency_passed` field and must
not be reinterpreted as a current release decision.

### Historical measurements before the latency requirement was removed

Portable-release pilots (20 requests): baseline p50/p95 8098/8826 ms, 6 failures;
compact policy/command-only output 4200/4816 ms, 6 failures; explicit contract
hints with two threads 3156/3905 ms, 4 failures. These are exploratory results,
not acceptance certification. These runs predate the removal of the latency gate.

The full target-workstation run completed with the frozen corpus and verified v2
model, two threads, and 200 warm requests per run:

| Run | p50 | p95 | Unstageable responses |
| --- | ---: | ---: | ---: |
| 1 | 3102.6 ms | 3725.3 ms | 40/200 |
| 2 | 3124.0 ms | 3573.4 ms | 40/200 |
| 3 | 3118.5 ms | 3682.0 ms | 40/200 |

Cold completion: 3726.0 ms. Every run failed the then-current latency gate and
command correctness checks. The correctness failures remain relevant; the old
latency thresholds no longer apply.
Other local regression work overlapped some measurements; these are failed
engineering measurements, not an isolated release certification. The measured
release preceded the final diagnostic extensions and Unicode parser containment;
the ASCII corpus and inference settings were unchanged. Numeric evidence is in
[the aggregate report](evidence/alpha-latency-20260911.json). Fresh, representative
release-candidate quality evidence is still needed before daily dogfood;
three-by-200 timing reports are recommended for trustworthy comparisons, not a
mandatory performance threshold.

## Acceptance

Zero deterministic discrepancies and observed execution-boundary escapes; passing
boundary, property/fuzz and real-PTY suites; all final staging gates satisfied.
Assistance must be correct, complete enough to serve the request, and explain its
recommendations and limitations. Invalid, truncated and unverifiable responses
are failures, not fast successes. Correctness and representative assistance
quality remain release gates; latency is not. The benchmark validates its frozen
command cases, not all possible explanatory assistance or universal alpha
readiness. Removing the latency requirement does not waive unresolved quality,
stale-state, privacy or unintended-execution defects.

Dogfood measurement is memory-only with manual aggregate export. Never export
requests, commands, output, paths, content hashes or persistent session IDs.
V2/v3 remain regression suites; v4 is deferred until production stabilization and
deliberate sanitized contributions from real dogfood experience.
