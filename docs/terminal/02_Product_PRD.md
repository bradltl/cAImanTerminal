# cAIman Terminal — Product Requirements Document (PRD)

## Assistive alpha amendment — 2026-09-14

Alpha has **no latency acceptance threshold**. Measure completed-response timing
and responsiveness, but prioritize correct, complete, useful assistance and clear
explanations over token-count or latency optimizations. A fast refusal is not a
successful answer. CPU remains supported; GPU offload is optional and explicitly
enabled, with honest capability/fallback reporting.

Validated suggestions belong inline at the active prompt, visually separate from
typed input. Tab stages a visible suggestion; only a distinct user Enter executes
it. Explanations, plans, uncertainty and host warnings belong in the assistant
pane. The model must explain its recommendation; host-generated descriptions are
labelled as such. Incomplete coverage must not discard otherwise useful advice
or misrepresent an unverified proposal as a validated command.

The versioned policy is `alpha-v1.1`, adding audited literal file operations.
Ordinary risky operations can stage with warnings after all other checks pass;
the current critical-operation blocks, secret protection, unsupported syntax and
stale-state protections remain. Broad natural-language coverage, remote staging
and complete semantic verification remain open work, not solved by this amendment.

## Retained alpha conformance requirements

The [alpha conformance contract](14_Alpha_Conformance.md) specifies current MVP
staging claims for this release: narrow audited CLI coverage, no passive/remote
staging, and one separately requested model retry after an unverifiable result.
Safety/secret rejection never retries. Dogfood requires exact deterministic
conformance and passing boundary/PTY/fuzz and assistance-quality gates, with no
unverified command successes. Timings are diagnostic, not an alpha release gate.
Dogfood metrics are memory-only; export is manual and aggregate-only. V4 remains
deferred until real dogfooding and material stabilization.

> Scope: terminal application. Reviewed 2026-09-10 for the split workspace.
> Code is in `terminal/`; commands run from the repository root unless stated otherwise.
> Model research is documented in [llm/README.md](../../llm/README.md).

**Version:** 0.1
**Status:** Product requirements and acceptance targets; implementation status is tracked in 12_Project_Status.md
**Initial platform:** Arch Linux / CachyOS
**Initial shell:** Bash
**Product type:** Local AI-assisted terminal emulator

---

## 1. Product Summary

cAIman Terminal is a desktop Linux terminal application with a real Bash terminal and an integrated, context-aware AI assistant. The assistant helps users construct commands, understand shell behavior, interpret failures, and troubleshoot terminal workflows while remaining fully local and under explicit user control.

The AI is **not an execution agent**. It may stage a command, but it may never execute the command. The user must press Enter for every user command.

The application should function as a normal terminal even when the AI is disabled or unavailable.

---

## 2. Goals

### G-001 — Context-aware terminal assistance

Provide AI assistance that understands the current terminal session, including current directory, recent commands, output, exit status, platform, and shell context.

### G-002 — Preserve user execution control

Ensure the AI cannot autonomously execute terminal commands under any circumstances.

### G-003 — Fully local operation

Provide inference and core assistant functionality without cloud services or external APIs.

### G-004 — Low resource overhead

Use a small embedded model and deterministic host logic to provide useful assistance without requiring a large local inference stack.

### G-005 — High trustworthiness

Prefer clarification, validation, and local documentation over hallucinated syntax or invented identifiers.

### G-006 — Minimal interruption

Provide passive assistance only when likely to add value and remain silent during ordinary valid terminal use.

### G-007 — Native Linux-terminal experience

Preserve expected Bash, PTY, terminal application, keyboard, tab, completion, and remote-session behavior.

---

## 3. Non-Goals for MVP

The MVP will not:

- execute user commands autonomously;
- provide an agent/auto mode;
- perform cloud inference;
- require Ollama or LM Studio;
- support every Linux distribution;
- support every shell;
- act as a coding agent or repository-wide software engineer;
- provide persistent cross-session AI memory;
- provide generalized desktop automation;
- expose a public model API/server;
- use telemetry by default.

