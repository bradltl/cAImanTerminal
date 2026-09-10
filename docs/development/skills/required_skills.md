# cAIman Terminal maintenance competencies

Current scope: two related projects, Rust desktop/runtime work and Python local-LLM
research. Web frameworks, game engines, embedded hardware and cloud services are
not dependencies of this workspace.

- **Rust desktop/systems work:** GTK4, VTE, Bash/Readline, PTYs, ownership,
  concurrency, process lifecycle and Unix permissions.
- **Local inference:** llama.cpp, GGUF chat templates/tokenizers, token budgets,
  cancellation, grammar-constrained responses and bounded context.
- **Model research:** Python, PyTorch, Transformers, TRL, PEFT, datasets,
  quantization/export, throughput measurement and held-out evaluation.
- **Validation:** Bash AST analysis, installed CLI help, deterministic risk gates,
  adversarial fixtures, raw-versus-host-system scoring and explicit user execution.
- **Maintenance:** versioned configuration, adapter contracts, reproducible builds,
  Git history, CI, documentation and artifact provenance.

Use [scripts/check.sh](../../../scripts/check.sh) for the workspace's deterministic
checks. Graphical and live-model tests are separate opt-in checks described in the
[terminal harness guide](../../../terminal/tests/README.md). No Jest/Node pipeline
is used here. Do not treat a model safety rejection as proof of a useful answer.
