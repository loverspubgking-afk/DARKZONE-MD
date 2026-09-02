"""
memory.py — RED-MIND v6 cross-task memory (naya feature)
=========================================================
Har chat mein agent user ko yaad rakhta hai. Server-side, sab devices pe kaam karta hai.
"""
import json
import os
import threading

MEM_FILE = "memory.json"
_lock = threading.Lock()


def _load() -> dict:
    try:
        with open(MEM_FILE) as f:
            return json.load(f)
    except Exception:
        return {"user_memory": "", "updated": None}


def get_user_memory() -> str:
    with _lock:
        return (_load().get("user_memory") or "").strip()


def set_user_memory(text: str) -> str:
    with _lock:
        data = _load()
        data["user_memory"] = (text or "").strip()[:4000]
        from datetime import datetime
        data["updated"] = datetime.now().isoformat()
        with open(MEM_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    return data["user_memory"]