---

## 4. Primary User

### Persona: Linux technical user / developer

The initial user is comfortable using a terminal and wants faster access to command syntax, diagnostics, and system context without leaving the shell.

Representative characteristics:

- uses Linux as a primary or frequent development environment;
- understands the shell but does not memorize every CLI option;
- works across OS tools, developer tools, GitHub, and cloud CLIs;
- values local privacy and low latency;
- is willing to review commands before execution;
- does not want an autonomous agent changing the system.

The product should remain useful to less experienced users, but MVP decisions should not reduce terminal fidelity for experienced users.

---

## 5. Core User Stories

### US-001 — Translate intent into a command

As a user, I can type:

```text
@ find every log file larger than 500 MB
```

and receive a correct command staged for review.

### US-002 — Explain a failure

As a user, after a command fails, I can type:

```text
@ explain that error
```

and receive a concise explanation grounded in the actual command, output, and exit status.

### US-003 — Suggest the next diagnostic

As a user, I can ask the assistant to troubleshoot a failure and receive one safe next diagnostic command at a time.

### US-004 — Preserve execution control

As a user, I know that no AI-generated command will run until I press Enter.

### US-005 — Passive correction

As a user, when I make an obvious typo, the terminal may offer a ghost-text correction that I can accept with Tab.

### US-006 — No unnecessary interruptions

As a user, normal valid terminal input should not cause the AI pane to constantly comment or offer redundant suggestions.

### US-007 — Use current CLI documentation

As a user, I want the assistant to rely on the version of `gh`, `gcloud`, pacman, and other tools actually installed on my machine rather than invent version-specific syntax.

### US-008 — Work over SSH

As a user, I can SSH to another host and continue receiving context-aware help without the assistant confusing local and remote system metadata.

### US-009 — Review a multi-step plan

As a user, I can see the assistant's intended troubleshooting plan but remain in control of each step.

---

## 6. Functional Requirements

## 6.1 Terminal Runtime

### FR-TERM-001 — Real PTY

The application shall host a real pseudo-terminal and run Bash as the initial supported shell.

### FR-TERM-002 — Normal terminal compatibility

The terminal shall support normal interactive terminal applications without AI-specific wrappers around each command.

### FR-TERM-003 — Shell command boundaries

The application shall detect prompt/command/output boundaries using semantic shell integration rather than terminal pixel scraping where practical.

### FR-TERM-004 — Current directory

The application shall track the active working directory for each terminal tab.

### FR-TERM-005 — Exit status

The application shall capture the exit status of completed commands.

### FR-TERM-006 — Output capture

The application shall retain a bounded representation of recent stdout/stderr for AI context.

### FR-TERM-007 — Visual clear

Running `clear` shall clear the terminal display but shall not erase current-session context used by the assistant.

---

## 6.2 Terminal Tabs

### FR-TAB-001 — Multiple tabs

The application shall support multiple terminal tabs in MVP.

### FR-TAB-002 — Context isolation

Each tab shall have isolated:

- PTY;
- current directory;
- command history;
- captured output;
- assistant conversation state;
- pending suggestion;
- local/remote state.

### FR-TAB-003 — No cross-tab leakage

Context from one tab shall not be provided to another tab unless an explicit future feature enables it.

---

## 6.3 AI Pane

### FR-AIUI-001 — Right-side assistant pane

The application shall provide a right-side AI pane adjacent to the terminal.

### FR-AIUI-002 — Collapsible

The user shall be able to collapse and restore the AI pane.

### FR-AIUI-003 — Display role

The AI pane shall primarily display:

- explanations;
- multi-step plans;
- relevant warnings;
- source/documentation disclosures;
- assistant status.

### FR-AIUI-004 — No required chat input box

The primary AI input mechanism shall be the terminal prompt, not a separate assistant text box.

---

## 6.4 Explicit AI Interaction

### FR-EXPLICIT-001 — `@` prefix

Input beginning with `@` at a Bash prompt shall be intercepted by the application before it is passed to Bash.

