"""
ollama_client.py  —  Ollama backend (Colab GPU / local PC / VPS)
================================================================
Kisi bhi Ollama server se baat karta hai (default: localhost:11434).
Colab tunnel link bhi de sakte ho: https://xxx.trycloudflare.com
"""

import os
import httpx


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
    base = (ollama_url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
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

    try:
        r = httpx.post(f"{base}/api/chat", json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return (data.get("message", {}).get("content", "") or "").strip()
    except httpx.HTTPStatusError as e:
        return f"[Ollama error {e.response.status_code}: {e.response.text[:200]}]"
    except Exception as e:
        return f"[Ollama connection error: {e} — kya server/tunnel on hai?]"


if __name__ == "__main__":
    print(chat("Salam! Ek line mein apna intro de."))
