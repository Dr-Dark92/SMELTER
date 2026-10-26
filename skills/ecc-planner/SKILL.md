---
name: ecc-planner
description: Plan a coding feature or substantial repair with exact source locations, small milestones, dependencies and executable acceptance criteria before implementation.
---
# Plan a bounded implementation

Read the current task, authoritative workspace and relevant callers/tests. Preserve the selected host game and requested behavior. Distinguish implemented code, proposed design and observed runtime evidence.

Write a short plan containing affected paths, interface/dependency decisions, small milestones and the test that accepts each milestone. Address missing runtime APIs explicitly. Define observable outcomes and failure cases; isolate engine access behind an adapter so controller logic can be tested offline when appropriate. Avoid changing host engines to accommodate a tooling limitation.

Stop planning when the next concrete edit and validation are clear. Save necessary state in an ordinary project document or permitted project-memory note before a context handoff. Execute within the existing authorization instead of repeatedly asking about routine implementation choices. Planning does not grant a new tool, game installation or publishing action.

Adapted from ECC's [planner agent](references/upstream.md). This is a Qwen instruction profile; no Claude model, separate worker or delegation is registered.
