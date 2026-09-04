"""
games_ai.py — RED-MIND AI GAMES
================================
Dono games "omni" (OmniRoute free models) se chalte hain, agent_company.orchestrate
ke pattern par (parallel workers + final review).

1) STORY FORGE  — AI dungeon master.
   Har turn: model ek scene describe karta hai + 3 choices deta hai. User ki choice
   par story aage barhti hai. Session history device|gameId se store hoti hai.
   Events: scene, choices, choice_result, game_over

2) HEIST CREW   — 4 AI roles (Lookout, Hacker, Driver, Insider).
   User heist plan likhta hai -> har agent apne role se PARALLEL respond karta hai
   -> Boss review -> final outcome.
   Events: heist_start, agent_start, agent_done, heist_review, heist_final, game_over
"""
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from omniroute_client import chat as omni_chat


# ─────────────────────────── helpers ───────────────────────────
def _llm(prompt, model="omni", timeout=240.0):
    """Ek single omni (OmniRoute) call — game prompt ke liye."""
    return omni_chat(prompt, model=model, timeout=timeout)


def _json_from(text):
    """Model response mein se pehla valid {...} JSON nikaal kar dict return karo.

    Model kabhi-kabhi JSON ke aas-paas text likh deta hai — yeh usay saaf karta hai.
    """
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def _clamp_choices(choices):
    """Hamesha 3 choices return karo (kam/max hone par zaroorat ke mutabiq)."""
    out = []
    for c in (choices or [])[:3]:
        if isinstance(c, str) and c.strip():
            out.append(c.strip())
    while len(out) < 3:
        out.append("Aage badho.")
    return out[:3]


# ────────────────────────── STORY FORGE ──────────────────────────
# In-memory sessions, key = device|gameId. Turn count cap rakhta hai taake
# infinite loop na ho.
_STORY = {}


def _story_key(device, game_id):
    return f"{device}|{game_id}"


def _story_save(device, game_id, data):
    _STORY[_story_key(device, game_id)] = data
    # memory guard
    if len(_STORY) > 5000:
        _STORY.clear()


def _story_load(device, game_id):
    return _STORY.get(_story_key(device, game_id))


# System prompt ke andar JSON-schema + role. Hindi/RomanUrdu friendly.
STORY_PROMPT = (
    "You are an immersive AI DUNGEON MASTER for 'Story Forge'. "
    "The story is a gritty, no-filters sci-fi/thriller adventure. "
    "You write vivid, concise scene descriptions (2-4 sentences) in the same language "
    "as the player (Roman Urdu / Urdu / English — match the player). "
    "After EVERY scene you MUST offer exactly 3 distinct, meaningful choices. "
    "\n\nAlways answer with ONLY valid JSON (no markdown, no extra text):\n"
    "{\"scene\": \"...\", \"choices\": [\"choice A\", \"choice B\", \"choice C\"]}\n\n"
    "If the player's input is a choice you were given, weave it into the next scene and "
    "advance the story. If the story has reached a natural conclusion (you decide so, or "
    "after ~8 turns), answer with:\n"
    "{\"game_over\": true, \"scene\": \"...ending...\", \"end\": \"...\"}\n"
    "Do NOT repeat the exact same choices twice in a row."
)


def run_story(device, game_id, message, on_event, model="omni"):
    """Story Forge ka ek turn. Events emit karta hai, kuch return nahi karta."""
    msg = (message or "").strip()
    sess = _story_load(device, game_id)

    # Naya game shuru karo (ya purani session uthao)
    if not sess or sess.get("over"):
        sess = {"history": [], "turns": 0, "over": False}

    history = list(sess["history"])
    # history poori ho jaye to purane turns hatao (context window bachao)
    if len(history) > 12:
        history = history[-12:]

    # Prompt: system + pichhli alternate user/assistant history + is baar ka input
    messages = [{"role": "system", "content": STORY_PROMPT}] + list(history)
    if msg:
        messages.append({"role": "user", "content": msg})
    prompt_msgs = _history_to_prompt(messages)

    raw = _llm(prompt_msgs, model=model)
    data = _json_from(raw) or {}

    is_over = bool(data.get("game_over")) or sess["turns"] >= 7

    # Scene ka pata lagao
    scene = (data.get("scene") or "").strip() or (data.get("end") or "").strip() or raw.strip() or "(scene samajh nahi aaya)"
    if not data.get("game_over") and not data.get("scene") and data.get("choices") is None:
        # model ne pure text diya to scene bana do, choices default
        data["choices"] = ["Aage badho", "Peel ke jao", "Kuch aur socho"]

    if is_over:
        end = (data.get("end") or scene).strip()
        sess["over"] = True
        on_event({"type": "scene", "text": scene})
        on_event({"type": "game_over", "text": end, "reason": "story concluded",
                  "turns": sess["turns"] + 1})
        _story_save(device, game_id, sess)
        return

    choices = _clamp_choices(data.get("choices"))
    on_event({"type": "scene", "text": scene})
    on_event({"type": "choices", "choices": choices})

    # is turn ko history mein store karo (clean user/scene alternation)
    if msg:
        history.append({"role": "user", "content": msg})
    history.append({"role": "assistant",
                    "content": f"Scene: {scene} | Choices: {', '.join(choices)}"})
    sess["history"] = history
    sess["turns"] += 1
    _story_save(device, game_id, sess)


