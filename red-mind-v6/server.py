"""
server.py — RED-MIND v6 — naya server (FastAPI)
================================================
API contract v5/v6 frontend ke saath compatible.
Endpoints: /api/agent (SSE), /api/simple, /api/chats, /api/keys, /api/memory,
           /api/activity, /api/company, /api/health, /files/{name}
"""
import asyncio
import json
import queue
import threading
import time
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse

from brain import run_agent
from company import orchestrate
from omni import chat as omni_chat
from memory import get_user_memory, set_user_memory, get_all, add_fact

START = time.time()
APP_VERSION = "6.1.0"
KEYS_FILE = "api_keys.json"
CHATS_FILE = "chats.json"
ACTIVITY_MAX = 120
_activity = []
_activity_lock = threading.Lock()


def log_activity(ev, title=""):
    if ev.get("type") in ("thinking",):
        return
    with _activity_lock:
        _activity.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "type": ev.get("type"), "name": ev.get("name", ""),
            "status": str(ev.get("result", ev.get("text", "")))[:120],
            "title": (title or "")[:40],
        })
        del _activity[:-ACTIVITY_MAX]


app = FastAPI(title="RED-MIND v6")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
async def health():
    import httpx
    ollama_ok = False
    model = ""
    try:
        r = httpx.get("http://127.0.0.1:11434/api/tags", timeout=3)
        models = r.json().get("models", [])
        ollama_ok = bool(models)
        model = models[0].get("name", "") if models else ""
    except Exception:
        pass
    return {"status": "ok", "version": APP_VERSION, "uptime": int(time.time() - START),
            "memory": bool(get_user_memory()), "ollama_ready": ollama_ok, "ollama_model": model}


@app.post("/api/agent")
async def agent_endpoint(req: Request):
    data = await req.json()
    message = data.get("message", "")
    history = data.get("history", [])
    model = data.get("model", "omni")
    ollama_url = data.get("ollamaUrl") or None
    title = (data.get("title", "") or "")[:40]

    def event_stream():
        q = queue.Queue()
        state = {"done": False}

        def on_event(ev):
            q.put(ev)
            log_activity(ev, title)

        def worker():
            try:
                run_agent(message, history=history, on_event=on_event,
                          model=model, ollama_url=ollama_url)
            except Exception as e:
                q.put({"type": "error", "text": str(e)})
            finally:
                state["done"] = True

        threading.Thread(target=worker, daemon=True).start()

        def gen():
            while True:
                try:
                    ev = q.get(timeout=0.3)
                    yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    if state["done"]:
                        break
            yield "data: [DONE]\n\n"

        return gen()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/simple")
async def simple_endpoint(req: Request):
    data = await req.json()
    try:
        ans = omni_chat(data.get("message", ""), history=data.get("history", []))
        return {"reply": ans}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/company")
async def company_endpoint(req: Request):
    data = await req.json()
    task = data.get("message", "")
    q = queue.Queue()
    state = {"done": False}

    def on_event(ev):
        q.put(ev)
        log_activity(ev, task[:40])

    def worker():
        try:
            orchestrate(task, on_event=on_event)
        except Exception as e:
            q.put({"type": "error", "text": str(e)})
        finally:
            state["done"] = True

    threading.Thread(target=worker, daemon=True).start()

    def gen():
        while True:
            try:
                ev = q.get(timeout=0.4)
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
            except queue.Empty:
                if state["done"]:
                    break
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/chats")
async def get_chats(did: str = ""):
    try:
        data = json.load(open(CHATS_FILE))
        return {"chats": data.get(did, {})}
    except Exception:
        return {"chats": {}}


@app.post("/api/chats")
async def save_chats(req: Request):
    data = await req.json()
    did = data.get("did", "")
    try:
        store = {}
        try:
            store = json.load(open(CHATS_FILE))
        except Exception:
            pass
        store[did] = data.get("chats", {})
        json.dump(store, open(CHATS_FILE, "w"), ensure_ascii=False)
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/keys")
async def save_key(req: Request):
    data = await req.json()
    provider, key = (data.get("provider") or "").strip(), (data.get("key") or "").strip()
    if not provider or not key:
        return JSONResponse({"error": "provider aur key dono chahiye"}, status_code=400)
    try:
        ks = {}
        try:
            ks = json.load(open(KEYS_FILE))
        except Exception:
            pass
        ks[provider] = key
        json.dump(ks, open(KEYS_FILE, "w"))
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/memory")
async def get_memory():
    d = get_all()
    return {"memory": d["user_memory"], "facts": d["facts"]}


@app.post("/api/memory")
async def set_memory(req: Request):
    data = await req.json()
    mem = set_user_memory(data.get("memory", ""))
    return {"ok": True, "memory": mem}


@app.post("/api/fact")
async def add_fact_ep(req: Request):
    data = await req.json()
    res = add_fact(data.get("fact", ""))
    return {"ok": True, "result": res}


@app.post("/api/multitask")
async def multitask_endpoint(req: Request):
    """Ek se 4 tasks EK SAATH — parallel agents."""
    from concurrent.futures import ThreadPoolExecutor
    data = await req.json()
    tasks = [t.strip() for t in data.get("tasks", []) if t.strip()][:4]
    model = data.get("model", "omni")
    q = queue.Queue()
    state = {"done": False}

    def run_one(i, t):
        q.put({"type": "task_start", "task": i, "text": t})
        def ev(e):
            q.put({**e, "task": i})
            log_activity(e, f"[T{i+1}] {t[:30]}")
        try:
            ans = run_agent(t, on_event=ev, model=model)
            q.put({"type": "task_done", "task": i, "text": ans or "(koi jawab nahi)"})
        except Exception as e:
            q.put({"type": "task_done", "task": i, "text": f"[error] {e}"})

    def worker():
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda a: run_one(*a), list(enumerate(tasks))))
        state["done"] = True

    threading.Thread(target=worker, daemon=True).start()

    def gen():
        while True:
            try:
                ev = q.get(timeout=0.4)
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
            except queue.Empty:
                if state["done"]:
                    break
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/activity")
async def activity():
    with _activity_lock:
        return {"activity": list(reversed(_activity))}


@app.get("/files/{name}")
async def files(name: str):
    import os
    path = os.path.join("files", os.path.basename(name))
    if not os.path.exists(path):
        return JSONResponse({"error": "not found"}, status_code=404)
    mime = "audio/mpeg" if name.endswith(".mp3") else "image/jpeg"
    return FileResponse(path, media_type=mime)


@app.get("/")
async def root():
    return {"app": "RED-MIND", "version": APP_VERSION,
            "uptime": int(time.time() - START),
            "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(__import__("os").environ.get("PORT", 7860)))
