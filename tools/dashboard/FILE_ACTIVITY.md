# File activity in chat

Approved frontend workspace reads and CSS replacements produce one card per
file and source/destination area. Reading six distinct files produces six
cards. A card contains an expandable original file snapshot and a read-only
code box below it. Repeated operations update the existing card.

The original is captured before the first file operation in the turn. Drafts
show the actual `new_text` CSS replacement received in a tool call. After a
successful write, the lower box shows the updated file read from disk. Failed
edits keep the failed proposal separate from the last confirmed saved version.
Reads do not claim a write. Interrupted proposals are unconfirmed.

The job status response includes `files`; the existing GUI poll displays them
while a request runs and when reconnecting after a refresh. Completed file
cards are stored in the existing message execution JSON, so no schema migration
is required. Earlier messages without snapshots cannot reconstruct old files.

File text is rendered as text, never HTML. Previews are bounded to 12 cards
and 128 Ki characters per original/updated file; truncation is labeled. No new
filesystem or editing permissions are granted. Only frontend files
already exposed by built-in workspace tools are observed. The OpenCode bridge
uses the same controller tracker for those calls, including actual saved CSS.
OpenCode native reads remain reported activity without reconstructed snapshots. External MCP servers
need an explicit file-event adapter before their edits can be shown reliably.

Updates follow real model/tool events. Ollama may deliver complete tool
arguments together, so a CSS draft can appear as one block rather than token
by token. No typing animation is fabricated. The model's plain-text narrative
is not interpreted as file edits, and generic code editing is not introduced.

Validation: Python tests cover six-file tracking, real saved writes, rejected
edits, original retention, cancellation, bounds, access scopes and persistence
in a real temporary chat database. JavaScript tests cover expandable cards,
stable updates and inert code rendering. Browser fixtures exercise the live
job polling and completed history on desktop and mobile without invoking AI.
