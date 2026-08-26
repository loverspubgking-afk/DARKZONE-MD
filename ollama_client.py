"""
ollama_client.py  —  Ollama backend (Colab GPU / local PC / VPS)
================================================================
Kisi bhi Ollama server se baat karta hai (default: localhost:11434).
Colab tunnel link bhi de sakte ho: https://xxx.trycloudflare.com
"""

import os
import httpx

# Kaggle notebook is file mein har baar fresh link upload karta hai
GITHUB_LINK_URL = "https://raw.githubusercontent.com/loverspubgking-afk/DARKZONE-MD/main/tunnel-link.txt"


def _resolve_url(ollama_url: str | None) -> str:
    """Agar URL khali/'auto' hai to GitHub se latest tunnel link uthao."""
    u = (ollama_url or "").strip()
    if u and u.lower() != "auto":
        return u.rstrip("/")
    # auto: GitHub se fresh link
    try:
        r = httpx.get(GITHUB_LINK_URL, timeout=15)
        link = r.text.strip()
        if link.startswith("http"):
            return link.rstrip("/")
    except Exception:
        pass
    return "http://localhost:11434"


def chat(
    user_input: str,
    history: list[dict] | None = None,
    *,
    system_prompt: str | None = None,
    ollama_url: str | None = None,
    model: str | None = None,
    timeout: float = 300.0,
) -> str:
    """Ollama /api/chat se plain text jawab."""
    base = _resolve_url(ollama_url)
    mdl = model or os.environ.get("OLLAMA_MODEL", "huihui_ai/dolphin3-abliterated")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if history:
        for m in history:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "tool":
                messages.append({"role": "assistant", "content": f"[TOOL_RESULT]\n{content}"})
            else:
                messages.append({"role": role if role in ("user", "assistant") else "user",
                                 "content": content})

    messages.append({"role": "user", "content": user_input})

    payload = {
        "model": mdl,
        "messages": messages,
        "stream": False,
        "options": {"num_ctx": 8192, "temperature": 0.7},
    }

    import time as _time
    last_err = ""
    for attempt in range(3):
        try:
            r = httpx.post(f"{base}/api/chat", json=payload, timeout=timeout)
            if r.status_code in (502, 503, 504, 522, 524, 520):
                last_err = f"HTTP {r.status_code} (tunnel/GPU busy)"
                _time.sleep(6 * (attempt + 1))
                continue
            r.raise_for_status()
            data = r.json()
            return (data.get("message", {}).get("content", "") or "").strip()
        except httpx.HTTPStatusError as e:
            return f"[Ollama error {e.response.status_code}: {e.response.text[:200]}]"
        except Exception as e:
            last_err = str(e)
            _time.sleep(6 * (attempt + 1))
    return f"[Ollama connection error: {last_err} — server/tunnel busy ya off hai, dobara try karo]"


if __name__ == "__main__":
    print(chat("Salam! Ek line mein apna intro de."))
