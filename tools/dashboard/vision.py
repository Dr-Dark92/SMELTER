"""Validate image attachments for Ollama vision; no arbitrary filesystem reads."""
from __future__ import annotations
import base64
import binascii

MAX_IMAGE_BYTES = 2 * 1024 * 1024
ALLOWED = {"image/png", "image/jpeg", "image/webp"}

def validate_image(image: dict) -> str:
    if not isinstance(image, dict) or image.get("mime") not in ALLOWED:
        raise ValueError("Unsupported image format (PNG, JPEG, WebP only)")
    encoded = image.get("base64")
    if not isinstance(encoded, str) or not encoded or len(encoded) > ((MAX_IMAGE_BYTES + 2) // 3) * 4:
        raise ValueError("Image exceeds 2 MiB limit")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid base64 image") from exc
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("Image exceeds 2 MiB limit")
    mime = image["mime"]
    valid = (mime == "image/png" and raw.startswith(b"\\x89PNG\\r\\n\\x1a\\n")) or (
        mime == "image/jpeg" and raw.startswith(b"\\xff\\xd8\\xff")) or (
        mime == "image/webp" and raw.startswith(b"RIFF") and raw[8:12] == b"WEBP")
    if not valid:
        raise ValueError("Image signature does not match declared format")
    return encoded
