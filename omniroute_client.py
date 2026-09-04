"""OmniRoute client — FREE models gateway (OpenAI-compatible)."""
import os, json, httpx
GITHUB_OMNI = "https://raw.githubusercontent.com/loverspubgking-afk/DARKZONE-MD/main/omni-link.txt"
KEYS_FILE = "api_keys.json"

def _base(url=None):
    if url: return url.rstrip("/")
    # 1) pehle localhost (aksar app aur OmniRoute ek hi server par hote hain)
    try:
        r = httpx.get("http://localhost:20128/v1/models", timeout=4)
        if r.status_code == 200: return "http://localhost:20128"
    except Exception: pass
    # 2) GitHub tunnel links (naya repo pehle, purana fallback)
    for gh in ["https://raw.githubusercontent.com/loverspubgking-afk/redmind-links/main/omni-link.txt",
               "https://raw.githubusercontent.com/loverspubgking-afk/DARKZONE-MD/main/omni-link.txt"]:
        try:
            t = httpx.get(gh, timeout=8).text.strip()
            if t.startswith("https://"): return t.rstrip("/")
        except Exception: pass
    return "http://localhost:20128"

def _key(provider=None):
    try:
        ks = json.load(open(KEYS_FILE))
        return ks.get(provider) or (list(ks.values())[0] if ks else "")
    except Exception: return ""

def chat(user_input, history=None, *, system_prompt=None, omni_url=None, model="auto", provider=None, timeout=300.0):
    msgs = []
    if system_prompt: msgs.append({"role": "system", "content": system_prompt})
    for m in (history or []):
        r = m.get("role", "user")
        if r == "tool": msgs.append({"role": "assistant", "content": f"[TOOL_RESULT]\n{m.get('content','')}"})
        else: msgs.append({"role": r if r in ("user","assistant") else "user", "content": m.get("content","")})
    msgs.append({"role": "user", "content": user_input})
    headers = {"Content-Type": "application/json"}
    k = _key(provider)
    if k: headers["Authorization"] = f"Bearer {k}"
    try:
        r = httpx.post(f"{_base(omni_url)}/v1/chat/completions",
                       json={"model": model or "auto", "messages": msgs}, headers=headers, timeout=timeout)
        r.raise_for_status()
        d = r.json()
        return (d.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
    except Exception as e:
        return f"[OmniRoute error: {e}]"
