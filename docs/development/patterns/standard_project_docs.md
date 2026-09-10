# Standard Project Documentation Structure

To maintain consistency, traceability, and ease of onboarding for both human engineers and AI agents, every project within the ecosystem must implement the following standardized set of documents. These documents serve as the definitive source of truth for the project's lifecycle.

## Required Documents

1. **`00_README.md`**
   - The entry point for the repository. Includes quick start instructions, high-level purpose, and links to all other relevant documentation.

2. **`01_Project_Overview.md`**
   - A high-level executive summary of the project, its business value, target audience, and core capabilities.

3. **`02_Product_PRD.md`** (Product Requirements Document)
   - Detailed user stories, functional requirements, non-functional requirements, and explicit definition of out-of-scope items.

4. **`03_Architecture_Overview.md`**
   - System design diagrams, technology stack choices, integration points, and high-level structural boundaries (e.g., separating presentation from core logic).

5. **`04_Data_Structure_and_Storage.md`**
   - Data dictionary, database schemas, JSON payloads, and state management details.

6. **`05_Agent_Development_Plan.md`**
   - Instructions and milestone breakdowns specifically tailored for AI agents (e.g., dividing tasks between implementation agents and review agents).

7. **`06_Testing_Plan.md`**
   - Acceptance criteria, unit testing strategies, integration test edge cases, and manual validation steps.

8. **`07_Decision_Log.md`** (ADR - Architecture Decision Records)
   - A chronological record of significant technical and product decisions, including the context, alternatives considered, and the chosen path.

9. **`08_Module_Service_Specifications.md`**
   - Detailed breakdown of individual services, APIs, or modules, including clear contracts and I/O expectations.

10. **`09_Operational_and_Support_Overview.md`**
    - Playbooks for deployment, CI/CD pipelines, observability/monitoring setups, and troubleshooting guides for DevOps.

11. **`10_User_and_Admin_Guides.md`**
    - Documentation geared toward end-users and administrators operating the software in production.

12. **`11_Open_Issues_Risks_and_Backlog.md`**
    - A living document tracking known limitations, technical debt, identified security risks, and future milestone planning.

13. **`12_Project_Status.md`**
    - A frequently updated snapshot of the current state of the project, recent milestones achieved, and immediate next steps.

14. **`.agent-config.yaml`** (Agent Configuration)
    - A configuration file residing in the project root that maps specific standard roles (e.g., Principal Engineer, DevOps, Planner) to their required LLM (e.g., Gemini 1.5 Pro) and execution framework (e.g., Antigravity, Autogen). This ensures agents always use the correct models and parameters per project.
