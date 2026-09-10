# Local artifacts

These directories are shared by the two source projects and ignored by Git:

- `models/`: GGUF files. The app default is `qwen2.5-0.5b-instruct-sft-v2.gguf`.
- `checkpoints/`: training checkpoints, adapters and merged weights.
- `results/`: generated JSON/HTML evaluation reports.

The folder reorganization moved existing local files here without regenerating or
deleting them. A fresh clone does not include weights, checkpoints or past reports.
Research model IDs, hashes and available download URLs are in
[`llm/config/models.yaml`](../llm/config/models.yaml). From `llm/`, `bench pull`
can download models with a configured URL. Locally tuned SFT models without a
published URL must be copied here or produced by the training pipeline. The app
never downloads a model at runtime.

Research paths use `../artifacts/...` from `llm/`; app paths use `artifacts/...`
from the repository root. The installed launcher stores an absolute fallback path.
