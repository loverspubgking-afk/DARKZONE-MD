"""agent_company.py — AGENT COMPANY (Boss plans, Workers execute, Boss reviews)"""
import json, re, threading
from concurrent.futures import ThreadPoolExecutor
from omniroute_client import chat as omni_chat
from agent import run_agent

ROLES = {
    "coder": "💻 CODER — tum code likhne/chalane wale worker ho. run_shell, write_file, read_file, browser_* tools use karo. Code complete karo, test karo, output do.",
    "researcher": "🔍 RESEARCHER — tum data dhoondhne wale worker ho. web_search, fetch_url, http_request, wikipedia_search use karo. Facts/data lao, sources do.",
    "designer": "🎨 DESIGNER — tum visual banane wale worker ho. generate_image use karo (English prompts best). Images banao aur paths do.",
    "writer": "📝 WRITER — tum content likhne wale worker ho. read_file se data lo, write_file se final content likho. Clean, professional text.",
}

BOSS_PLAN_PROMPT = """You are the BOSS of an AI agent company. User ka task: {task}

Poora task socho aur 2-4 SUBTASKS mein divide karo. Har subtask ek role ko do:
available roles: coder, researcher, designer, writer

Output ONLY valid JSON (koi aur text nahi):
{{"subtasks": [{{"role": "coder", "task": "kya karna hai - specific instruction"}}, ...]}}"""

BOSS_REVIEW_PROMPT = """You are the BOSS reviewing workers ke results.

ORIGINAL TASK: {task}
WORKER RESULTS:
{results}

Review karo: errors hain? kuch missing? Quality kaisi?
Phir FINAL REPORT do (Roman Urdu if user Roman Urdu):
📋 KYA KIYA / 🔍 RESULTS / ✅ NATIJA / ➡️ AGLA STEP (agar kuch bacha)"""


def _llm(prompt, model="auto"):
    return omni_chat(prompt, model=model, timeout=240)


def orchestrate(task, on_event=None, worker_model="omni", boss_model="auto", max_workers=4,
                role_models=None, parallel=True):
    """Boss plan → workers execute (PARALLEL + per-role models) → review → final report."""
    ev = on_event or (lambda e: None)
    role_models = role_models or {}

    # 1) BOSS PLAN
    ev({"type": "boss_thinking"})
    plan_raw = _llm(BOSS_PLAN_PROMPT.format(task=task), boss_model)
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

    # 2) WORKERS — parallel threads + har role apna model use kar sakta hai
    results = [None] * len(subtasks)
    lock = threading.Lock()

    def _run_one(i, st):
        role = st.get("role", "coder")
        wtask = st.get("task", "")
        ev({"type": "worker_start", "role": role, "task": wtask})
        wm = role_models.get(role, worker_model)  # per-role model (mixed brain team)
        try:
            result = run_agent(
                wtask,
                system_prompt=ROLES.get(role, ROLES["coder"]),
                max_steps=8,
                on_event=lambda e, r=role: ev(dict(e, worker=r)),
                model=wm,
            )
        except Exception as e:
            result = f"[worker error: {e}]"
        ev({"type": "worker_done", "role": role, "result": str(result)[:500]})
        return i, f"[{role}] {result}"

    if parallel and len(subtasks) > 1:
        with ThreadPoolExecutor(max_workers=min(3, len(subtasks))) as ex:
            futures = [ex.submit(_run_one, i, st) for i, st in enumerate(subtasks)]
            for f in futures:
                i, res = f.result()
                results[i] = res
    else:
        for i, st in enumerate(subtasks):
            _, results[i] = _run_one(i, st)

    results = [r for r in results if r]

    # 3) BOSS REVIEW + FINAL
    ev({"type": "boss_review"})
    final = _llm(BOSS_REVIEW_PROMPT.format(task=task, results="\n\n".join(results)), boss_model)
    ev({"type": "final", "text": final})
    return final


if __name__ == "__main__":
    print(orchestrate("Ek chhoti si website ke liye: research karo latest web trends, ek logo image banao, index.html likho"))
