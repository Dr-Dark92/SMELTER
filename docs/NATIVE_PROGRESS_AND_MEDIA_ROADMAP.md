# Native progress and media bridge

## Progress implementation — 27 October 2026

The session-bound read-only SSE monitor is implemented in
`tools/dashboard/native_progress.py`, with a native progress card and settings
panel, explicit identity binding, reconnect/gap handling, public lifecycle
metadata filtering and final workspace chart snapshots. It uses existing
runtimes and does not submit prompts. See [operation and limits](NATIVE_PROGRESS.md).
Offline HTTP-fixture tests cover the live transition and reconnect paths; a real
user-run Melty task remains the acceptance check. Generated-media ingestion
remains planned below.

## What is verified

OpenCode documents an HTTP server with `/event` and `/global/event` server-sent
event streams. Multiple clients can connect. On 2026-10-26 the running local
server's `/doc` described `text/event-stream`; a scoped, read-only connection to
`/event?directory=<exact Melty project directory>` returned `server.connected`.
No model request or chat message was submitted for this check.
[Official OpenCode server documentation](https://opencode.ai/docs/server/).

This establishes an available progress transport. A published Melty task-progress
WebSocket contract was not found in the reviewed public material. It does not
establish that Melty has no internal socket. A dedicated WebSocket relay is
technically possible, but a one-way progress mirror can first use the documented
OpenCode SSE source. No WebSocket dependency or guessed Melty protocol is installed.

The dashboard currently has authenticated job polling, file-activity cards,
registered GLB attachments, a pinned model-viewer 4.1.0 viewer, animation selection
and turntable controls. GLB upload is limited to 25 MiB; image inputs accept PNG,
JPEG and WebP. These existing views do not automatically discover native Qwen's
new files or display arbitrary generated assets inside its Melty chat.

## Progress relay design (implemented)

1. Bind an operator-selected OpenCode session ID, exact native directory and
   SMELTER workspace ID. Persist the mapping; do not infer it from recency or
   similarly named folders. Reconnect must retain that identity.
2. Consume the documented SSE stream in a bounded background worker. Accept only
   allowlisted public message/tool/status events for that session. Exclude hidden
   reasoning, environment values, tokens and unrelated sessions. Untrusted event
   text is data, never an instruction or authorization.
3. Normalize events with source session/event IDs, timestamps, sequence and
   provenance. Deduplicate reconnects, bound history and rate, and re-read session
   status after a gap. Disconnection is distinct from completion or test success.
4. Publish through the dashboard's authenticated API, initially cached polling
   or same-origin SSE. Adopt WebSocket if interactive control needs justify it;
   keep stop/control admission separate and never restart work on reconnect.
5. Tool completion can request a bounded index refresh. Final session completion
   saves a relation snapshot only for the explicitly bound workspace. No inference
   or message submission should occur while monitoring.

Final acceptance needs a real native task: visible progress without reasoning leakage,
correct session isolation, reconnect/dedup, explicit error/cancel states, and no
additional model calls. Historical native message text and generated assets are
not mirrored by this lifecycle monitor.

## Proposed generated-media contract

Register a tool-produced asset with workspace ID, approved relative path, kind,
MIME, byte length, SHA-256, producing event/proposal and task identity. Recheck
ownership, policy and hash before serving through opaque attachment IDs. Never
accept arbitrary filesystem URLs or remote HTML as a preview.

- Texture/image: show the registered PNG/JPEG/WebP with path and checksum.
- Model/animation: reuse the GLB viewer and animation controls for a validated
  registered GLB. Preserve a download link to the original asset.
- FBX, Blender scenes and DDS: require an explicit, bounded conversion recipe
  using the existing declared Blender/image tooling. Track input/output hashes;
  conversion is a separate operation, not proof of engine integration.
- Connect task → producing tool → source asset → converted asset in the relation
  graph. Label unverified conversion or engine-import relationships accordingly.

Acceptance needs texture, GLB and animated-GLB fixtures, stale-hash rejection,
unsupported-format handling and failure isolation. Native chat attachment mirroring
still needs an exposed Melty contract; dashboard previews can be implemented first.
