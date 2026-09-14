# September 2026 hardening

This supersedes older claims about passive staging, SSH detection, model loading
and benchmark certification. The app remains an engineering preview, not a
security sandbox or a production-administration tool.
The [alpha acceptance guide](14_Alpha_Conformance.md) contains the current
finding-to-test matrix and historical three-by-200 timing evidence. Latency is no
longer an alpha gate; model correctness and full assistance coverage remain open.
Commands are printable ASCII only: a property-test native Unicode
scanner crash is contained by preflight before native parsing.

## Shipping staging authority

`worker::process` produces the desktop's context-bound validation. Every command
crosses syntax, CLI, host risk/secret and explicit intent checks; a repaired
command crosses them again. Unknown/ambiguous requests can retain clearly
unverified explanatory advice. Passive requests
can explain, but cannot repair or stage. Automatic model repair is disabled.
An unverifiable response can offer one separate **Retry suggestion** action while
the original request snapshot is unchanged. A safety/secret rejection never
offers retry. The alpha policy allows bounded deterministic task-option correction.

The UI checks the tab and cancellation ticket, then request ID, authenticated
prompt generation, context generation, CWD, input, local
mode and prompt state at acceptance. Bash independently compares physical CWD
and the exact Readline buffer plus prompt generation before replacing it. A new
prompt with identical CWD/input still invalidates an old stage file. The stage writer rescans the
command. Only typed Snapshot/Stage keys cross the application PTY boundary;
neither contains Enter. The separate user Enter still executes the command.

Supported natural-language staging contracts are intentionally small:

- disk usage (`df -h` or `df -hT`), memory usage (`free -h`);
- list files (`ls` or `ls -la`), recursively (`ls -R` / `ls --recursive`);
- working directory (`pwd`), Git status (`git status`);
- Arch system update (`pacman -Syu`, with host-selected sudo when needed);
- read a named file in the current directory (`cat`/`less`, exact quoted operand).

The `alpha-v1.1` manifest adds audited mkdir/rmdir/rm/cp/mv literal forms. Ordinary
file operations can stage with warnings, including project-local deletion;
unsupported options and critical mutations remain separate checks. Copying from
a system path is distinguished from overwriting it in the audited two-operand
form. Model-generated explanations do not grant new command authority.

The versioned alpha CLI manifest limits which literals can be verified; installed
programs outside it cannot stage. An explicit literal authorizes only that exact command, operands and privileges;
every other gate still applies. Questions, negation and unsupported tasks cannot
authorize a generated command. Destructive commands outside alpha CLI coverage
cannot stage, even when the legacy risk-only API reports Elevated. Aliases, functions,
PATH, startup files and local executables remain trusted user configuration;
the host cannot guarantee their standard semantics.

## Findings and resolution

| Audit item | Change | Verification |
| --- | --- | --- |
| Generic intent / passive repairs | Typed fail-closed registry, immutable borrowed mode, final binding | adversarial, guidance and host tests |
| Secret-bearing candidates | Shared scan before repair, pending and stage write; no redact-and-stage | Rust adversarial and Python security tests |
| Prompt provenance | OS/shell only in system facts; bounded and labelled untrusted CWD, history, docs/output | hostile-context and context tests |
| Python versus shipping policy | Versioned worker traces and independent Python alpha profile; exact decisions | `llm/tools/conformance.py` |
| Path/wrapper bypass | Reject path-qualified/non-ASCII executables, expansion, interpreters/wrappers | corpus and generated wrapper tests |
| SSH heuristics | Pause for **all** running/unknown programs; only original local Bash prompt resumes | GTK wrapper/OSC tests; remote worker rejects before inference |
| Event log/forgery/replay | Private 0600 FIFO, random 256-bit nonce, strict sequence/UTF-8/size; no append log | partial-write, wrong-nonce and replay tests |
| Model integrity/hangs | Trusted digest before parser; sealed memfd; helper killed/reaped on cancel, pipe stall, crash/deadline | sealed-byte, subprocess, malformed GGUF and live tests |
| Benchmark hygiene | Existing suites labelled examined regression data; overlap audit and frozen candidate gate | dataset audit and replay/hash tests |
| Missing integration/fuzz/mutation | 5,120 seeded parser inputs, wrapper properties, Bash parse-only checks, four mutants, GTK/OSC CI | commands below |

The nonce prevents accidental cross-session or unauthenticated event injection,
**not malicious same-UID code**, which can read memory/files or alter the shell.
The helper provides crash/deadline isolation, not a privilege/filesystem sandbox.
Help probes use fixed routes, a clean environment, neutral CWD, two-second timeout,
process-group cleanup and 64 KiB output limit. Python live help is disabled;
research tools are fixture-only.

