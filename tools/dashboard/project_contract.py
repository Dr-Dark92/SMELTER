"""Read-only project documentation contract inspection.

Does not create or modify project files. Paths must be explicitly supplied
by the caller; never traverse the whole disk or infer permissions.
"""
from pathlib import Path

REQUIRED = ("README.md", "HANDOVER.md")
RECOMMENDED = ("docs/ARCHITECTURE.md", "docs/DECISIONS.md")
HANDOVER_HEADINGS = (
    "Current status", "Completed and verified", "In progress",
    "Known issues", "Next actions", "Validation", "Agent instructions"
)

def inspect_project(project_path):
    from python_tools import _plain_path
    from access_policy import require
    root = _plain_path(Path(project_path).expanduser()).resolve(strict=True)
    require(root,'read')
    for name in REQUIRED+RECOMMENDED:require(root/name,'read')
    if not root.is_dir():
        raise ValueError("Project path must be a directory")
    required = {name: (root / name).is_file() for name in REQUIRED}
    recommended = {name: (root / name).is_file() for name in RECOMMENDED}
    handover = root / "HANDOVER.md"
    missing_sections = []
    if handover.is_file():
        content = handover.read_text(encoding="utf-8", errors="replace").lower()
        missing_sections = [name for name in HANDOVER_HEADINGS
                            if name.lower() not in content]
    return {
        "project": str(root),
        "required": required,
        "recommended": recommended,
        "missing_handover_sections": missing_sections,
        "handover_ready": all(required.values()) and not missing_sections,
        "read_only": True,
    }
