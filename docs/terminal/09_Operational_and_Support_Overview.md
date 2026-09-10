# Operations and support

> Scope: terminal application. Reviewed 2026-09-10 for the split workspace.
> Code is in `terminal/`; commands run from the repository root unless stated otherwise.
> Model research is documented in [llm/README.md](../../llm/README.md).

Build dependencies: Rust, C/C++ compiler, clang/libclang, CMake, pkg-config, GTK4,
and GTK4 VTE 0.76 or newer. Cargo downloads dependencies only during explicit build
setup. No application port/service is required.

Run from repository root or pass `--model` with an absolute GGUF path. Model
weights are separate from the executable. Missing model/runtime errors are
reported in the UI; `--no-ai` skips loading. No terminal content is logged to a
telemetry service. Headless `--ask` intentionally prints its result for local use. `--audit-report`
replays saved raw candidates through static host validation without inference.

CI runs deterministic Rust tests, the desktop build/tests, formatting, linting,
and existing Python tests. Graphical integration is a separate display-dependent
check. Model weights are not downloaded by CI.

Troubleshooting:

- `vte-2.91-gtk4` missing: install `vte4`, not just GTK3's `vte3`.
- CachyOS package signature 404: use signed standard Arch packages or repair the
  mirror configuration; do not disable verification.
- No display: use core tests/headless `--ask`; desktop tests require GTK display.
- AI unavailable: check the model path and start the program from the repo root.
- Custom Bash prompt/bindings conflict: compare against the integration script;
  first iteration supports Emacs Readline mode only.

System distribution packages, crash cleanup of temporary IPC files, and production
logging policy are deferred. A per-user launcher/icon/man-page installer is available. Removing the built binary
and Cargo `target` directory rolls back the app without modifying the user's
`.bashrc`; integration applies only to cAIman-launched shells.

## Local desktop installation

Build a desktop executable, then install the prepared assets:

```bash
cargo build --offline --features desktop,inference
python3 terminal/packaging/install.py
```

The default prefix is `~/.local`. The installer places an executable under
`lib/cayman-terminal`, a shell launcher under `bin`, a freedesktop application
entry, a scalable icon, the section-1 man page, and theme license notices under
`share`. It never copies or downloads model weights. The launcher passes the
existing repository GGUF as an absolute path; supply `--model /path/to/file.gguf`
to the installer to select another default. Saved model preferences override the launcher fallback; explicit CLI model options override both.

Re-run the build and installer after code changes to update the installed copy.
Core-only Cargo tests can replace the development binary but cannot replace the
installed desktop executable. `glib-compile-resources` (from GLib development
tools) is required when building embedded desktop icon resources.

For a staged package inspection, pass `--prefix /tmp/cayman-install-preview`.
`desktop-file-validate packaging/io.cayman.Terminal.desktop` and
`man -l terminal/resources/man/cayman-terminal.1` verify the launcher metadata/manual.

The default model is SFT v2, specified in `terminal/resources/default-model.txt` for both
CLI and installer. `--model` overrides it. Runtime context/validation checks and
live-model regression commands are documented in `terminal/tests/README.md`; the live
harness records semantic failures separately from successful context budgeting.