## Privacy and model integrity limits

Recognized token families, Basic/Bearer credentials, password options, URL
passwords and multiline private keys are withheld. Detection is heuristic, not
proof that arbitrary secrets are absent. Disable AI around sensitive data. The
terminal and Bash history retain normal shell behavior. Journals/conversation are
bounded in memory; events occupy bounded kernel storage. This does not prevent
swap/core-dump retention or the user's own logging.

The shipped v2 digest is
`fdb77f88b8282cbb0e65f8362b5c11e8ea8648f1730661fb5592e5b6a633fb61`.
Custom weights require `--model-sha256` or the digest setting, obtained from a
trusted source. Symlinks are resolved and opened bytes copied, hashed and sealed
before llama.cpp parses them. The sealed copy can consume roughly a model-file's
worth of extra RAM/swap during loading. Hashing/loading occur inside the
deadline-supervised helper. Each inference gets fresh KV state.

## Evaluation honesty

Python is not a staging authority. Its explicitly selected alpha profile now
independently compares complete deterministic candidate decisions with production
Rust, including contracts, CLI validation and corrections. The broader research
profile remains separate. The old 60-case manifest with 56 disagreements is
retired; exact alpha comparisons fail on any discrepancy without a record/bypass
mode. This finite corpus is not general equivalence or a safety proof. See the
[alpha contract and evidence](14_Alpha_Conformance.md).

All existing suites have been examined. Exact-request auditing finds v3 overlaps
for `gh-045`, `interaction-033`, and `interaction-043` against checked-in training
sets. Historical artifacts remain historical results, not unseen evaluations.
An untouched holdout cannot be created retroactively. Independently collect and
freeze one, then use `dataset_audit.py --candidate-dir PATH --expected-sha256 HASH`.
Exact disjointness alone does not establish semantic independence or absence
from base-model training.

New reports identify the implementation, corpus/template hashes and holdout
status. Replay requires exact prompt hashes, rejects missing records and reuse
as repair, and refuses sanitized raw artifacts. Pairwise comparison requires the
same model, scenarios, corpus, templates and raw replay artifact. Legacy unbound
artifacts intentionally fail closed. Staging no longer implies simulated execution:
only explicit execution fixtures enter subsequent history. Non-streaming live
TTFT is unmeasured (0 sentinel), not estimated from total latency.
The legacy one-record-per-turn format cannot replay an absent repair or a
different tool-augmented prompt; these now fail explicitly instead of being
silently substituted. Observed-output questions use quoted recorded evidence
when sufficient, avoiding model reconstruction of already available facts.

## Reproducible checks

From the root, with `pip install -e './llm[test]'` in `.venv`:

```sh
cargo fmt --all -- --check
cargo test --locked --no-default-features
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
.venv/bin/python -m pytest llm/tests
cargo build --locked
.venv/bin/python llm/tools/conformance.py
.venv/bin/python llm/tools/dataset_audit.py
.venv/bin/python llm/tools/mutation_check.py
GDK_BACKEND=x11 CAYMAN_TEST_X11_KEYS=1 cargo test --lib ui::tests::desktop_flow -- --ignored --nocapture
cargo test --test llm_harness default_model_harness -- --ignored --nocapture
```

Mutation runs edit temporary copies and must fail assertions, not compilation;
only four named guards are measured. CI runs GTK/PTY, disabled-AI and settings
tests separately under Xvfb. Live-model CI is manual on a trusted `caiman-model`
runner with `CAIMAN_TEST_MODEL` pointing to pinned v2 weights. It neither downloads
arbitrary models nor runs PR code there. Provisioning that runner and collecting
an independent holdout remain external release prerequisites. Local test success
is not a hosted CI run.

## Historical pre-alpha verification (2026-09-11)

Superseded counts: the current suite has 101 exact Rust/Python comparisons and
109 Python tests, with no disagreement baseline. See the alpha guide for current
property, PTY, fuzz, mutation and latency results. The earlier evidence follows.

Rust default-feature and headless regressions passed, as did formatting and
Clippy with warnings denied. Python: 106 tests passed. The 60-case production
corpus/conformance baseline passed; all four targeted mutants were caught.
GTK/Bash staging, unknown-wrapper pause, OSC/clipboard isolation, AI-disabled
and settings-window tests passed on X11. The pinned v2 harness passed recorded
output, real disk-usage inference and tokenizer-compaction checks; supervised
`--ask 'show disk usage'` returned validated `df -hT`. The Arch failed-update
follow-up regression passed without passive staging. No suggested command was
executed by the model; the PTY test executes only its explicit test sentinel after
the separate simulated user Enter.
