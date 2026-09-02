"""
omni.py — OmniRoute client (user ka apna gateway, OpenAI-compatible)
===================================================================
"""
import json
import os

import httpx

OMNI_LINK_URL = "https://raw.githubusercontent.com/loverspubgking-afk/DARKZONE-MD/main/omni-link.txt"
KEYS_FILE = "api_keys.json"


def base_url() -> str:
    ov = os.environ.get("OMNI_URL_OVERRIDE", "").strip()
    if ov:
        return ov.rstrip("/")
    try:
        t = httpx.get(OMNI_LINK_URL, timeout=15).text.strip()
        if t.startswith("https://") or t.startswith("http://"):
            return t.rstrip("/")
    except Exception:
        pass
    return "http://localhost:20128"


def _key(provider=None) -> str:
    try:
        ks = json.load(open(KEYS_FILE))
        return ks.get(provider) or (list(ks.values())[0] if ks else "")
    except Exception:
        return ""


def chat(user_input, history=None, *, system_prompt=None, model="auto",
         provider=None, timeout=300.0, base=None):
    """OmniRoute chat. model='auto' gateway khud best chunta hai."""
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
    headers = {"Content-Type": "application/json"}
    k = _key(provider)
    if k:
        headers["Authorization"] = f"Bearer {k}"
    r = httpx.post(f"{base or base_url()}/v1/chat/completions",
                   json={"model": model or "auto", "messages": msgs},
                   headers=headers, timeout=timeout)
    r.raise_for_status()
    d = r.json()
    return (d.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
