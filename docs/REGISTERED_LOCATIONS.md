# Registered locations

Open Settings → Workspaces & Access. Locations appear in a searchable table with selection checkboxes, folder paths, enabled status, Read / Write / Execute flags and permitted operations.

| Control | Result |
| --- | --- |
| + Add | Open the location editor; Browse navigates folders on the machine running SMELTER |
| Remove | Remove selected registrations from the draft; folders and files are not deleted |
| Enable / Disable | Change selected draft rows |
| Apply | Validate and atomically save the draft for new tasks |
| Revert | Discard the draft and reload the applied policy |

New locations start enabled and read-only. Click a location name to edit its folder, flags, fixed operations or relative exclusions. Execute requires at least one registered operation. Disabled rows are ignored: to deny a nested subtree within a broader location, keep the nested row enabled with all permissions off.

Drafts survive navigation between Settings sections. They do not affect next-task folder choices until Apply succeeds. Active tasks retain their admitted policy. Another window changing the policy causes a revision conflict; reload with Revert before editing again. The API accepts optional `expected_revision` for compatibility; the GUI always supplies it and the backend compares it inside a SQLite write transaction.

## Folder browser boundary

`GET /api/location-browser` requires dashboard authentication. This operator interface lists directory names only, including outside registered scopes so new locations can be selected. It does not grant model access, upload files, read file contents, run a shell or expose a new MCP/model tool. Navigation uses Home, current checkout, registered locations and fixed Windows drives or Linux filesystem shortcuts. Manual absolute path entry remains available.

Hidden folders are opt-in. Each response visits at most 3,000 entries and returns at most 200 directories, with a truncation notice. Links/reparse points, network paths and traversal are rejected. Whole drives/filesystem roots may be browsed but cannot be selected for a grant; policy validation independently rejects whole-root grants.

## Offline verification

The temporary GUI fixture includes an Assets tree with Characters and Environments folders and a file that must not appear in the picker. Browser checks cover Add/Browse, staged permissions, bulk Disable, Apply/Revert, navigation draft retention, concurrent-window conflict, Remove, root selection and desktop/mobile overflow. Existing skills/import/attachment and retention/reconnect/Stop flows are regression checked separately. No Qwen service is used. The Windows native drive-enumeration branch still requires a rig smoke test.

Run from the repository root:

```fish
python tools/analysis/offline_gui_fixture.py
```

Open the authenticated URL printed by that command. The fixture uses disposable state and synthetic replies; stop it with Ctrl+C.
