# Project Hygiene and Engineering Standards

To ensure long-term maintainability and consistency across the ecosystem, all projects—whether built by human engineers or AI agents—must adhere to the following hygiene and standard practices.

## 1. Code Readability and Commenting
- **Human-Readable Code**: All complex logic must be accompanied by clear, concise comments explaining the *why*, not just the *what*. Code should be written assuming a human will need to read, debug, and maintain it.
- **Self-Documenting Structure**: Use descriptive variable and function names to minimize the need for redundant inline comments.

## 2. Developer Documentation
- **Standard Project Docs**: Every repository must adopt the 14-part file structure defined in [Standard Project Documentation](standard_project_docs.md). This includes a PRD, Architecture Overview, Decision Log, and Project Status.
- **Scope**: The documentation must explain how to set up the local environment, run tests, build the project, and understand the core architecture for both human engineers and AI agents.

## 3. Conventional Commits
- **Standardized History**: Commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification to allow for automated changelog generation and clear project history.
- **Formats**: Use standard prefixes such as:
  - `feat:` for new features
  - `fix:` for bug fixes
  - `chore:` for routine tasks, dependency updates, or tool configurations
  - `docs:` for documentation updates
  - `refactor:` for code changes that neither fix a bug nor add a feature

## 4. CI/CD and Automated Testing
- **Pipeline Integration**: Automated testing (unit, integration, and deterministic sim tests) must be integrated directly into the Continuous Integration / Continuous Deployment (CI/CD) pipelines.
- **Quality Gates**: Code cannot be merged into the main branch unless it passes all automated tests and linter checks in the pipeline.

## 5. Logging and Observability
- **Standard Formats**: Where appropriate, use standard observability frameworks like [OpenTelemetry (OTEL)](https://opentelemetry.io/) to emit metrics, logs, and distributed traces.
- **Configurable Levels**: Applications must support configurable logging levels (e.g., `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`) to adapt to different diagnostic needs.
- **Environment Context**: Logging strategies must be tailored to the operating environment (e.g., highly verbose debug logs during local development; structured, rate-limited JSON logs in production environments).
