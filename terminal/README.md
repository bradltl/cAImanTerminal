# cAIman Terminal — desktop app

Rust + GTK4/VTE + Bash + embedded CPU llama.cpp. The assistant can explain and
stage commands; only the user presses Enter. This is an engineering preview.

All commands below run from the **repository root**, not `terminal/`.

## Build and launch

On Arch/CachyOS, install Rust, clang, CMake, pkgconf, GTK4, vte4 and librsvg.
GTK4 VTE 0.76 or newer is required. Then:

```sh
cargo build --locked --features desktop,inference
./target/debug/caiman-terminal
./target/debug/caiman-terminal --no-ai
./target/debug/caiman-terminal --model /absolute/path/to/model.gguf
```

The default is `artifacts/models/qwen2.5-0.5b-instruct-sft-v2.gguf`. Weights are
local artifacts and are not committed or downloaded at runtime. Missing model
weights leave the terminal usable. `--ask` uses the final runtime validation
pipeline and never executes a suggested command.

## Install and settings

```sh
python3 terminal/packaging/install.py
caiman-terminal
man caiman-terminal
```

The installer copies the debug desktop build, icon, desktop entry and manual to
`~/.local`. Rebuild and reinstall after source changes. This independent copy
prevents a headless test build from breaking the installed launcher.

Open **Menu → Settings** or press **Ctrl+,** for themes, font/scrollback, assistant
behavior, local model/runtime options and host information. Theme changes and disabling AI apply on Save;
other settings apply on relaunch. Disabling AI hides its pane in every tab,
including new tabs and windows launched with `--no-ai`. Model precedence is `--model`, saved choice,
installed launcher fallback, then the source default. The executable is `caiman-terminal`; the installer supplies a legacy
`cayman-terminal` forwarding alias. Desktop identity and the existing
`cayman-terminal` settings directory stay stable, preserving pins and preferences.

## Verify

```sh
cargo fmt --all -- --check
cargo test --locked --no-default-features
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
# Requires a graphical session; run each GTK test separately:
cargo test --locked --lib ui::tests::desktop_flow -- --ignored --nocapture
cargo test --locked --lib settings_ui::tests::settings_window -- --ignored --nocapture
```

See the [runtime harness guide](tests/README.md) for live-model testing and context
policies. Raw-model training and benchmarking belong to [`llm/`](../llm/README.md).
For static safety replay: `./target/debug/caiman-terminal --audit-report artifacts/results/RUN.json`.
That replay is narrower than full end-to-end evaluation.

## Documentation

[Product overview](../docs/terminal/01_Project_Overview.md) ·
[Requirements](../docs/terminal/02_Product_PRD.md) ·
[Architecture](../docs/terminal/03_Architecture_Overview.md) ·
[User guide](../docs/terminal/10_User_and_Admin_Guides.md) ·
[Status](../docs/terminal/12_Project_Status.md) ·
[Theme credits](resources/themes/README.md)
