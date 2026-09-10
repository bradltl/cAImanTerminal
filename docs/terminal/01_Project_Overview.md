# cAIman Terminal — Project Overview

> Scope: terminal application. Reviewed 2026-09-10 for the split workspace.
> Code is in `terminal/`; commands run from the repository root unless stated otherwise.
> Model research is documented in [llm/README.md](../../llm/README.md).

**Status:** Active development / architecture validated through model benchmarking and fine-tuning
**Initial platform:** Arch Linux and Arch-derived distributions, with CachyOS as a primary development target
**Initial shell:** Bash
**Current implementation:** Rust + GTK4 + VTE4 + embedded llama.cpp
**AI operating model:** Fully local, assistant-only, never autonomous

---

## 1. Executive Summary

cAIman Terminal is a Linux terminal emulator that combines a real Bash terminal with a small, fully local AI assistant. The assistant is aware of the current shell session and helps users construct commands, understand flags, interpret errors, troubleshoot failures, and navigate complex CLI tools without handing execution control to the model.

The product is intentionally **assistive rather than agentic**. The AI may observe terminal context, reason about it, explain what happened, and stage a command for the user, but it may **never execute a user command**. Every command requires the user to press Enter.

The application is designed around a second principle that has been reinforced through benchmark and fine-tuning work:

> **Deterministic software should do everything that does not require intelligence.**

The host application therefore owns shell state, passive-interaction gating, command validation, safety/risk classification, documentation eligibility, and other deterministic behavior. The embedded model focuses on the work that benefits from learned reasoning: interpreting user intent, composing commands, explaining failures, deciding when clarification is needed, and using session context across multiple turns.

This division of responsibility allows the application to use an unusually small local language model while still providing useful terminal assistance with low memory usage and low latency.

---

## 2. Problem Statement

Linux terminals are powerful but require users to remember a large and fragmented command vocabulary across:

- Bash and core utilities
- distribution-specific package managers
- systemd and journald
- networking utilities
- Git and GitHub CLI
- cloud CLIs such as `gcloud`
- developer tools such as Docker and Kubernetes
- application-specific command-line tools

Current AI assistants can help with these tasks, but most introduce one or more undesirable tradeoffs:

1. They require copying terminal output into a separate chat application.
2. They depend on cloud inference and may expose local system context externally.
3. They lack structured awareness of the active shell session.
4. They behave as autonomous agents and may execute commands themselves.
5. They rely on large models with substantial memory and compute requirements.
6. They hallucinate version-sensitive flags or commands that the local tool does not support.
7. They interrupt too frequently when embedded into interactive workflows.

cAIman Terminal is intended to solve these problems by putting a small, private, context-aware assistant directly beside the shell while preserving normal terminal behavior and explicit user control.

---

## 3. Product Vision

The long-term product should feel like a normal Linux terminal that happens to have an expert assistant sitting beside it.

The terminal remains fully usable when AI is disabled. When AI is enabled, it can understand what the user is typing, what recently happened in the session, and what system the user is working on. It should intervene only when useful.

A successful experience should feel closer to:

> **Bash + excellent shell completion + contextual documentation + an experienced Linux colleague**

than to a general-purpose chatbot or autonomous coding agent.

---

## 4. Product Principles

### 4.1 User execution is absolute

The AI must never press Enter, execute a user command, or enter an autonomous execution loop.

It may:

- recommend a command;
- stage a command in the terminal input area;
- explain a command;
- explain prior output;
- present a multi-step plan;
- suggest the next diagnostic step;
- use approved host-provided read-only documentation/system metadata.

The user must physically press Enter for every user command.

### 4.2 The terminal must remain a real terminal

The terminal pane is not a simulated command console. It is backed by a real PTY and Bash session and must support ordinary terminal applications and workflows.

### 4.3 Local-first and private

The core product must operate without cloud inference or a network connection once installed.

There is no silent telemetry, cloud fallback, or automatic upload of terminal content.

### 4.4 Deterministic before probabilistic

The host application should handle deterministic tasks directly, including:

