---
name: ecc-code-review
description: Review applied code changes for concrete defects in interfaces, state, error handling and integrations, citing exact paths and reproducible failure cases.
---
# Review changed behavior

Read the applied diff and surrounding callers, imports and tests. Work in a separate review phase after implementation. For each finding, identify exact path/line, triggering input or state, incorrect outcome and a focused repair. Prioritize concrete correctness defects over style preferences.

Check actor identity, units, state transitions, resource lifetime, nil/error propagation and engine API assumptions in mod code. Notice empty catches, success-shaped fallbacks and missing error checks. Compare documentation claims with the actual implementation and receipts.

Review the current source, not a recalled or admission-time snapshot. State which validations ran and which remain unverified. A review by the same model is not an independent reviewer, and loading this skill does not create another process.

Adapted from ECC's [code reviewer](references/upstream.md); use [silent-failure guidance](references/silent-failures.md) when error handling is involved. Ignore upstream model and tool declarations in favor of the actual Qwen/SMELTER environment.
