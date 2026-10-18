"""Safe, tool-free local chat through Ollama's loopback API.

No OpenCode agent is invoked: the model receives only conversation text.
No filesystem or shell tools are exposed.
"""
from __future__ import annotations
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from chats import read_chat, _db
from vision import validate_image
from contextlib import closing
import sqlite3

ENDPOINT = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen3.5:9b"
MAX_RESPONSE = 128 * 1024

def ask(root, conversation_id, prompt, opener=urlopen, image=None):
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 1800:
        raise ValueError("Prompt must be 1–1800 characters")
    chat = read_chat(root, conversation_id)
    messages = [{"role":"system","content":"You are SMELTER's local assistant. You have no access to tools, files, shell, or GitHub. Do not claim to execute actions."}]
    for m in chat["messages"][-24:]:
        if m["role"] in ("user", "assistant"):
            messages.append({"role":m["role"],"content":m["content"]})
    user_message = {"role":"user","content":prompt.strip()}
    if image is not None:
        user_message["images"] = [validate_image(image)]
    messages.append(user_message)
    payload = json.dumps({"model":MODEL,"messages":messages,"stream":False,"options":{"num_predict":1024}}).encode()
    request = Request(ENDPOINT, data=payload, method="POST", headers={"Content-Type":"application/json"})
    try:
        with opener(request, timeout=120) as response:
            raw = response.read(MAX_RESPONSE + 1)
    except (URLError, HTTPError, TimeoutError, OSError) as exc:
        raise ValueError("Local Ollama unavailable: " + type(exc).__name__) from exc
    if len(raw) > MAX_RESPONSE:
        raise ValueError("Model response too large")
    try:
        result = json.loads(raw)
        answer = result["message"]["content"]
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError("Invalid Ollama response") from exc
    if not isinstance(answer, str) or not answer.strip() or len(answer) > 64000:
        raise ValueError("Empty or invalid model answer")
    # Store the prompt and answer atomically, only after inference succeeds.
    with closing(sqlite3.connect(_db(root), timeout=5)) as conn, conn:
        conn.execute("PRAGMA foreign_keys=ON")
        if conn.execute("SELECT 1 FROM conversations WHERE id=?", (conversation_id,)).fetchone() is None:
            raise ValueError("Conversation no longer exists")
        conn.execute("INSERT INTO messages(conversation_id,role,content) VALUES(?,'user',?)", (conversation_id,prompt.strip()))
        conn.execute("INSERT INTO messages(conversation_id,role,content) VALUES(?,'assistant',?)", (conversation_id,answer))
    return {"reply":answer,"model":MODEL,"stored":True,"tools_executed":False,"image_analyzed":image is not None}
