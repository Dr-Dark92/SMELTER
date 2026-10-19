"""SMELTER: isolated, read-only Ollama vision diagnostic.

Generates a tiny PNG with a known visual target, submits it to local Ollama,
and reports whether the model recognizes it. No SMELTER database writes.
"""
from __future__ import annotations

import argparse
import base64
import json
import struct
import sys
import time
import zlib
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ENDPOINT = "http://127.0.0.1:11434/api/chat"


def png_test_card() -> bytes:
    """Make a 96x96 RGB PNG: a red square on a white background."""
    width = height = 96
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            rows.extend((220, 20, 30) if 18 <= x < 78 and 18 <= y < 78 else (255, 255, 255))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(rows)))
            + chunk(b"IEND", b""))


def probe(model: str, timeout: int = 180) -> dict:
    image = base64.b64encode(png_test_card()).decode("ascii")
    payload = {
        "model": model,
        "stream": False,
        "think": False,
        "options": {"num_predict": 256, "temperature": 0},
        "messages": [
            {"role": "system", "content": "You are inspecting an actual attached image. Answer only from the image. If you cannot see it, say so."},
            {"role": "user", "content": "What color is the central square in this image? Answer with the color name.", "images": [image]},
        ],
    }
    started = time.monotonic()
    request = Request(ENDPOINT, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=timeout) as response:
        data = response.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError("Ollama response exceeds diagnostic limit")
    result = json.loads(data)
    message = result.get("message") or {}
    answer = message.get("content", "")
    if not isinstance(answer, str):
        raise ValueError("Ollama returned non-text content")
    return {
        "model": result.get("model", model),
        "answer": answer.strip(),
        "expected": "red",
        "recognized_red": "red" in answer.lower().split(),
        "done_reason": result.get("done_reason"),
        "prompt_eval_count": result.get("prompt_eval_count"),
        "eval_count": result.get("eval_count"),
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "image_bytes": len(png_test_card()),
        "image_attached": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only local Qwen vision smoke test")
    parser.add_argument("--model", default="qwen3.5:9b")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    try:
        result = probe(args.model, args.timeout)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "type": type(exc).__name__, "detail": str(exc)}, indent=2))
        return 2
    result["status"] = "pass" if result["recognized_red"] else "needs_investigation"
    print(json.dumps(result, indent=2))
    return 0 if result["recognized_red"] else 1


if __name__ == "__main__":
    sys.exit(main())
