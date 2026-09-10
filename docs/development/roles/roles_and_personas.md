# cAIman Terminal development responsibilities

These describe responsibilities, not a requirement to spawn agents or use
particular models. Work can be performed by one maintainer or a team.

| Role | Owns | Boundary |
| --- | --- | --- |
| Terminal engineer | `terminal/`: GTK/VTE, shell integration, settings and packaging | User input remains authoritative; model suggestions never submit Enter |
| Runtime/harness engineer | Prompt/context management, model adapters, validation and runtime tests | Keep model generation separate from execution and deterministic host decisions |
| Research engineer | `llm/`: scenarios, scoring, datasets, training and GGUF evaluation | Preserve held-out evaluation and model/artifact provenance |
| Platform maintainer | Host adapters and audited command-help profiles | Use installed evidence and fail explicitly for unsupported behavior |
| Reviewer | Regression coverage, portability boundaries and documentation | Report model-quality and integration limits separately from unit-test results |

Project scope and current limitations are tracked in the [documentation index](../../README.md).
Generated weights and checkpoints belong in `artifacts/`, not source commits.
