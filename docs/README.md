# cAIman Terminal documentation

Updated for assistive alpha on **2026-09-14**. Alpha has no latency gate;
correctness, useful coverage and explanation quality still require evidence.

## Current guides

- [Workspace and quick starts](../README.md)
- [Terminal app](../terminal/README.md)
- [LLM research](../llm/README.md)
- [Research scope and contracts](research/README.md)
- [Local artifacts](../artifacts/README.md)
- [Runtime harness](../terminal/tests/README.md)
- [Security hardening, verification and remaining limits](terminal/13_Security_Hardening.md)
- [Alpha policy, executable review matrix and acceptance evidence](terminal/14_Alpha_Conformance.md)

## Terminal product and implementation

1. [Project overview](terminal/01_Project_Overview.md)
2. [Product requirements](terminal/02_Product_PRD.md) — includes acceptance targets, not a claim that every requirement is implemented
3. [Architecture and provider boundaries](terminal/03_Architecture_Overview.md)
4. [Data structures and storage](terminal/04_Data_Structure_and_Storage.md)
5. [Development plan](terminal/05_Agent_Development_Plan.md)
6. [Testing](terminal/06_Testing_Plan.md)
7. [Decision log](terminal/07_Decision_Log.md) — dated historical decisions are retained
8. [Module contracts](terminal/08_Module_Service_Specifications.md)
9. [Operations](terminal/09_Operational_and_Support_Overview.md)
10. [User guide](terminal/10_User_and_Admin_Guides.md)
11. [Known limitations](terminal/11_Open_Issues_Risks_and_Backlog.md)
12. [Current status and history](terminal/12_Project_Status.md)
13. [Security hardening](terminal/13_Security_Hardening.md)
14. [Alpha conformance and release gates](terminal/14_Alpha_Conformance.md)
15. [Performance/correctness review, dispositions and measurements](terminal/15_Performance_Correctness_Review.md)
16. [Optional GPU acceleration and CPU fallback](terminal/16_GPU_Acceleration.md)

## Development guidance and archive

Repository process patterns, roles and skills are under [development/](development/).
The workspace check entry point is [scripts/check.sh](../scripts/check.sh).
The generic [document pattern](development/patterns/standard_project_docs.md) is a
template: this workspace uses the root README instead of a duplicate `00_README.md`,
and keeps numbered product documents under `docs/terminal/`.
The [original research brief](research/archive/harness-design.md) is archived; its
statement that the desktop app did not yet exist describes that earlier stage.

Unless a guide says otherwise, Cargo/app commands run from the repository root.
Python research commands run from `llm/`. No documentation path assumes the local
checkout directory has been renamed.
