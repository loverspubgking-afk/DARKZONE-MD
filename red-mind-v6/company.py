"""
company.py — RED-MIND v6 Agent Company — PARALLEL workers (naya)
================================================================
Boss plan karta hai → 4 role workers EK SAATH chalte hain (ThreadPoolExecutor) → Boss review → final report.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor

from omni import chat as omni_chat
from brain import run_agent

ROLES = {
    "coder":      "💻 CODER — code likhna/chalana. run_shell, write_file, read_file use karo. Code likho, chalao, test output do.",
    "researcher": "🔍 RESEARCHER — data dhoondna. web_search, fetch_url, wikipedia_search, youtube_search use karo. Sources ke saath facts lao.",
    "designer":   "🎨 DESIGNER — visuals banana. generate_image use karo (English prompts). Image ka naam/path do.",
    "writer":     "📝 WRITER — content likhna. Data ko clean professional text banao, write_file se save karo.",
}

PLAN_PROMPT = """You are the BOSS of an AI agent company. User task: {task}

Task ko 2-4 SUBTASKS mein todo. Har subtask ek role ko do (roles: coder, researcher, designer, writer).
Workers parallel chalte hain — isliye subtasks aise banao ke ek doosre pe depend na karein.

Output ONLY valid JSON:
{{"subtasks": [{{"role": "researcher", "task": "specific instruction"}}, ...]}}"""

REVIEW_PROMPT = """You are the BOSS reviewing workers ke results.

ORIGINAL TASK: {task}
WORKER RESULTS:
{results}

Errors? Missing? Quality? Review karo aur FINAL REPORT do (user Roman Urdu bole to Roman Urdu, warna English):
✅ NATIJA: seedha jawab
📋 KYA HUVA: har worker ka kaam (1 line each)
➡️ AGLA STEP: agar kuch bacha ho"""


def orchestrate(task, on_event=None, worker_model="omni", max_workers=4):
    ev = on_event or (lambda e: None)

    ev({"type": "boss_thinking"})
    plan_raw = omni_chat(PLAN_PROMPT.format(task=task), timeout=240)
    subtasks = []
    m = re.search(r"\{.*\}", plan_raw, re.DOTALL)
    if m:
        try:
            subtasks = json.loads(m.group(0)).get("subtasks", [])
        except Exception:
            pass
    if not subtasks:
        subtasks = [{"role": "coder", "task": task}]
    subtasks = subtasks[:max_workers]
    ev({"type": "boss_plan", "subtasks": subtasks})

    # ---- PARALLEL workers (naya — purane system mein sequential the) ----
    def do_worker(st):
        role = st.get("role", "coder")
        wtask = st.get("task", "")
        ev({"type": "worker_start", "role": role, "task": wtask})
        try:
            res = run_agent(wtask, model=worker_model, max_steps=10,
                            role_prompt=ROLES.get(role, ROLES["coder"]))
        except Exception as e:
            res = f"[worker error: {e}]"
        ev({"type": "worker_done", "role": role, "result": str(res)[:600]})
        return f"[{role}] {res}"

    with ThreadPoolExecutor(max_workers=max(2, len(subtasks))) as pool:
        results = list(pool.map(do_worker, subtasks))

    ev({"type": "boss_review"})
    final = omni_chat(REVIEW_PROMPT.format(task=task, results="\n\n".join(results)), timeout=240)
    ev({"type": "final", "text": final})
    return final