### FR-EXPLICIT-002 — Supported intents

The assistant shall support explicit requests such as:

```text
@ update my system
@ explain that error
@ why did that fail?
@ what does this flag do?
@ use rsync instead
@ make that recursive
@ continue
@ what's next?
```

### FR-EXPLICIT-003 — AI responses

The AI may return one of the following conceptual outcomes:

- command recommendation;
- explanation;
- clarification question;
- plan plus one next command.

### FR-EXPLICIT-004 — No execution

An explicit AI request shall never directly execute the recommended user command.

---

## 6.5 Passive AI Assistance

### FR-PASSIVE-001 — Debounce

Passive AI evaluation shall occur only after a configurable short idle interval
(current default 250 ms). This debounce is a behavior setting, not a response-time
acceptance threshold.

### FR-PASSIVE-002 — Host eligibility gate

The host application shall determine whether the current input is eligible for passive AI inference.

The LLM shall not be the primary component deciding whether ordinary valid input deserves interruption.

### FR-PASSIVE-003 — Eligible conditions

Potential eligibility conditions include:

- likely natural-language request at the shell prompt;
- obvious executable typo;
- invalid known flag;
- high-confidence incomplete command;
- likely correction after a failed command.

### FR-PASSIVE-004 — Suppressed conditions

AI inference should normally be suppressed for:

- ordinary valid shell commands;
- comments;
- interactive full-screen terminal applications;
- normal path completion;
- shell input already covered by deterministic completion;
- low-confidence ambiguous partial input.

### FR-PASSIVE-005 — Ghost text

Passive command recommendations shall appear as ghost text rather than being inserted automatically.
The display must be aligned with the active prompt/cursor, not a reserved strip
below the terminal. When placement or context is uncertain, hide the ghost and
preserve normal Bash completion; keep any useful explanation in the pane.

---

## 6.6 Tab Acceptance and Completion

### FR-COMP-001 — Tab precedence

If AI ghost text is visible, pressing Tab shall accept the AI ghost text.

Otherwise, Tab shall perform normal Bash completion.

### FR-COMP-002 — Acceptance is not execution

Accepting AI ghost text shall only place the proposed text into the command buffer.

### FR-COMP-003 — Deterministic completion first

History, PATH, filesystem, Bash completion, and other deterministic completion systems should respond before AI inference where possible.

---

## 6.7 Model Response Contract

### FR-MODEL-001 — Structured response

The embedded model shall return a constrained structured response rather than arbitrary UI prose.

Target conceptual schema:

```json
{
  "action": "suggest_command | explain | clarify",
  "command": "string or null",
  "explanation": "string or null",
  "question": "string or null",
  "plan": null
}
```

The exact serialized schema may evolve during implementation.
Generated suggestions require a nonempty explanation of purpose, important
arguments, effects and uncertainty. A short optional plan may describe subsequent
steps, but only one command is offered. Explainability means a useful rationale,
not disclosure of hidden chain-of-thought. Deterministic descriptions must not
be presented as model-generated reasoning.

### FR-MODEL-002 — Host-owned risk

Model-provided risk labels, if retained for research, shall not be authoritative.

The host shall own final risk and safety classification.

### FR-MODEL-003 — Host-owned documentation routing

The model shall not require a general-purpose execution/tool interface for documentation lookup.

The host determines whether local documentation should be supplied.

### FR-MODEL-004 — Host-owned passive `NO_ACTION`

Passive non-interruption shall be primarily implemented by the host eligibility gate rather than model generation.

---

## 6.8 Context Collection

### FR-CTX-001 — Structured terminal context

The context builder shall provide structured data instead of raw terminal screen scraping.

### FR-CTX-002 — Context fields

Context may include:

- shell;
- OS/distribution;
- kernel;
- current directory;
- recent commands;
- exit codes;
- bounded stdout/stderr;
- known installed executables;
- local/remote session state;
- relevant approved file contents;
- documentation snippets supplied by the host.

### FR-CTX-003 — Context limits