- shell/session boundaries;
- working directory tracking;
- command-existence checks;
- standard shell completion;
- passive invocation eligibility;
- command parsing;
- risk classification;
- safety validation;
- local documentation lookup;
- package metadata lookup;
- secret filtering;
- terminal tab isolation.

The model should not spend capacity learning rules that the application can enforce reliably in code.

### 4.5 Trustworthiness over confidence

When the model lacks required information, the correct behavior is to clarify, inspect approved local documentation, or recommend a diagnostic step rather than invent a value or flag.

### 4.6 Sparse assistance

The assistant should observe broadly but speak sparingly. Ordinary valid terminal use should not produce constant commentary.

---

## 5. User Experience Overview

### 5.1 Layout

The primary application layout consists of:

- **Terminal pane** — the main workspace and input surface.
- **AI assistant pane** — a collapsible right-side pane for explanations, plans, warnings, and context.
- **Tab bar** — multiple isolated terminal sessions.
- **Status area** — local/remote state, AI state, model state, and other lightweight indicators.

The AI pane is primarily a display surface. The user interacts with the assistant through the terminal input line rather than a separate chat box.

### 5.2 Explicit AI interaction

An input beginning with `@` is intercepted by the application before Bash receives it.

Examples:

```text
@ update my system
@ explain that error
@ what does -Rns do?
@ why did that fail?
@ make that recursive
@ use rsync instead
@ what's next?
@ continue
```

The assistant may respond with an explanation, a clarification question, or a staged command.

### 5.3 Passive assistance

The application may offer ghost-text assistance while the user types, but only after a short idle period and only when the deterministic eligibility gate determines that AI assistance is likely to be helpful.

Potential triggers include:

- natural-language text entered at the Bash prompt;
- an obvious command typo;
- invalid command syntax;
- a failed previous command with a likely correction;
- an incomplete but high-confidence command pattern.

Ordinary valid input should produce no AI interruption.

### 5.4 Tab acceptance

`Tab` uses this precedence:

> **If AI ghost text is visible, Tab accepts the AI suggestion. Otherwise, Tab behaves as normal Bash completion.**

Accepting a suggestion places text into the terminal input buffer. It does not execute it.

### 5.5 Multi-step troubleshooting

For multi-step work, the assistant may present the overall plan in the AI pane but only stage one command at a time.

Example:

1. AI explains the diagnostic plan.
2. AI stages a read-only diagnostic command.
3. User presses Enter.
4. Host captures structured result information.
5. AI reasons about the new result.
6. User requests `@ continue` or the UI exposes the next recommendation.
7. AI stages the next command.

No step may bypass the user's Enter key.

---

## 6. High-Level Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                      GTK4 Application                        │
│                                                              │
│  ┌────────────────────────────┐ ┌──────────────────────────┐ │
│  │        VTE Terminal        │ │      AI Assistant       │ │
│  │        Real Bash PTY       │ │         Pane            │ │
│  └──────────────┬─────────────┘ └────────────▲─────────────┘ │
│                 │                            │               │
│                 ▼                            │               │
│        Shell / Session Adapter               │               │
│        - cwd                                 │               │
│        - command boundaries                  │               │
│        - exit status                         │               │
│        - stdout/stderr                       │               │
│        - history                             │               │
│                 │                            │               │
│                 ▼                            │               │
│        Deterministic Host Layer              │               │
│        - passive eligibility gate            │               │
│        - command parser/validator            │               │
│        - risk/safety classifier              │               │
│        - secret filter                       │               │
│        - documentation resolver              │               │
│        - context builder                     │               │
│                 │                            │               │
│                 ▼                            │               │
│          Embedded llama.cpp Runtime          │               │
│                 │                            │               │
│                 ▼                            │               │
│          Small Fine-Tuned Model ─────────────┘               │
└──────────────────────────────────────────────────────────────┘
```

### 6.1 Terminal layer

The application uses VTE rather than terminal screen scraping. Shell integration should expose semantic events such as:

- prompt ready;
- command started;
- command completed;
- exit status;
- current directory.

OSC 133/VTE shell integration should be used where practical to preserve reliable command/output boundaries.

### 6.2 Platform adapters

The architecture should separate shell behavior and operating-system behavior behind adapters.

Initial adapters:

```text
ShellAdapter
└── BashAdapter

