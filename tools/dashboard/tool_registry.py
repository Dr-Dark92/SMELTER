"""Shared tool definitions and fixed dispatch for direct and MCP transports."""
MAX_DEPTH = 8


def schemas(grants):
    tools = []
    if grants.get("rea_analysis"):
        tools.append({"type": "function", "function": {
            "name": "rea_capabilities", "description": "Run the connected local REA CLI capabilities command. Reports actual REA capabilities and limitations; does not install providers or execute a target.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}})
        tools.append({"type": "function", "function": {
            "name": "rea_inspect_pe_resources", "description": "Use REA to statically inspect PE resource metadata, locations and hashes in an approved .exe/.dll. Requires relative_path within the approved REA folder; use forward slashes. Reads up to 64 MiB. Does not execute the target, decompile code, extract assets, or parse .oppc containers. Retains original REA JSON and returns a bounded preview.",
            "parameters": {"type": "object", "properties": {"relative_path": {"type": "string"}},
                           "required": ["relative_path"], "additionalProperties": False}}})
    if grants["inventory_root"]:
        tools.append({"type": "function", "function": {
            "name": "inventory_directory",
            "description": "Read-only, bounded file metadata inventory inside the user-approved folder. No file contents are read. Use relative_path='.' for the approved folder. scan_complete describes traversal; entries_truncated describes the returned sample. A short sample does NOT imply the scan stopped. Report exact byte sizes; do not infer asset contents from names/extensions.",
            "parameters": {"type": "object", "properties": {
                "relative_path": {"type": "string"},
                "max_depth": {"type": "integer", "minimum": 0, "maximum": MAX_DEPTH}},
                "required": ["relative_path"], "additionalProperties": False}}})
    if grants["write_diagnostics"]:
        tools.append({"type": "function", "function": {
            "name": "write_diagnostic_markdown",
            "description": "Create a new UTF-8 Markdown handover/report in this checkout's diagnostics/ only. filename must be a plain .md basename. Existing files get a numeric suffix, never overwritten. Return includes verified path, byte count and SHA-256. No scripts or dependencies are run.",
            "parameters": {"type": "object", "properties": {
                "filename": {"type": "string"}, "content": {"type": "string"}},
                "required": ["filename", "content"], "additionalProperties": False}}})
    return tools



def execute_builtin(root, grants, name, arguments):
    from python_tools import inventory, write_markdown
    if name == 'inventory_directory':
        return inventory(grants, arguments)
    if name == 'write_diagnostic_markdown':
        return write_markdown(root, grants, arguments)
    if name in {'rea_capabilities', 'rea_inspect_pe_resources'}:
        from rea_connection import run_rea
        return run_rea(root, grants, name, arguments)
    raise ValueError('Unknown registered tool')
