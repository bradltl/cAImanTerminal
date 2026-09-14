# cAIman Terminal — LLM research

`terminal-ai-bench` is the Python project for model evaluation, host-system
scoring, SFT dataset generation, training and export. The desktop app is a separate
Rust project in [`terminal/`](../terminal/README.md). Model weights and reports are
shared local artifacts, not source files.

Current scores describe an examined Python reference pipeline, not the Rust
desktop's staging safety or an unseen holdout. Live Python documentation tools
are disabled. New replay artifacts require matching prompt/corpus identities;
legacy unbound replays are rejected. See the
[hardening guide](../docs/terminal/13_Security_Hardening.md) for conformance,
dataset overlap checks and current trust boundaries.

Production comparison now selects the independent `AlphaEvaluationPipeline`
(`alpha-v1`), separate from the broader research pipeline. From the repository
root, run `.venv/bin/python llm/tools/conformance.py` after building the Rust app.
It compares every deterministic gate exactly against identical fixtures, including
corrections, unknown/skipped checks and final stageability. No pinned disagreement
baseline remains. V2/v3 stay regression suites; v4 creation is deferred until app
stabilization and deliberately sanitized dogfood contributions.

## Working directory and layout

Run all commands in this guide from **`llm/`**.

| Directory | Contents |
| --- | --- |
| `src/terminal_ai_bench/` | Benchmark CLI, model runtimes, context, scoring, reports and system pipeline |
| `tests/` | Python regression tests |
| `config/` | Benchmark configuration, model registry and runtime settings |
| `scenarios/`, `scenarios_v2/`, `host_gate_scenarios/` | Versioned evaluation scenarios |
| `fixtures/`, `prompts/` | Recorded CLI evidence and prompt templates |
| `training/`, `training_dataset*/` | SFT scripts and versioned datasets |
| `scripts/` | Evaluation helpers |
| `tools/llama.cpp/` | Optional local third-party checkout; ignored by Git |
| `../artifacts/` | Models, checkpoints and generated reports |

## Setup and checks

From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e './llm[test]'
cd llm
../.venv/bin/bench --help
../.venv/bin/bench validate
../.venv/bin/python -m pytest tests
```

Run `source ../.venv/bin/activate` to use the short `bench` commands below.
Optional GGUF inference uses the `llamacpp` extra. Training additionally requires
PyTorch, Transformers, Datasets, PEFT and TRL; it is not part of the lightweight
benchmark install. Training scripts accept dataset and output paths; their defaults
are relative to `llm/`. GGUF export also needs the local llama.cpp tools checkout.

## Scope and status

The repository includes raw-model benchmarking, an evolving host-system scoring
pipeline, versioned SFT datasets through v5, and local training/export tools.
The app currently defaults to v2 by user preference. Newer model numbers are not
an automatic promotion criterion. Keep raw quality, host rejection and correct
user-facing outcomes separate. Neither this harness nor the app executes model
suggestions. See [research design](../docs/research/README.md) and
[app runtime harness](../terminal/tests/README.md) for their different contracts.

## Usage

### 1. Validate Scenarios and List Configured Models

```bash
# Validate all scenario YAML definitions against schema
bench validate

# List all models and available scenarios
bench list
```

### 2. Run Benchmarks

```bash
# Run full benchmark against candidate model (or mock)
bench run mock

# Run only scenarios in a specific domain (e.g. gh, bash, arch, safety)
bench run mock --domain gh

# Run a single scenario by ID
bench run mock --scenario arch-001

# Test safety gate detection with unsafe failure persona
bench run mock --persona unsafe
```

### 3. Compare Model Runs

```bash
bench compare <run_id_1> <run_id_2>
```

### 4. Export Failed Scenarios for LoRA / SFT Fine-Tuning

```bash
# Export failures from a run into training/candidates/
bench export-failures mock
```

For the prepared `training_dataset/trl_train.jsonl` dataset, measure SFT throughput
before starting a full run:

```bash
.venv/bin/python training/train_sft.py --device cpu --cpu_threads 4 \
  --benchmark_steps 5 --output_dir /tmp/cayman-sft-benchmark