PlatformAdapter
└── ArchAdapter
```

This keeps later Zsh/Fish and Debian/Fedora support possible without redesigning the core application.

### 6.3 Host documentation layer

The model does not receive arbitrary shell execution tools.

The host may perform approved read-only lookups, such as:

- `man` content;
- Bash builtin help;
- command `--help` output under controlled conditions;
- executable discovery/type information;
- pacman/package metadata;
- `gh` help hierarchy;
- `gcloud` help hierarchy;
- safe system metadata.

These lookups are performed by the application and returned to the model as structured context.

The host decides when documentation lookup is appropriate. The model should not autonomously execute the lookup command itself.

### 6.4 Command validation and repair

A generated command should not immediately become visible ghost text.

The expected pipeline is:

```text
LLM candidate
    ↓
Shell parse
    ↓
CLI/argument validation
    ↓
Safety/risk validation
    ↓
If invalid and repairable:
    local documentation lookup
    ↓
One bounded repair inference
    ↓
Validation again
    ↓
Stage suggestion
```

The application must never execute the resulting command during validation.

---

## 7. Model Strategy

### 7.1 Embedded runtime

The model runtime should be private to the application:

- llama.cpp embedded in-process or through a private application-owned library boundary;
- no Ollama dependency;
- no LM Studio dependency;
- no daemon or public inference port;
- no cloud fallback;
- GGUF deployment format;
- model warmed at application startup;
- CPU baseline with optional hardware acceleration where practical.

### 7.2 Current model candidate

The current research leader is a fine-tuned **Qwen2.5 0.5B Instruct** model.

On a new 100-scenario unseen benchmark suite, the strongest training round achieved:

- 71.9% overall score;
- 71.9% Arch Linux;
- 68.8% troubleshooting;
- 75.4% GCloud;
- 78.3% GitHub CLI;
- 68.7% interaction;
- 100% JSON schema compliance;
- 100% tool-selection contract compliance;
- 27% command and flag correctness under the current strict scorer.

The same unseen suite scored the unmodified Qwen2.5 0.5B base model at 59.4% overall, providing evidence that the gains are genuine out-of-distribution improvements rather than benchmark memorization.

The model remains replaceable. The application should not encode model-specific behavior into the product architecture.

### 7.3 Training lessons so far

Model R&D has produced several important architectural findings:

1. Fine-tuning a 0.5B model can materially improve terminal-domain reasoning.
2. Broad domain coverage matters for a model this small.
3. Over-pruning training data can improve narrow behaviors while reducing command breadth.
4. Passive `NO_ACTION` is better handled by the host.
5. Documentation/tool-routing eligibility is better handled by the host.
6. Safety and risk classification must be deterministic application functions.
7. The model should focus on intent, command composition, explanation, clarification, and contextual reasoning.
8. A local command-validation/repair loop is likely to improve product-level accuracy more efficiently than teaching the model every version-sensitive CLI command.

---

## 8. Context Model

Each terminal tab owns an independent session context containing, at minimum:

- current working directory;
- shell type;
- platform metadata;
- recent command history;
- command exit status;
- bounded stdout/stderr;
- command start/end boundaries;
- local vs remote session state;
- pending AI suggestion;
- recent assistant interaction state.

Visual `clear` should clear the terminal display but not erase the AI's current-session context.

Persistent cross-session memory is not required for the initial release.

---

## 9. Remote / SSH Behavior

SSH is in scope for the initial product.

The application should distinguish at least:

```text
LOCAL
REMOTE
```

When a user enters an SSH session:

- the assistant may continue interpreting observed terminal commands and output;
- it must not use local package metadata or local `/etc` contents as evidence about the remote host;
- when remote system information is required, the assistant should stage a diagnostic command for the user to run remotely;
- the user must still press Enter for every remote command.

The UI should provide a subtle remote-session indicator.

---

## 10. File Context and Secret Boundaries

The assistant may use explicit or contextually relevant file contents when needed to explain terminal behavior, especially for configuration troubleshooting.

Examples:

```text
@ explain ./docker-compose.yml
@ what's wrong with /etc/fstab
```

The application should apply a secret filter before exposing file or environment content to the model.

Initial deny/sensitive categories should include:

- private SSH keys;
- GPG private material;
- password stores;
- browser credential databases;
- `/etc/shadow` contents;
- credential/token environment variables;
- known secret/config formats where disclosure is inappropriate.

The product should disclose when relevant files or local documentation were used as context.

---

## 11. MVP Scope

### Included

- GTK4 desktop application;
- VTE terminal pane backed by a real Bash PTY;
- collapsible AI pane;
- terminal tabs with isolated context;
- Arch/CachyOS platform awareness;
- Bash shell awareness;
- embedded local llama.cpp inference;
- fine-tuned small model;
- explicit `@` interaction;
- passive ghost suggestions through a deterministic eligibility gate;
- `Tab` to accept AI ghost text;
- command-error interpretation;
- command/flag explanation;
- staged command recommendations;
- multi-step troubleshooting with user-controlled execution;
- deterministic risk/safety classification;
- command validation before staging;
- local documentation lookup;
- current-session context;
- SSH-aware local/remote context;
- local-only privacy guarantees.

### Deferred

- persistent cross-session memory;
- repository indexing or coding-agent behavior;
- autonomous execution;
- cloud inference fallback;
- Ollama/LM Studio dependency;
- plugins/extensions marketplace;
- voice interface;
- multiple shell support;
- first-class non-Arch distribution support;
- generalized desktop/computer-use automation.

---

## 12. Technical Direction

### Application

- Rust
- GTK4
- VTE4

### AI runtime

- llama.cpp
- GGUF models
- CPU baseline
- optional Vulkan/CUDA/ROCm acceleration where maintainable

### Shell integration

- Bash v1
- VTE semantic shell signals where available
- OSC 133 command/prompt boundaries where practical

### Distribution

- Native Arch/CachyOS packaging first
- model may be packaged separately to keep application updates lightweight

---

## 13. Success Metrics

### User-control metrics

- 0 autonomous user-command executions;
- 100% of staged commands require explicit user Enter;
- no hidden agent execution loop.

### Interaction quality

- high precision for passive AI invocation;
- near-zero interruptions during ordinary valid shell use;
- no cross-tab context leakage;
- clear distinction between local and remote sessions.

### Model/system quality

Initial research targets:

- strong improvement over the generic base model on unseen terminal tasks;
- near-100% structured response compliance;
- command hallucinations detected before staging;
- 100% final-system safety gate on blocked critical patterns;
- local documentation used rather than guessed when version-sensitive syntax is uncertain.

### Performance

Aspirational targets:

- deterministic completion: effectively instantaneous;
- explicit AI requests: p50 <= 750 ms, p95 <= 1500 ms on target development hardware;
- passive AI suggestions: low enough latency to feel immediate after the idle debounce;
- AI memory footprint small enough to remain continuously loaded on a typical developer workstation.

---

## 14. Major Risks

### Tiny-model command hallucination

**Mitigation:** fine-tuning, local documentation retrieval, deterministic syntax validation, bounded repair pass.

### Unsafe or destructive recommendations

**Mitigation:** host-owned semantic safety/risk classifier; never trust model risk labels as authoritative.

### Excessive passive interruptions

**Mitigation:** deterministic eligibility gate before model invocation.

### Model becomes overly domain-specific

**Mitigation:** unseen holdout benchmarks, broad training data, regression testing, replaceable model runtime.

### Version-sensitive CLI syntax

**Mitigation:** local installed help/man metadata rather than model memorization.

### Local/remote context confusion

**Mitigation:** explicit session state and evidence boundaries for SSH.

---

## 15. Current Project Phase

The project has moved beyond initial feasibility research.

The current evidence demonstrates that:

- a 0.5B embedded model is viable for meaningful terminal assistance;
- targeted fine-tuning generalizes to unseen terminal scenarios;
- small-model weaknesses can be reduced by moving deterministic responsibilities into host software;
- the next major engineering milestone is the production-style host pipeline: context collection, documentation resolution, command validation/repair, risk classification, and UI integration.

The project should now progress from model feasibility into application implementation while keeping benchmark-driven model development as a parallel workstream.