Raw terminal history shall be bounded and summarized as necessary to control token usage and latency.

### FR-CTX-004 — Recent-session priority

Current-session context shall take priority over persistent historical memory in MVP.

---

## 6.9 Command Recommendation

### FR-CMD-001 — Stage only

The assistant may stage one command for the user.

### FR-CMD-002 — Preserve editability

The user shall be able to edit a staged command before execution.

### FR-CMD-003 — Multi-step work

For a multi-step task, the assistant may show the entire conceptual plan but shall only stage the current next command.

### FR-CMD-004 — Missing information

The assistant should request clarification rather than invent required values such as:

- release IDs;
- workflow IDs;
- target hosts;
- region/zone values;
- filenames;
- deployment targets;
- destructive-operation targets.

### FR-CMD-005 — Context continuation

`@ continue` shall use the current session's assistant/task context and newly observed command result.

---

## 6.10 Command Validation

### FR-VALID-001 — Pre-stage validation

Every AI-generated command shall pass through deterministic validation before being offered as a stageable suggestion.

### FR-VALID-002 — Shell parsing

The validator shall parse shell syntax sufficiently to identify:

- executable;
- arguments;
- flags;
- quoting;
- pipes;
- redirections;
- command chains;
- destructive subcommands where relevant.

### FR-VALID-003 — Executable validation

Where practical, the application shall verify that the proposed executable exists in the relevant environment.

### FR-VALID-004 — Flag/subcommand validation

For supported command families, the application should validate known subcommands and flags using current local metadata/help.

### FR-VALID-005 — Invalid suggestion

An invalid command shall not be presented as a trusted/ready ghost suggestion.

### FR-VALID-006 — Deterministic correction and explicit retry

Alpha permits automatic deterministic correction only for audited task-option
rules, followed by every validation gate. An unverifiable first response ends
with clarification or verification failure. A separate Retry suggestion action
permits one new inference bound to unchanged request context. Safety/secret
rejection is never repairable, and passive requests never retry.

### FR-VALID-007 — Repair remains non-executing

The repair process shall never execute the generated user command.

---

## 6.11 Documentation Resolver

### FR-DOC-001 — Whitelisted read-only capabilities

The host may provide read-only documentation/system metadata through controlled providers.

Initial provider categories:

- man page lookup;
- Bash builtin help;
- command help;
- executable discovery/type;
- package metadata;
- pacman information;
- GitHub CLI help;
- GCloud CLI help;
- safe host metadata.

### FR-DOC-002 — No arbitrary model shell tool

The LLM shall not receive a general arbitrary shell execution function.

### FR-DOC-003 — Version-sensitive commands

The host should favor current installed CLI help for version-sensitive or obscure commands rather than relying on model memory.

### FR-DOC-004 — Timeouts

Any host documentation probe capable of invoking a binary shall have strict timeouts and allowlisting.

### FR-DOC-005 — Source disclosure

The AI pane should indicate when a recommendation relied on local documentation or file context.

---

## 6.12 Safety and Risk

### FR-SAFE-001 — Deterministic safety layer

Final command risk shall be determined by host code, not solely by the language model.

### FR-SAFE-002 — Risk levels

Initial user-facing risk levels:

```text
Normal
Caution
Elevated
```

### FR-SAFE-003 — Elevated examples

Elevated or critical detection shall include categories such as:

- sudo/root operations;
- recursive deletion;
- filesystem formatting;
- block-device writes;
- package removal of critical system components;
- recursive permission/ownership changes;
- firewall/network-policy changes;
- service/system changes;
- pipes from remote content into interpreters;
- credential exposure;
- system-critical path mutation;
- fork/resource exhaustion patterns.

### FR-SAFE-004 — Semantic classification

Risk classification should be semantic where possible rather than relying only on exact regex strings.

Example:

```text
operation = package removal
package = glibc
```

should be critical regardless of whether the proposed package manager is `pacman`, `apt`, or another command.

### FR-SAFE-005 — Warning display

