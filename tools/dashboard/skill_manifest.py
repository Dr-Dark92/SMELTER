"""Conservative SKILL.md metadata extraction for bundled and third-party skills."""
from __future__ import annotations
import re


def parse_skill_manifest(content):
    if not isinstance(content, str) or not content.strip():
        return {"valid": False, "name": "", "description": "", "format": "invalid"}
    text = content.lstrip("\ufeff")
    meta = {}
    format_name = "markdown"
    if text.startswith("---\n") or text.startswith("---\r\n"):
        match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
        if not match or len(match.group(1)) > 8192:
            return {"valid": False, "name": "", "description": "", "format": "invalid"}
        format_name = "frontmatter"
        for line in match.group(1).splitlines():
            m = re.match(r"^([a-zA-Z_-]+):\s*(.*)$", line)
            if m and m.group(1).lower() in ("name", "description"):
                value = m.group(2).strip().strip("\"'")
                if value and value not in ("|", ">"):
                    meta[m.group(1).lower()] = value
        text = text[match.end():]
    heading = re.search(r"^#\s+(.+?)\s*$", text, re.M)
    purpose = re.search(r"^##\s+Purpose\s*$\n+([^#\n][^\n]*)", text, re.M | re.I)
    name = (meta.get("name") or (heading.group(1).strip() if heading else ""))[:120]
    description = (meta.get("description") or (purpose.group(1).strip() if purpose else ""))[:300]
    # A heading plus descriptive body is common in third-party skill repositories.
    if not description and heading:
        after = text[heading.end():]
        paragraph = re.search(r"(?m)^(?!\s*(?:#|>|-|\*|`))([A-Za-z][^\n]{14,})$", after)
        if paragraph:
            description = paragraph.group(1).strip()[:300]
    return {"valid": bool(name and description), "name": name, "description": description, "format": format_name}
