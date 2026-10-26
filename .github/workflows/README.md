# CI

`offline-verification.yml` contains the active contracts, managed OpenCode/MCP
smokes and browser checks. The contracts job runs Python dashboard/setup/analysis
tests and Node frontend tests on Windows and Linux. Live model inference is not
part of these checks.

Push triggers cover the branch patterns declared in the workflow; pull requests
targeting `main` or `SMELTERV1` also trigger it. A direct push to
`feature/agent-stack-game-mods` does not match the current push filter, so local
verification should be retained and CI must not be claimed for that push alone.
