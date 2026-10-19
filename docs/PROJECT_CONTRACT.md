# SMELTER Project Documentation Contract — V1

Every SMELTER-managed project should have a root `README.md` and `HANDOVER.md`.
Complex projects should also include `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`, and `docs/diagrams/`.

## README.md minimum
Project purpose; current scope; architecture overview; prerequisites; setup; usage; tests; security boundaries; documentation links.

## HANDOVER.md minimum
### Current status
Current objective, branch, and current implementation state.

### Completed and verified
Only work supported by observed code, test results, or commits.

### In progress
Partially completed work and its state.

### Known issues
Reproducible defects, risks, and unknowns.

### Next actions
Ordered, actionable steps with expected acceptance criteria.

### Validation
Commands, last observed results, environment, and date. Mark unrun checks as pending.

### Agent instructions
Project constraints, protected directories, allowed operations, approval requirements, and relevant entry points.

## Transfer protocol
1. Current agent reads the repo and checks tests/status.
2. Current agent updates HANDOVER.md after approval.
3. Next agent reads README.md, HANDOVER.md, and architecture/decision docs.
4. Next agent independently verifies critical claims before changing code.
5. The new agent resumes the listed next action and preserves existing constraints.

Never silently overwrite user project documentation or grant tool permissions through a handover file.
