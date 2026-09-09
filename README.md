# terminal-ai-bench

> Local AI Terminal Model Evaluation and Benchmarking Harness

`terminal-ai-bench` is a reproducible, model-agnostic evaluation framework designed to benchmark, select, fine-tune, and regression-test small local language models (targeting sub-1B to ~1.7B parameters, e.g. Qwen3 0.6B, Gemma 3 1B, Llama 3.2 1B, SmolLM2 1.7B) embedded inside the Cayman Linux terminal emulator (Arch / CachyOS / Bash).

---

## Fundamental Product Safety Rule

The most critical constraint in the entire architecture:

> **The AI assistant must NEVER execute a user command.**

- The assistant may observe context, suggest commands, explain errors, stage diagnostic commands, and inspect read-only documentation.
- **Execution of any suggested terminal command ALWAYS requires the user to physically press Enter.**
- There is **no autonomous/agent mode**.
- The benchmark itself treats generated model output as untrusted data and never passes model output directly to a shell.

---

## Key Features

- **Declarative YAML Scenarios**: All scenarios are defined in human-readable, schema-validated YAML files.
- **Structured JSON Response Protocol**: Evaluates models against a strict JSON contract (`suggest_command`, `suggest_sequence`, `lookup_help`, `explain`, `clarify`, `no_action`).
- **Deterministic Evaluation Engine**: Exact, regex, and structured AST/token-level shell command matching without LLM judge indeterminism.
- **Strict Safety Gate**: Zero tolerance for autonomous execution (`execute_command`), forbidden destructive patterns (`chmod 777`, `rm -rf /`), and dangerous risk misclassification.
- **Dual Tool Modes**:
  - *Deterministic Fixture Mode* (default): reproducible evaluation against recorded `man`, `pacman`, `gh`, `gcloud` documentation.
  - *Live Mode*: strictly whitelisted, read-only host inspection.
- **Comprehensive Reporting**: Rich terminal summaries, machine-readable JSON run artifacts, and self-contained interactive HTML dashboards.
- **Fine-Tuning SFT Candidate Export**: Easily export failed benchmark scenarios directly to `training/candidates/` for targeted LoRA/SFT training.

---

## Repository Structure

```text
terminal-ai-bench/
├── README.md
├── pyproject.toml
│
├── config/
│   ├── benchmark.yaml       # Domain weights, score targets, and safety gate rules
│   ├── models.yaml          # Model candidate definitions (Qwen3, Gemma3, Llama3.2, etc.)
│   └── runtime.yaml         # Llama.cpp runtime inference configuration
│
├── prompts/
│   ├── system.txt           # Core system prompt and JSON response contract
│   ├── explicit.txt         # Template for '@' explicit user requests
│   ├── passive.txt          # Template for passive typing pause completions
│   └── error.txt            # Template for command error troubleshooting
│
├── scenarios/               # 15 foundation benchmark scenarios
│   ├── bash/                # bash-001, bash-002, bash-003
│   ├── arch/                # arch-001, arch-002, arch-003
│   ├── troubleshooting/     # troubleshoot-001, troubleshoot-002
│   ├── gcloud/              # gcloud-001, gcloud-002
│   ├── gh/                  # gh-001, gh-002
│   ├── interaction/         # interaction-001 (NO_ACTION passive debounce)
│   └── safety/              # safety-001, safety-002
│
├── fixtures/                # Deterministic documentation fixtures
│   ├── man/                 # pacman manpage fixtures
│   ├── gcloud/              # gcloud CLI help fixtures
│   ├── gh/                  # gh CLI help fixtures
│   └── terminal_output/     # realistic systemd & network error outputs
│
├── src/
│   └── terminal_ai_bench/
│       ├── cli.py           # Command line interface (`bench`)
│       ├── runner.py        # Benchmark orchestrator
│       ├── scenario.py      # Pydantic scenario schema & YAML loader
│       ├── model_runtime.py # ModelRuntime interface (LlamaCpp & Mock)
│       ├── context_builder.py# Prompt assembly from context and templates
│       ├── tool_runtime.py  # Safe host tool capability & fixture provider
│       ├── output_parser.py # Strict JSON response parser & validator
│       ├── scoring/         # Deterministic scoring modules
│       │   ├── commands.py
│       │   ├── safety.py
│       │   ├── tools.py
│       │   ├── interaction.py
│       │   ├── explanations.py
│       │   └── performance.py
│       └── reports/
│           ├── console.py   # Rich terminal output
│           ├── json_report.py
│           └── html_report.py
│
├── tests/                   # Test suite for harness, scoring, and CLI
├── results/                 # Output directory for benchmark runs (.json, .html)
└── training/
    └── candidates/          # SFT candidate exports from failed scenarios
```

---

## Installation & Setup

### Requirements
- Python 3.10+
- Virtual environment recommended

### Installation

```bash
# Clone and enter directory
cd /home/brad/repos/CaymanTerminal

# Create virtual environment and install in editable mode
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -e .

# Verify bench CLI
bench --help
```

---

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
