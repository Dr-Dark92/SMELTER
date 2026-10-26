---
name: ecc-test-review
description: Review whether tests execute changed production behavior, catch real failures and cover important boundaries; use when a green result may conceal missing module or integration coverage.
---
# Review test quality

Map changed functions and interfaces to actual test invocations. Trace imports to the canonical implementation and confirm test discovery. Compilation, export presence and no-throw checks have narrower scope than behavior assertions.

Look for tests that duplicate implementation math, print failures without failing the process, silently skip unavailable modules, remove the failing test or mock the controller itself. Fake only the external engine/services needed to execute real production logic. Check both expected outcomes and rejected inputs, cooldown boundaries, target loss and error propagation where relevant.

Propose focused regressions for concrete gaps. When authorized and supported, use a disposable copy to verify that a small known fault makes the relevant test fail; never damage the active coding copy for this check. Do not claim coverage percentages without measurement.

Report each important gap with exact path, behavior it fails to protect, and a minimal test recommendation. A passing runner receipt proves execution success, not adequate test quality.

Adapted from ECC's [PR test analyzer](references/upstream.md). No PR or independent review agent is created by loading this profile.
