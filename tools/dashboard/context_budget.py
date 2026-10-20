"""Bound serialized prompt growth; token estimates are explicit, not tokenizer proof."""
import json


def bounded(messages, tools, context, output):
    # A conservative estimate for ordinary source/text; special model tokenizers
    # and vision token costs differ. Never claim exact model token accounting.
    budget = max(128, context-output-512)
    rows=[dict(m) for m in messages]
    def estimate():
        text=[{k:v for k,v in m.items() if k!='images'} for m in rows]
        size=len(json.dumps({'messages':text,'tools':tools or []},ensure_ascii=False).encode())
        return (size+1)//2 + 32*len(rows) + (4096 if any(m.get('images') for m in rows) else 0)
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
    return rows, {'method':'UTF-8 bytes / 2 plus message/vision reserve; estimate only',
                  'estimated_prompt_tokens':estimate(),'prompt_budget':budget,'history_messages_removed':removed}
