# User guide

> Scope: terminal application. Reviewed 2026-09-10 for the split workspace.
> Code is in `terminal/`; commands run from the repository root unless stated otherwise.
> Model research is documented in [llm/README.md](../../llm/README.md).

Start `./target/debug/caiman-terminal`. Bash and the assistant share a compact,
terminal-style split. The assistant shows only `Ready..` after the model loads.
Drag the divider to resize the panes. Drag tabs to reorder them.

- Ctrl+Shift+T: new tab (also the small + button).
- Ctrl+Shift+W: close the current tab.
- Shift+Left / Shift+Right or Ctrl+PageUp / Ctrl+PageDown: switch tabs.
- Ctrl+Shift+A: hide/show the assistant pane.
- Ctrl+Shift+C / Ctrl+Shift+V: terminal copy/paste.

The tab-bar menu contains pane visibility and AI enable/disable controls.
`--no-ai` starts without loading a model.

Type requests at the normal prompt and press Enter:

```text
@ find every log file larger than 500 MB
@ explain that error
@ what does this flag mean?
@ continue
```

Every submitted `@` message appears in that tab's AI pane. Your messages and the
assistant's replies remain visible as you type or receive automatic hints;
scroll the pane to review the conversation. This history lasts for the tab's lifetime.

Each AI request also includes a fresh, bounded snapshot of that tab's terminal
text, current input, working directory, and recent commands with output and exit
status. You can refer to "this output" or "that error" without copying it into
the AI pane. Context stays within the tab and is redacted before reaching the model.

Requests to read a README or Markdown/text file use matching regular filenames
in the current directory and an installed viewer (`less`, or `cat`). Missing or
ambiguous filenames prompt for clarification. Questions about terminal text editors
identify an installed editor and show its save/exit keys. These common requests
receive local guidance without model inference or package-manager suggestions.

A recommendation appears in the assistant pane and a muted suggestion strip below
the terminal. Read the command and any risk explanation. Press Tab
to place it in your Bash input; edit it if needed, then press Enter yourself.
Without a suggestion, Tab remains normal Bash completion. Typing another key
invalidates the old suggestion. Invalid commands are not staged.

Pause after typing a natural-language task, an unknown command, a package-manager
command, or any short/long flag to request passive help. Requests start after about
250 ms idle. Known host errors and common `find` input receive direct guidance;
other requests take additional time for local inference. `ai · thinking` indicates
work in progress. Commands without a help trigger stay quiet.

Failed commands and completed assistant suggestions automatically trigger a
follow-up using the command, output, exit status, and original intent. There is
no need to type `@ explain that error`. Ctrl-C and direct SSH do not trigger local
follow-ups. Invalid suggestions get one model repair using installed help; if
that also fails, the assistant shows the host's reason and offers no ghost.

Ghost suggestions use a fixed-height strip, not cursor-aligned inline rendering.
Tab still only stages a validated command; Enter executes it.

The assistant uses recent context from the current tab. `clear` does not erase
that context. A new tab starts fresh. Direct SSH pauses assistance while the
remote foreground session owns the terminal; use normal SSH commands there.

Suggestions do not provide automatic undo. There is no cloud fallback, automatic
model download, or arbitrary model tool execution. Missing AI does not stop Bash.
This preview does not implement automatic file-content reading or full remote
assistant integration. See the backlog before relying on it for daily workflows.

Pausing after bare `find` now offers `find . -type f` with filename-search tips.
Pausing after `find . -name` or `find . -size` explains the missing operand without
inventing a filename or size. Unquoted filename patterns can receive a quoted
replacement. On CachyOS, failed apt updates get a direct pacman explanation and
a validated `sudo pacman -Syu` suggestion (without sudo when already root).

Type `ps -` to see installed options and their meanings, or narrow the list with
`ps -f` or `ps --so`. The same flag-help trigger applies to other commands;
installed help or man pages supply the descriptions. When documentation is
unavailable, the assistant says so. Flag lists never pick or execute an option
for you. Previous-command advice clears when you start editing.

## Icon, themes, and manual

After local installation, launch `caiman-terminal` from any directory or choose
cAIman Terminal in the desktop app menu. The original caiman icon is drawn with literal monospaced ASCII characters in
terminal green on a dark background, focused on the eyes and upper snout;
`--help` includes the same eyes-only ASCII caiman.

Open the tab-bar menu and choose Theme. Five bundled terminal styles are Dracula,
Nord, Gruvbox Dark, Catppuccin Mocha, and Tokyo Night, alongside the original
cAIman default. The entire window and all its tabs update immediately. The choice
is saved to `$XDG_CONFIG_HOME/cayman-terminal/settings.json`, normally
`~/.config/cayman-terminal/settings.json`. Existing other windows retain their
current colors; newly launched windows read the saved preference.

`caiman-terminal --theme nord` overrides the saved preference for one window.
`caiman-terminal --list-themes` lists IDs. Read `man caiman-terminal` for options,
shortcuts, configuration paths, examples, and known limits. The source manual can
also be viewed with `man -l terminal/resources/man/caiman-terminal.1`.

## Settings

Open the tab-bar menu → Settings, or press Ctrl+,.

- Appearance: theme, terminal/assistant font size and scrollback.
- Assistant: AI enabled at startup, pane visibility and assistance delay.
- Model & runtime: local GGUF file chooser, registered model backend, CPU threads,
  context tokens, maximum response tokens and timeout. Leave the model path empty
  to use the application default, currently Qwen SFT v2.
- Terminal & host: registered terminal/shell providers, detected operating system,
  host adapter and command-help behavior. OS detection is automatic; choosing a
  different OS to bypass host validation is not supported.

Save applies the theme and disabling AI immediately. Disabling AI hides its pane
in all tabs; `--no-ai` also starts with the pane hidden. Relaunch cAIman for other settings. Invalid
values are shown in the window and do not replace the saved configuration.
`--model` overrides the saved model for that launch. The installed launcher provides
an absolute fallback model path, so saved model choices work from any directory.
Settings are stored in `~/.config/cayman-terminal/settings.json` (or XDG_CONFIG_HOME).
