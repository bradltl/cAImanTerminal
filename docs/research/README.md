# LLM research scope

Current as of 2026-09-10. Source and commands are in [`llm/`](../../llm/README.md).
The research project supports the terminal product but has a separate runtime,
dependency set, test suite and development cycle.

| Activity | Implementation | Interpretation |
| --- | --- | --- |
| Raw model evaluation | `bench run`, model runtime, scenarios and scoring | Measures model output before app guardrails |
| Host-system evaluation | `bench run --system`, Python `terminal_ai_bench/system/` | Evaluates that host pipeline; do not assume exact parity with the Rust desktop runtime |
| SFT work | `llm/training/`, versioned `training_dataset*` | Generates datasets, trains adapters/merged weights and exports GGUF |
| Desktop runtime regression | `terminal/tests/`, `--ask`, `--audit-report` | Tests the Rust runtime; static audit is narrower than live documentation/repair evaluation |

V2 is the current application default by user preference. V3–V5 datasets and model
registry entries remain research assets; no historical scores or hashes were
regenerated during the directory cleanup. The v5 live terminal-reference failure
is retained in the runtime harness documentation as a known model-quality finding.

Generated weights/checkpoints/reports live in `artifacts/` and are not pushed.
Scenario YAML, recorded help fixtures, training scripts and versioned datasets
remain source-controlled. Use separate held-out scenarios when assessing a tuned
model; a safety rejection and a correct useful answer are separate measures.

See the [archived initial brief](archive/harness-design.md) for design history.
Its future-tense app discussion is historical, not current implementation status.
