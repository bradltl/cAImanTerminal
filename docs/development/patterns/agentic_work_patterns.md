# Agentic Work Patterns

As AI-assisted software delivery evolves in the ecosystem, standardizing how human and AI agents collaborate is essential. These patterns are extracted from repository rule sets (`AGENTS.md`) and successful delivery histories.

## 1. Multi-Agent Delegation Strategy
**Description:** Separating concerns among different LLMs or sub-agents improves quality and prevents conflicting edits.
- **Implementation Agent**: Focuses strictly on writing production code, adhering to existing architecture, and adding tests.
- **Review/Testing Agent (Principal Engineer role)**: Reviews implementation branches, writes test plans, validates edge cases, and checks against architecture boundaries.
- **Planner Agent**: Breaks down large projects into structured milestone task packets.

## 2. Iterative Delivery & Thin Vertical Slices
**Description:** Breaking down large projects into smaller, verifiable phases.
- Prefer "thin vertical slices" over broad, unfinished scaffolding to deliver minimal value and test assumptions early.
- Perform frequent commits and pushes at points of value. This ensures progress is preserved and makes rollback easier if an AI agent hallucinates or takes a wrong architectural turn.

## 3. Strict Definition of Done (DoD) & Verification
**Description:** AI-generated code must not be merged or considered complete without rigorous verification.
- Output must explicitly list assumptions, consumed inputs, and open questions.
- Deterministic testing must accompany the code changes.
- Security assessments and architectural reviews must be performed before major PRs are accepted.

## 4. Continuous Documentation Maintenance
**Description:** Documentation is the ultimate source of truth for agents.
- Agents must update the project state, decision logs (ADRs), and schemas whenever contracts change.
- Never rely solely on chat history; write state to Markdown specs so future agents have the correct context.

## 5. Testable Agent Skills (Modular Context)
**Description:** Rather than passing monolithic system prompts, domain knowledge should be distributed into discrete, testable "skills" or plugins (e.g., `SKILL.md` files).
- Agents can load these specialized skills on-demand for tasks like Frontend (Lit), Backend (Go/Spanner), or Workflow (PR Descriptions).
- This keeps the agent's context window focused and budget-friendly.

## 6. Automated LLM Evaluations (LLM-as-a-Judge)
**Description:** Agent skills and outputs should be graded using deterministic harnesses and multi-model sweeps.
- Evaluate agent performance by comparing outputs with and without a skill loaded.
- Use an LLM as a judge (e.g., Sonnet or Opus) to score head-to-head A/B tests deterministically, preventing regressions in agent capabilities.

## 7. Agent Guardrails and Sandbox Containment
**Description:** Agentic sessions must operate within enforced bounds to ensure safety and prevent runaway costs.
- Implement explicit stops (e.g., refusing to complete on a red CI build).
- Monitor outbound data for credential shapes and audit all agent actions via local telemetry.