Elevated suggestions shall display a clear reason before the user chooses whether to execute the command.

### FR-SAFE-006 — User remains in control

Safety warnings shall not convert the assistant into an execution agent. The user continues to control terminal execution.

### FR-SAFE-007 — Shipping safety gate

The final product pipeline shall achieve 100% pass on the defined critical safety regression suite before release.

---

## 6.13 Error Interpretation and Troubleshooting

### FR-ERR-001 — Structured result

After a command completes, the assistant may receive:

- command text;
- cwd;
- exit code;
- stdout;
- stderr;
- timestamp/session metadata.

### FR-ERR-002 — Concise explanation

The assistant shall provide a concise explanation of likely failure cause when requested.

### FR-ERR-003 — Diagnostic-first behavior

For troubleshooting, the assistant should prefer diagnostic/read-only steps before configuration changes when practical.

### FR-ERR-004 — Do not repeat known failure

The assistant should not blindly recommend the same command that just failed unless it has a specific reason for retrying it.

### FR-ERR-005 — One next step

When troubleshooting requires multiple actions, the assistant shall stage only one next command at a time.

---

## 6.14 File Context

### FR-FILE-001 — Explicit file request

The user may ask the assistant to interpret a local file by path.

Examples:

```text
@ explain ./docker-compose.yml
@ what's wrong with /etc/fstab
```

### FR-FILE-002 — Contextual file inference

The assistant may identify a relevant configuration file based on terminal context, subject to the secret policy.

### FR-FILE-003 — Disclosure

The assistant pane shall indicate when file contents were used.

### FR-FILE-004 — Secret filtering

Known sensitive file types and paths shall be denied or redacted before model context construction.

Initial sensitive categories include:

- private SSH keys;
- GPG private files;
- browser credential stores;
- password managers;
- `/etc/shadow` contents;
- credential/token environment variables;
- obvious secret-bearing configuration.

---

## 6.15 SSH / Remote Sessions

### FR-SSH-001 — Detect remote state

The application shall track whether the tab is in a local or remote shell context when practical.

### FR-SSH-002 — Remote indicator

The UI shall display a subtle remote-session state.

### FR-SSH-003 — Evidence separation

Local package metadata, local system files, and local distribution documentation shall not be presented to the model as facts about the remote system.

### FR-SSH-004 — Remote diagnostics

If remote metadata is required, the assistant may stage a read-only diagnostic command for the user to execute on the remote host.

### FR-SSH-005 — Remote user execution

The user must press Enter for every suggested remote command.

---

## 6.16 Undo / Command Journal

### FR-UNDO-001 — Command journal

The application shall record session-level metadata for commands, including:

- command;
- cwd;
- timestamp;
- exit code;
- bounded output;
- AI-origin indicator;
- host risk classification.

### FR-UNDO-002 — Honest reversibility

The application shall never claim an operation is undoable unless a valid reversal mechanism is known.

### FR-UNDO-003 — Undo staging

For known reversible operations, `@ undo that` may stage a reversal command but shall still require user Enter.

### FR-UNDO-004 — Non-reversible commands

For operations such as destructive file removal, disk writes, or destructive Git history rewrites, the assistant shall state when reliable undo is unavailable.

Advanced snapshot-based undo is deferred.

---

## 6.17 Privacy

### FR-PRIV-001 — Local inference

AI inference shall execute locally.

### FR-PRIV-002 — No network inference dependency

The application shall not require network access to reason about terminal context.

### FR-PRIV-003 — Memory-only aggregate measurement

The application shall not automatically write or upload session metrics.
Metrics shall be bounded and memory-only, with manual aggregate export containing
no commands, prompts, output, paths, free-form errors, hashes or persistent IDs.
Unknown execution attribution shall remain unknown.

### FR-PRIV-004 — No cloud fallback

Failure of the local model shall not silently redirect inference to a remote provider.

### FR-PRIV-005 — Explicit downloads only

Model/application updates that require network downloads shall occur through explicit installation/update behavior, not hidden runtime retrieval.

---

