"""
memory.py — RED-MIND v6.1 — cross-task memory + agent self-memory
==================================================================
user_memory: user apne haath se likhta hai (Memory button)
facts: agent khud save karta hai (save_memory tool)
Dono har chat ke system prompt mein inject hote hain.
"""
import json
import threading
from datetime import datetime

MEM_FILE = "memory.json"
_lock = threading.Lock()
MAX_FACTS = 40


def _load() -> dict:
    try:
        with open(MEM_FILE) as f:
            d = json.load(f)
    except Exception:
        d = {}
    d.setdefault("user_memory", "")
    d.setdefault("facts", [])
    return d


def _save(d):
    d["updated"] = datetime.now().isoformat()
    with open(MEM_FILE, "w") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def get_user_memory() -> str:
    """System prompt ke liye poora memory text (user + agent facts)."""
    with _lock:
        d = _load()
    parts = []
    if d["user_memory"].strip():
        parts.append(d["user_memory"].strip())
    for f in d["facts"]:
        parts.append(f"• {f}")
    return "\n".join(parts)


def set_user_memory(text: str) -> str:
    with _lock:
        d = _load()
        d["user_memory"] = (text or "").strip()[:4000]
        _save(d)
    return d["user_memory"]


def add_fact(fact: str) -> str:
    """Agent ka apna memory — naya fact save (duplicate skip)."""
    fact = (fact or "").strip()[:300]
    if not fact:
        return "[khaali fact]"
    with _lock:
        d = _load()
        if fact not in d["facts"]:
            d["facts"].append(fact)
            del d["facts"][:-MAX_FACTS]
            _save(d)
            return f"Yaad rakh liya: {fact}"
        return "Ye pehle se yaad hai"


def get_all() -> dict:
    with _lock:
        d = _load()
        return {"user_memory": d["user_memory"], "facts": d["facts"]}
