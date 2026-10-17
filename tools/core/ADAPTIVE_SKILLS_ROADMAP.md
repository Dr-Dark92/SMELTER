# SMELTER capability evolution roadmap

## Round 14 — Autonomous multi-file development (current)
Qwen generates three cooperating Python modules in a disposable workspace. A fixed, independently authored 10-test suite exercises module-level and integration behavior in Docker with no network, read-only mounts, non-root user, and resource limits. Failed attempts receive feedback; duplicate candidates terminate; unsuccessful files are removed. Passing files are **not** automatically merged.

## Future stage — Adaptive external skills and tools
Separate discovery from installation and execution.

1. **Discovery:** enumerate candidate skills, tools, and documentation from explicitly configured GitHub repositories, local directories, and approved registries. Never auto-fetch from arbitrary model-generated URLs.
2. **Provenance:** record source URL, commit/release digest, license, authorship, dependencies, manifest schema, and content hashes. Pin immutable revisions.
3. **Inspection:** validate declared permissions, dependency conflicts, file types, network requirements, tool API compatibility, and executable content. Treat source metadata as untrusted.
4. **Quarantine:** import into a disposable directory, not the active registry or project tree. Reject symlinks/path traversal and unsafe archive members.
5. **Sandbox testing:** exercise candidate skills against synthetic fixtures with independently authored tests; disable network by default and never mount Docker socket, secrets, project data, or host code writable.
6. **Promotion:** produce an auditable compatibility report and request explicit approval before registering a capability or granting new permissions. Support rollback and revocation.
7. **Adaptation:** if an API differs, allow Qwen to generate a *separate adapter* in the sandbox, test it against a stable contract, and promote only after approval.

**Non-goals:** unrestricted self-installation, autonomous trust decisions, unreviewed execution of remote scripts, or automatic merges into main.

Round 14 establishes multi-file generation and integration gates. External capability ingestion remains future work.
