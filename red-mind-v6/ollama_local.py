"""
ollama_local.py — Ollama 14B route (Kaggle GPU, uncensored Neural 14B)
======================================================================
"""
import json
import os

import httpx

LINK_URL = "https://raw.githubusercontent.com/loverspubgking-afk/DARKZONE-MD/main/tunnel-link.txt"
MODEL_URL = "https://raw.githubusercontent.com/loverspubgking-afk/DARKZONE-MD/main/model-name.txt"
CONFIG_FILE = "config.json"


def _model() -> str:
    try:
        return json.load(open(CONFIG_FILE)).get("ollama_model", "huihui_ai/qwen3-abliterated:14b")
    except Exception:
        return "huihui_ai/qwen3-abliterated:14b"


def _url(base_url=None) -> str:
    ov = os.environ.get("OLLAMA_URL_OVERRIDE", "").strip()
    if ov:
        return ov.rstrip("/")
    if base_url and base_url.strip() and base_url.strip().lower() != "auto":
        return base_url.strip().rstrip("/")
    try:
        t = httpx.get(LINK_URL, timeout=12).text.strip()
        if t.startswith("http"):
            return t.rstrip("/")
    except Exception:
        pass
    return "http://127.0.0.1:11434"


def chat(user_input, history=None, *, system_prompt=None, base_url=None, timeout=280.0):
    """Ollama /api/chat — streaming nahi, simple."""
    url = _url(base_url)
    msgs = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    for m in (history or []):
        r = m.get("role", "user")
        if r == "tool":
            msgs.append({"role": "assistant", "content": f"[TOOL_RESULT]\n{m.get('content', '')}"})
        else:
            msgs.append({"role": r if r in ("user", "assistant") else "user",
                         "content": m.get("content", "")})
    msgs.append({"role": "user", "content": user_input})
    r = httpx.post(f"{url}/api/chat",
                   json={"model": _model(), "messages": msgs, "stream": False,
                         "options": {"num_ctx": 8192}},
                   timeout=timeout)
    r.raise_for_status()
    d = r.json()
    return (d.get("message", {}).get("content") or "").strip()
