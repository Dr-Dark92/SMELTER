---
name: ecc-cpp-standards
description: Implement or review native C++ mod code with explicit ownership, safe interfaces, resource lifetime, ABI constraints and the project's supported compiler standard.
---
# C++ mod implementation

Confirm the existing compiler, target ABI, language standard and required game SDK before editing. Use the project's supported standard rather than adopting a newer one because an example uses it. Favor explicit ownership, RAII, type-safe interfaces and bounded access. Retain necessary engine ABI layouts, calling conventions and packing; validate sizes and offsets independently.

Separate portable serialization/controller logic from Windows and game hooks. Avoid new engine globals in portable tests. Test units, coordinate transforms, stale/truncated records and error paths where relevant. Do not infer native API availability from an ASI loader or a successful compile.

Use supported SMELTER patch/test/build operations. `cpp` runs portable C++17 test programs; `build_native_mod` creates Windows artifacts without executing them. A compiler dependency, linter or sanitizer named in upstream is not automatically installed.

Adapted from [ECC C++ standards](references/upstream.md). Read individual guideline sections only when needed; game ABI constraints can require deliberate exceptions to general style guidance.