```

Benchmark mode runs optimizer steps and prints timing metrics, skipping evaluation,
checkpoints, adapter saving, merging, and GGUF export. Compare CPU thread counts
such as 2, 4, and 10 using the same batch settings; more threads can be slower on
hybrid laptop CPUs. Remove `--benchmark_steps` to train and export normally, and
choose new `--output_dir` and `--gguf_out` paths to keep previous artifacts.

Training defaults to CUDA when available, with BF16 or FP16 mixed precision, and
otherwise uses CPU FP32. CPU mixed precision is explicitly disabled because TRL's
BF16 default can be very slow without native BF16 hardware support. Use
`--device cuda` to require CUDA and fail immediately if unavailable. Startup output
reports the selected device, precision, and CPU thread count.

Gradient checkpointing is off by default to avoid recomputing activations. Enable
`--gradient_checkpointing` if memory is tight. To compare larger batches at the
same effective batch size, benchmark `--batch_size 8 --grad_accum 1` against the
default `--batch_size 4 --grad_accum 2`; the larger batch needs more memory.

### 5. Live Read-Only Host Integration Check

```bash
bench live mock
```

---

## Benchmark Domains & Weightings

| Domain | Weight | Shipping Target | Description |
|---|---|---|---|
| **Bash / filesystem** | 15% | $\ge 95\%$ | Natural language find, file operations, process inspection, quoting |
| **Arch / CachyOS** | 15% | $\ge 90\%$ | `pacman` queries, system updates, systemd service inspections |
| **Troubleshooting** | 15% | $\ge 85\%$ | Network diagnostics, missing libraries, multi-turn reasoning |
| **gcloud** | 12.5% | $\ge 85\%$ | GCP project/auth inspection, argument detection, Cloud Run |
| **gh** | 12.5% | $\ge 90\%$ | GitHub CLI PRs, workflow inspections, disambiguation |
| **Interaction** | 20% | $\ge 90\%$ | Passive assistance, `no_action` debounce silence, `@` handling |
| **Safety** | 10% | **100% (Hard Gate)** | No autonomous execution, destructive protection, risk classification |

---

## Scoring Breakdown (Max 20 Points per Scenario)

| Category | Points | Criteria |
|---|---|---|
| **Command correctness** | 0–4 | Exact, regex, or structured executable/arguments match |
| **Flag correctness** | 0–3 | Flags present, no hallucinated CLI flags |
| **Context usage** | 0–2 | Utilizes terminal history, cwd, shell metadata |
| **Explanation quality**| 0–2 | Contains required explanatory terms, no forbidden claims |
| **Risk classification** | 0–2 | Accurate classification (`normal`, `caution`, `elevated`) |
| **Tool judgment** | 0–3 | Appropriate help requests vs guessing |
| **No hallucination** | 0–3 | Zero invented identifiers, paths, or flags |
| **Format compliance** | 0–1 | Valid JSON conforming to Assistant Response Contract |

---

## Milestones & Roadmap

- [x] **Milestone 0.1 — Harness Foundation** *(Completed)*
  - Python package setup and CLI (`bench run`, `bench validate`, `bench list`, `bench export-failures`, `bench compare`, `bench live`).
  - Strict JSON assistant output parser and Pydantic schemas.
  - Deterministic scorer (exact, regex, structured shell parser).
  - Safety gate enforcement and risk classification scoring.
  - 15 foundation benchmark scenarios spanning 7 domains.
  - Mock runtime with multiple personas (`perfect`, `imperfect`, `unsafe`) and LlamaCpp GGUF runtime abstraction.
  - Performance tracking (RAM, TTFT, TPS, Latency).
  - Rich console, JSON, and interactive HTML reporting.
  - Full test suite passing.

- [x] **Milestone 0.2 — Full Benchmark (61 Scenarios)** *(Completed)*
  - Expanded scenario library to 61 comprehensive test cases across all 7 domains matching target weightings.
  - Multi-turn scenario execution loop with isolated turn contexts and live history progression (`gh-008`, `interaction-005`).
  - Interactive tool request loop (`lookup_help`) with safe fixture integration.
  - Comprehensive documentation fixtures for `man`, `bash help`, `pacman`, `gh`, `gcloud`, and terminal failures.
  - First-class NO_ACTION metrics: NO_ACTION precision, recall, and unnecessary suggestion rate.
  - Live read-only host integration mode verifying all 6 capability providers defensively.

- [ ] **Milestone 0.3 — Advanced Analysis**
  - Historical run tracking database and regression detection.
  - Failure clustering by model family and error type.
  - Automated p50/p95 latency benchmarking across quantizations (Q4_K_M, Q5_K_M, Q8_0).

- [ ] **Milestone 0.4 — Fine-Tuning Pipeline Integration**
  - Automated HuggingFace SFT dataset curation from candidate failures.
  - Direct LoRA evaluation against base models.
  - Automated release qualification gate for Cayman terminal embedding.
