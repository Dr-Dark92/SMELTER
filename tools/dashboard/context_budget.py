"""Bound serialized prompt growth; token estimates are explicit, not tokenizer proof."""
import json
import math
import re

# One JSON escape, a long letter/digit run (hash, base64, identifier), a word,
# one digit, a non-ASCII run, whitespace, or one ASCII punctuation character.
_PIECES = re.compile(r'\\u[0-9a-fA-F]{4}|\\.|[A-Za-z0-9]{17,}|[A-Za-z]+|[0-9]|[^\x00-\x7f]+|\s+|[^A-Za-z0-9\s]')


def estimate_tokens(text):
    """Conservative token estimate by character class.

    Calibrated against qwen3.5:4b prompt_eval_count on 2026-10-24: English
    1.13-1.28x, code 1.36-1.75x, JSON 1.18-1.56x the real count, and at or above
    it for CJK, Arabic, emoji, base64 and hex hashes. The previous bytes/2 rule
    was 1.8-2.4x on text and code but under-counted dense JSON (0.87x) and hashes.
    """
    total = 0.0
    for piece in _PIECES.findall(text):
        first = piece[0]
        if first == '\\':
            total += 1
        elif len(piece) > 16 and piece.isascii() and piece.isalnum():
            total += len(piece) + 1
        elif first.isascii() and first.isalpha():
            total += 1 if len(piece) <= 8 else math.ceil(len(piece) / 4)
        elif first.isspace():
            total += 0 if piece == ' ' else math.ceil(len(piece) / 4)
        elif not first.isascii():
            total += len(piece.encode()) / 1.6
        else:
            total += 1
    return math.ceil(total)


def bounded(messages, tools, context, output):
    # A conservative estimate for ordinary source/text; special model tokenizers
    # and vision token costs differ. Never claim exact model token accounting.
    budget = max(128, context-output-512)
    rows=[dict(m) for m in messages]
    def estimate():
        text=[{k:v for k,v in m.items() if k!='images'} for m in rows]
        serialized=json.dumps({'messages':text,'tools':tools or []},ensure_ascii=False)
        return estimate_tokens(serialized) + 32*len(rows) + (4096 if any(m.get('images') for m in rows) else 0)
    removed=0
    # Remove complete earlier user turns, never the current turn or tool-result
    # protocol groups belonging to it. Oversized current work fails explicitly.
    while estimate()>budget:
        users=[i for i,m in enumerate(rows) if m.get('role')=='user']
        if len(users)<2:
            raise ValueError('Estimated prompt budget exceeded. Use smaller file pages/fewer skills or increase context; completed actions remain recorded.')
        start,end=users[0],users[1]
        removed+=end-start
        del rows[start:end]
    return rows, {'method':'Character-class estimate calibrated on Qwen 3.5 plus message/vision reserve; estimate only',
                  'estimated_prompt_tokens':estimate(),'prompt_budget':budget,'history_messages_removed':removed}