def _history_to_prompt(msgs):
    """Message list ko ek single string prompt mein badlo (omni ko ek string diya hai)."""
    parts = []
    for m in msgs:
        role = m.get("role", "user")
        c = m.get("content", "")
        if role == "system":
            parts.append(f"SYSTEM:\n{c}")
        else:
            parts.append(f"{role.upper()}:\n{c}")
    return "\n\n".join(parts)


# ────────────────────────── HEIST CREW ──────────────────────────
HEIST_ROLES = {
    "Lookout": "👁 LOOKOUT — tum heist ke 'aankh' ho. Crowds, guards, camera, timing ke "
               "risks evaluate karo. 2-3 specific risks + unke counter-solutions do. "
               "Short, tactical, Roman Urdu/Urdu mein.",
    "Hacker": "💻 HACKER — tum security systems toot-nek wale ho. Alarms, cameras, locks, "
              "network ki weakness batao aur ek chhota logical plan do (2-4 steps).",
    "Driver": "🛞 DRIVER — tum escape ke maahir ho. Best exit route, backup road, get-away "
              "timing, aur traffic/cops avoid karne ka plan do (2-4 steps).",
    "Insider": "🎭 INSIDER — tum andar ka banda ho. Ise access, weak points, personnel, aur "
               "sabse bada 'inside secret' batao jo mission banayegi ya bigaaregi (2-4 steps).",
}

HEIST_BOSS = (
    "You are the HEIST BOSS. A crew of 4 agents (Lookout, Hacker, Driver, Insider) just "
    "reported their individual plans for the user's heist. Read ALL of them, check for "
    "conflicts/gaps/blind spots, and give a FINAL verdict: does it work? What's the success "
    "probability? What are the 2 biggest risks and the 1 fix for each. Then give a short "
    "2-3 step mission timeline. Keep it punchy and in Roman Urdu/Urdu if the user used that."
    "\n\nCREW REPORTS:\n{reports}"
)


def run_heist(device, game_id, plan, on_event, model="omni", max_agents=4):
    """Heist Crew — roles parallel, phir Boss review + final outcome."""
    plan = (plan or "").strip()
    if not plan:
        plan = "Bina plan ke — bas karo, kalwi heist."

    on_event({"type": "heist_start", "text": "Crew jama ho gayi — har agent apne role mein sochta hai…"})

    roles = list(HEIST_ROLES.items())[:max_agents]
    results = [None] * len(roles)
    lock = threading.Lock()

    def _worker(i, name, role_prompt):
        on_event({"type": "agent_start", "role": name})
        try:
            out = _llm(_history_to_prompt([
                {"role": "system", "content": role_prompt},
                {"role": "user", "content": f"User ki heist plan:\n{plan}\n\nApna role-run do."},
            ]), model=model)
        except Exception as e:
            out = f"[agent error: {e}]"
        on_event({"type": "agent_done", "role": name, "text": str(out)[:1800]})
        return i, (name, out)

    # PARALLEL (orchestrate pattern) — 4 threads
    if len(roles) > 1:
        with ThreadPoolExecutor(max_workers=min(3, len(roles))) as ex:
            futs = [ex.submit(_worker, i, name, rp) for i, (name, rp) in enumerate(roles)]
            for f in futs:
                i, res = f.result()
                results[i] = res
    else:
        for i, (name, rp) in enumerate(roles):
            _, res = _worker(i, name, rp)
            results[i] = res

    results = [r for r in results if r]
    reports = "\n\n".join(f"[{name}] {text}" for name, text in results)

    on_event({"type": "heist_review", "text": "Boss sab reports parh kar final verdict de raha hai…"})
    final = _llm(_history_to_prompt([
        {"role": "system", "content": HEIST_BOSS.format(reports=reports)},
        {"role": "user", "content": f"User ki heist plan:\n{plan}"},
    ]), model=model) or "(Boss ne kuch nahi kaha — verify karo)"

    on_event({"type": "heist_final", "text": final})
    on_event({"type": "game_over", "text": final, "reason": "heist resolved", "turns": 1})


# ────────────────────────── dispatcher ──────────────────────────
def run_game(game, device, game_id, message, on_event, model="omni", worker_model=None, max_agents=4):
    """API se ayi game request ko dispatch karo. game = 'story' | 'heist'."""
    gm = (game or "").strip().lower()
    wm = worker_model or model
    if gm == "story":
        run_story(device, game_id, message, on_event, model=wm)
    elif gm == "heist":
        run_heist(device, game_id, message, on_event, model=wm, max_agents=max_agents)
    else:
        on_event({"type": "game_over", "text": "Unknown game — sirf 'story' ya 'heist' chalte hain.", "reason": "bad game"})


if __name__ == "__main__":
    # quick smoke test
    print("running story smoke…")
    run_story("dev", "g1", "shuru karo", print, model="omni")