## 6.18 Model Runtime

### FR-RUNTIME-001 — Embedded llama.cpp

The application shall use a private llama.cpp-compatible runtime.

### FR-RUNTIME-002 — GGUF

Production models shall use GGUF-compatible deployment artifacts.

### FR-RUNTIME-003 — No external daemon requirement

The user shall not need Ollama, LM Studio, or a separately managed inference server.

### FR-RUNTIME-004 — Warm model

The model should be loaded/warmed near application startup so normal requests avoid repeated load cost.

### FR-RUNTIME-005 — CPU baseline

The product shall function with CPU inference on supported target hardware.

### FR-RUNTIME-006 — Optional acceleration

The application shall support explicitly enabled GPU layer offload in compatible
builds, without making GPU hardware a baseline requirement. CPU-only builds and
unavailable-device fallback remain usable. GPU selection must preserve verified
model loading, bounded supervision and fresh per-request inference state.

### FR-RUNTIME-007 — Replaceable model

The architecture shall permit swapping the embedded model without rewriting terminal/session logic.

---

## 7. Current Model R&D Baseline

The current champion research model is a fine-tuned Qwen2.5 0.5B Instruct variant.

On an unseen 100-scenario benchmark suite:

| Metric | Base Qwen2.5 0.5B | Current champion SFT |
|---|---:|---:|
| Overall | 59.4% | 71.9% |
| Bash | 65.8% | 75.7% |
| Arch | 47.7% | 71.9% |
| Troubleshooting | 46.9% | 68.8% |
| GCloud | 64.0% | 75.4% |
| GitHub CLI | 63.3% | 78.3% |
| Interaction | 63.5% | 68.7% |
| JSON compliance | 90.0% | 100.0% |
| Command correctness | 6.0% | 27.0% |

These metrics are research baselines, not final product acceptance criteria. The production system is expected to outperform raw-model behavior through deterministic validation, current local documentation, bounded repair, and host-owned safety logic.

---

## 8. Performance Requirements

### PR-PERF-001 — Interactive responsiveness

There is no alpha p50/p95 requirement. Record end-to-end worker latency, queueing,
model preparation/prefill/decoding and validation separately to guide optimization.
Report desktop input-to-display measurements separately from worker timings.
Latency alone must not fail alpha acceptance or justify incomplete explanations.

### PR-PERF-002 — Passive responsiveness

Passive suggestions should feel immediate after the input debounce. Deterministic completion should be used whenever possible to avoid model latency.

### PR-PERF-003 — Memory

The baseline model/runtime combination should remain small enough to stay resident continuously on a normal developer workstation.

### PR-PERF-004 — Bounded generation

Terminal-assistant responses shall remain bounded and cancellable, with enough
budget for a complete command, useful explanation and a concise plan when needed.
Truncated responses are failures, regardless of how quickly they finish.

### PR-PERF-005 — No repeated model load

Routine requests shall not reload the model.

---

## 9. MVP Acceptance Criteria

The MVP is ready for an internal dogfood release when all of the following are true.

### Terminal

- [ ] Real Bash PTY works reliably.
- [ ] Interactive terminal applications function normally.
- [ ] Current directory and command exit status are captured reliably.
- [ ] Tabs maintain isolated context.
- [ ] `clear` does not destroy AI session context.

### AI interaction

- [ ] `@` requests are intercepted and never sent to Bash.
- [ ] AI pane displays explanations and plans.
- [ ] AI can stage a command into the terminal.
- [ ] User Enter is required for every staged command.
- [ ] Multi-step troubleshooting stages one step at a time.
- [ ] `@ continue` uses prior task/session context.

### Passive assistance

- [ ] Passive eligibility is host-gated.
- [ ] Ordinary valid Bash commands do not trigger repeated AI interruptions.
- [ ] AI ghost text is visually distinguishable from typed text.
- [ ] Tab accepts ghost text when present.
- [ ] Normal Bash Tab completion works when no ghost text is present.

### Validation/safety

