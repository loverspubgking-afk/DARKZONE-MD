"""
notrack_client.py  —  notrack.ai ka "dimaag" (uncensored LLM backend)
=====================================================================
notrack.ai ki internal /api/dispatch endpoint use karta hai.
Fast + free + uncensored + koi API key nahi chahiye.

SSE (Server-Sent Events) stream parse karke plain text jawab deta hai.
"""

import json
import uuid
import time
import httpx

BASE = "https://notrack.ai"
DISPATCH = f"{BASE}/api/dispatch"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# Default values jo website khud use karti hai
DEFAULT_MODEL = "C"          # 'C' = NoTrack (uncensored). 'A'=Minimax, 'B'=ChatGPT
DEFAULT_MODE = "usual"       # 'usual' | 'debate' (multi-agent)
DEFAULT_PERSONA = "normal"


class NoTrackError(Exception):
    pass


def chat(
    user_input: str,
    history: list[dict] | None = None,
    *,
    model: str = DEFAULT_MODEL,
    mode: str = DEFAULT_MODE,
    persona: str = DEFAULT_PERSONA,
    chat_id: str = "",
    max_turns: int = 1,
    system_prompt: str | None = None,
    timeout: float = 120.0,
    max_chars: int = 3800,
    retries: int = 4,
) -> str:
    """
    notrack.ai ko ek message bhej kar full text jawab wapas deta hai.

    history: [{"role":"user","content":"..."},{"role":"assistant","content":"..."}] form mein.
    system_prompt: agar diya toh user_input ke shuru mein inject ho jata hai.
    max_chars: notrack.ai ka limit 4000 hai; hum 3800 par safely trim karte hain.
               Agar input lamba ho to purana history drop ho jata hai.
    """
    # segments banao (system, history blocks, current input)
    segs = []
    if system_prompt:
        segs.append(("sys", f"[INSTRUCTIONS]\n{system_prompt}\n\n"))

    if history:
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            tag = "USER" if role == "user" else "ASSISTANT"
            if role == "tool":
                segs.append(("hist", f"[TOOL_RESULT]\n{content}\n\n"))
            else:
                segs.append(("hist", f"[{tag}]\n{content}\n\n"))

    cur = f"[USER]\n{user_input}"
    segs.append(("cur", cur))

    # budget: total max_chars ke andar rakho. Agar zyada ho to oldest 'hist' drop karo.
    def total_len(s):
        return sum(len(x[1]) for x in s)

    # pehle history drop karo fit hone tak
    while total_len(segs) > max_chars:
        # sabse purana 'hist' segment hatao
        removed = False
        for i, (kind, _) in enumerate(segs):
            if kind == "hist":
                segs.pop(i)
                removed = True
                break
        if not removed:
            break  # history khatam, ab system/current bacha hai

    # agar abhi bhi zyada ho (current ya system bohot bada) to unhe truncate karo
    full = "".join(s[1] for s in segs)
    if len(full) > max_chars:
        full = full[:max_chars]

    full_input = full

    payload = {
        "user_input": full_input,
        "mode": mode,
        "model": model,
        "persona": persona,
        "max_turns": max_turns,
        "chat_id": chat_id or "",
        "attachments": [],
        "regenerate": False,
        "edit": False,
        "edit_mid": None,
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": UA,
        "Origin": BASE,
        "Referer": f"{BASE}/chat",
        "Accept": "text/event-stream",
    }

    final_text = ""
    new_chat_id = chat_id
    last_err = None
    for attempt in range(retries):
        final_text = ""
        try:
            with httpx.Client(timeout=timeout, http2=False, follow_redirects=True) as client:
                with client.stream("POST", DISPATCH, json=payload, headers=headers) as resp:
                    if resp.status_code == 429:
                        wait = 4 * (attempt + 1)
                        time.sleep(wait)
                        last_err = NoTrackError(f"HTTP 429 (ratelimit), retry after {wait}s")
                        continue
                    if resp.status_code != 200:
                        body = resp.read().decode("utf-8", "ignore")[:300]
                        raise NoTrackError(f"HTTP {resp.status_code}: {body}")

                    for line in resp.iter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[len("data:"):].strip()
                        if not data:
                            continue
                        try:
                            evt = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        etype = evt.get("type")
                        if etype == "chat_meta":
                            new_chat_id = evt.get("chat_id", new_chat_id)
                        elif etype == "message":
                            final_text = evt.get("content", "") or final_text
                        elif etype == "delta" and not final_text:
                            final_text += evt.get("chunk", "")
                        elif etype == "error":
                            ec = evt.get("code", "")
                            if ec == "ratelimit":
                                wait = 4 * (attempt + 1)
                                time.sleep(wait)
                                last_err = NoTrackError("ratelimit, retry")
                                break
                            raise NoTrackError(f"API error: {evt.get('content')}")
            if final_text:
                break
        except httpx.HTTPError as e:
            last_err = NoTrackError(f"Network error: {e}")
            time.sleep(3)
            continue
    else:
        if last_err:
            raise last_err

    return final_text.strip()


# ---------- Quick self-test ----------
if __name__ == "__main__":
    print("[TEST] notrack.ai se jawab aa raha hai...")
    ans = chat("Assalamualaikum! Ek line mein Roman Urdu mein khud ka introduction de.")
    print("JAWAB:", ans)
