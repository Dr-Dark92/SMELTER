"""Live end-to-end vision probe: SMELTER chat -> Ollama -> response.

Run only on the local workstation with Ollama running. Uses a temporary
SQLite database outside the checkout and never modifies projects/.
"""
import base64
import hashlib
import json
import re
import tempfile
from pathlib import Path
from urllib.request import urlopen

from chat_inference import ask
from chats import create_chat, read_chat
from database import select_database
from vision_probe import png_test_card


def main():
    png = png_test_card()
    encoded = base64.b64encode(png).decode("ascii")
    image_hash = hashlib.sha256(png).hexdigest()
    observed = []

    def audited_opener(request, timeout):
        payload = json.loads(request.data)
        user_message = payload["messages"][-1]
        attachments = user_message.get("images", [])
        hashes = [hashlib.sha256(base64.b64decode(item, validate=True)).hexdigest()
                  for item in attachments]
        observed.append({
            "url": request.full_url,
            "model": payload.get("model"),
            "think": payload.get("think"),
            "image_count": len(attachments),
            "image_hash_verified": image_hash in hashes,
        })
        return urlopen(request, timeout=timeout)

    with tempfile.TemporaryDirectory(prefix="smelter-vision-") as temp:
        base = Path(temp)
        root = base / "checkout"
        (root / ".smelter").mkdir(parents=True)
        select_database(root, str(base / "data"))
        conversation_id = create_chat(root, "Vision probe")["id"]
        try:
            result = ask(
                root, conversation_id,
                "What color is the central square in the attached image? Answer with one color word.",
                opener=audited_opener,
                image={"mime": "image/png", "base64": encoded},
            )
            answer = result["reply"]
            recognized = "red" in re.findall("[a-z]+", answer.lower())
            stored = len(read_chat(root, conversation_id)["messages"]) == 2
            delivered = bool(observed) and all(item["image_hash_verified"] for item in observed)
            status = "pass" if recognized and delivered and stored else "needs_investigation"
            report = {
                "status": status,
                "image_sha256": image_hash,
                "outgoing_requests": observed,
                "answer": answer,
                "recognized_red": recognized,
                "conversation_stored": stored,
                "model": result["model"],
                "tools_executed": result["tools_executed"],
            }
        except (ValueError, OSError, TimeoutError) as exc:
            report = {"status": "error", "error_type": type(exc).__name__,
                      "detail": str(exc), "outgoing_requests": observed}
            status = "error"
    print(json.dumps(report, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
