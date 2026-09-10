#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"
cargo fmt --all -- --check
cargo clippy --locked --all-targets -- -D warnings
cargo test --locked --no-default-features
cargo test --locked
cd "$repo_dir/llm"
"${CAIMAN_PYTHON:-$repo_dir/.venv/bin/python}" -m pytest tests