- [ ] AI command candidates are parsed before staging.
- [ ] Critical destructive operations are detected semantically.
- [ ] Risk classification does not depend on the model's own label.
- [ ] Invalid supported CLI syntax is rejected or repaired before staging.
- [ ] Critical safety benchmark passes 100% at the final-system level.
- [ ] No validator path executes the candidate user command.

### Documentation

- [ ] Host can provide man/Bash help.
- [ ] Host can resolve Arch/pacman metadata.
- [ ] Host can provide relevant `gh` help.
- [ ] Host can provide relevant `gcloud` help.
- [ ] Documentation probes are allowlisted and timeout-bounded.

### Privacy/runtime

- [ ] Inference works without cloud connectivity.
- [ ] No Ollama/LM Studio requirement.
- [ ] No terminal telemetry is transmitted by default.
- [ ] Model is warmed and remains resident.
- [ ] CPU-only inference path works.

---

## 10. Benchmark and Quality Gates

### QR-001 — Regression benchmark

Every model/prompt/architecture change shall run the existing regression benchmark.

### QR-002 — Locked unseen/holdout suite

Holdout scenarios shall remain excluded from training data until intentionally retired and replaced with a new unseen suite.

### QR-003 — Raw vs system metrics

Reports should distinguish:

```text
Raw model quality
Post-documentation/repair quality
Final validated command usability
Final system safety
```

### QR-004 — Command semantics

Benchmark scoring should increasingly use shell/argument semantics rather than narrow exact-command regex matching.

### QR-005 — Model metadata

Each benchmark result shall record:

- model name;
- resolved model file;
- SHA-256;
- quantization;
- prompt/schema version;
- benchmark version;
- runtime/backend version;
- inference settings;
- hardware metadata.

### QR-006 — Model identity

Comparison tooling shall detect accidental duplicate model hashes under different labels.

### QR-007 — Safety independence

Safety scoring shall inspect the command semantics independently from general action/command correctness scoring.

---

## 11. Initial Release Scope

### MVP 0.1

- Arch/CachyOS;
- Bash;
- GTK4/VTE4;
- tabs;
- AI pane;
- `@` explicit requests;
- host-gated passive suggestions;
- embedded Qwen-class local model;
- local session context;
- command staging;
- error explanation;
- command validation;
- deterministic safety classification;
- documentation resolver;
- basic SSH context awareness.

### Post-MVP candidates

- persistent memory;
- Zsh/Fish;
- Debian/Fedora adapters;
- deeper Git/repository awareness;
- richer reversible-operation journal;
- configurable model packs;
- plugin/tool ecosystem;
- additional local documentation providers;
- advanced hardware acceleration;
- model update management UI.

---

## 12. Open Product / Engineering Decisions

1. Final application/product name.
2. Final model response schema after host-owned risk/documentation responsibilities are removed.
3. Exact strategy for Bash semantic integration across shell configurations.
4. Whether model weights ship in the main package or a separate package.
5. Which GPU acceleration backends are supported in the first release.
6. Exact secret-filter policy and disclosure UX.
7. Exact command-validator implementation and shell AST library.
8. How much local CLI help is cached versus retrieved on demand.
9. Resolved for alpha: deterministic correction only; one separately requested model retry, never safety/secret repair.
10. Packaging/repository strategy for Arch/CachyOS distribution.

---

## 13. Recommended Next Engineering Milestone

Build the **production-style AI host pipeline** around the current champion model before another broad training round.

Milestone components:

1. terminal context builder;
2. passive eligibility gate;
3. model adapter and constrained output parser;
4. shell command parser;
5. command/subcommand/flag validator;
6. semantic safety/risk classifier;
7. documentation resolver for Bash/man/pacman/`gh`/`gcloud`;
8. deterministic correction and separately requested single retry;
9. staging/ghost-text UI;
10. benchmark integration that reports raw-model and final-system results separately.

The next training dataset should then target only residual failures that deterministic host logic cannot reliably solve, especially ambiguity, clarification, intent interpretation, and multi-turn contextual reasoning.
