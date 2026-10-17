# Round 13 — Autonomous Qwen developer

Requires Docker Desktop (Linux containers), a locally available `python:3.12-alpine` image, Python 3 and Ollama with `qwen3.5:9b`.

Prepare the image once with `docker pull python:3.12-alpine`.

Run:

```powershell
cd C:\SMELTER
py -3 tools\core\test_autonomous_developer_round13.py
py -3 tools\diagnostics\upload_reports.py --latest
```

Qwen writes a single synthetic game-recon module in a disposable workspace. Fixed tests run inside a network-disabled Docker container with a read-only filesystem, restricted resources and no repository or Docker socket mount. Failures trigger feedback and retries; unsuccessful generated code is deleted. Logs and JSON reports remain in `workspace/smelter-round13`. Successful code is not automatically merged.

This experiment depends on Docker's security boundary; it is not a formal guarantee against container escape. No host-side execution fallback is provided.
