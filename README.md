# cAIman Terminal

A local AI-assisted terminal and the research tools used to tune and evaluate its
models. These are related projects with separate build and test workflows.

This application has been built using LLMs (Codex, Claude, Gemini).

| Area | Purpose | Start here |
| --- | --- | --- |
| [`terminal/`](terminal/) | Rust desktop app, runtime LLM harness, settings and packaging | [App guide](terminal/README.md) |
| [`llm/`](llm/) | Python benchmarks, host-system evaluation, SFT training and versioned datasets | [Research guide](llm/README.md) |
| [`artifacts/`](artifacts/) | Local GGUF models, training checkpoints and generated reports; not committed | [Artifact layout](artifacts/README.md) |
| [`docs/`](docs/) | Product requirements, architecture, status and development guidance | [Documentation index](docs/README.md) |

## Terminal app

Run from the repository root:

```sh
cargo build --locked --features desktop,inference
./target/debug/caiman-terminal --no-ai
python3 terminal/packaging/install.py
```

With the local v2 GGUF under `artifacts/models/`, launch `caiman-terminal` for AI
assistance. Open **Settings** from the menu or press **Ctrl+,**. The launch command is `caiman-terminal`. The installer also supplies a
`cayman-terminal` forwarding alias for existing scripts. The desktop ID and
settings directory remain stable so pinned launchers and preferences keep working.

## Model research

Create a virtual environment at the root, then run research commands from `llm/`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e './llm[test]'
cd llm
../.venv/bin/bench validate
../.venv/bin/bench run mock
../.venv/bin/python -m pytest tests
```

The Python package remains `terminal-ai-bench`; `bench` evaluates models and the
host pipeline. It is not the desktop executable. Optional local inference and
training dependencies are documented in the research guide.

## Current status

Alpha has no latency release threshold; correctness, useful coverage and
explainability remain acceptance concerns. The
[alpha-v1.1 acceptance guide](docs/terminal/14_Alpha_Conformance.md) records exact
conformance and executable boundary gates. The
[performance review](docs/terminal/15_Performance_Correctness_Review.md) separates
deterministic command route from model generation; its historical latency limits
are superseded. Suggestions now render inline, model suggestions include an
explanation, and [optional GPU offload](docs/terminal/16_GPU_Acceleration.md) is
available in compatible builds when enabled.

Engineering preview: Linux, GTK/VTE, Bash, local llama.cpp and Qwen SFT v2 by
default. The app supports tabs, terminal-aware assistance, validated command
staging, themes and centralized settings. Provider interfaces establish extension
points; other operating systems, terminal implementations and model backends are
not implemented yet. Every suggested command still requires the user's Enter key.

See the [security hardening and verification guide](docs/terminal/13_Security_Hardening.md)
for the current staging contract, trust boundaries and benchmark limitations.

Model quality is an active research concern. Raw model scores, host rejection,
and a correct end-to-end answer are separate outcomes; passing unit tests is not
proof of model correctness. See [status](docs/terminal/12_Project_Status.md) and
[known limitations](docs/terminal/11_Open_Issues_Risks_and_Backlog.md).

Repository: [bradltl/cAImanTerminal](https://github.com/bradltl/cAImanTerminal).
