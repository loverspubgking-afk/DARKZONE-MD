"""
app.py  —  Web Chat Room (FastAPI + SSE)
=========================================
Ek proper chat interface jahan aap agent ko message karte hain,
aur LIVE dekhte hain ke woh kaunsa tool use kar raha hai.

Run:  uvicorn app:app --host 0.0.0.0 --port 8000
Phir browser mein:  http://localhost:8000
"""

import json
import asyncio
import threading
import queue

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from agent import run_agent
from notrack_client import chat as simple_chat

app = FastAPI(title="NoTrack Agent")

# ---------- Chat Room UI (inline, no external deps) ----------
HTML_PAGE = """<!DOCTYPE html>
<html lang="ur" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RED-MIND — Uncensored AI Agent</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0f1117; --panel: #1a1d29; --panel2: #232737;
    --text: #e4e6eb; --muted: #8b90a0; --accent: #7c5cff;
    --user: #2563eb; --tool: #d97706; --green: #10b981;
    --border: #2d3142;
  }
  body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
         background: var(--bg); color: var(--text); height: 100vh; display: flex; flex-direction: column; }
  header { background: var(--panel); padding: 14px 20px; border-bottom: 1px solid var(--border);
           display: flex; align-items: center; gap: 12px; }
  .logo { width: 38px; height: 38px; border-radius: 10px; background: linear-gradient(135deg,#7c5cff,#d946ef);
          display: flex; align-items: center; justify-content: center; font-size: 20px; }
  header h1 { font-size: 17px; font-weight: 600; }
  header .sub { font-size: 12px; color: var(--muted); }
  .badge { margin-left: auto; background: rgba(16,185,129,.15); color: var(--green);
           padding: 5px 11px; border-radius: 20px; font-size: 11px; font-weight: 600; }
  #chat { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 14px; }
  .msg { max-width: 80%; padding: 12px 16px; border-radius: 16px; line-height: 1.6;
         font-size: 14.5px; white-space: pre-wrap; word-wrap: break-word; animation: fade .25s ease; }
  @keyframes fade { from { opacity:0; transform: translateY(6px);} to {opacity:1; transform:none;} }
  .msg.user { align-self: flex-end; background: var(--user); color: #fff; border-bottom-right-radius: 4px; }
  .msg.agent { align-self: flex-start; background: var(--panel2); border: 1px solid var(--border);
               border-bottom-left-radius: 4px; }
  .msg.tool { align-self: flex-start; background: rgba(217,119,6,.12); border: 1px solid rgba(217,119,6,.4);
              font-family: 'Consolas',monospace; font-size: 13px; color: #fbbf24; }
  .msg.tool .head { font-weight: 700; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }
  .msg.tool pre { max-height: 180px; overflow: auto; color: #d1d5db; font-size: 12px;
                  white-space: pre-wrap; margin-top: 6px; }
  .msg.tool .toggle { cursor: pointer; color: #f59e0b; font-size: 11px; user-select: none; }
  .thinking { align-self: flex-start; color: var(--muted); font-size: 13px; font-style: italic;
              display: flex; align-items: center; gap: 8px; }
  .thinking .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--accent);
                   animation: pulse 1s infinite; }
  @keyframes pulse { 0%,100%{opacity:.3} 50%{opacity:1} }
  form { background: var(--panel); padding: 14px 16px; border-top: 1px solid var(--border);
         display: flex; gap: 10px; }
  input { flex: 1; background: var(--panel2); border: 1px solid var(--border); color: var(--text);
          padding: 13px 16px; border-radius: 12px; font-size: 14.5px; outline: none; }
  input:focus { border-color: var(--accent); }
  button { background: linear-gradient(135deg,#7c5cff,#d946ef); color: #fff; border: none;
           padding: 0 22px; border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer; }
  button:disabled { opacity: .5; cursor: not-allowed; }
  .sugg { display: flex; gap: 8px; flex-wrap: wrap; padding: 0 20px 6px; }
  .sugg button { background: var(--panel2); border: 1px solid var(--border); padding: 6px 12px;
                 border-radius: 16px; font-size: 12px; font-weight: 500; }
  code { background: rgba(0,0,0,.3); padding: 1px 5px; border-radius: 4px; font-size: 13px; }
  #status { font-size: 11px; color: var(--muted); text-align: center; padding-bottom: 4px; }
</style>
</head>
<body>
  <header>
    <div class="logo">🧠</div>
    <div>
      <h1>RED-MIND</h1>
      <div class="sub">Uncensored Agent · Auto Search · Tools · Browser Automation</div>
    </div>
    <div class="badge" id="badge">● online</div>
  </header>

  <div id="chat">
    <div class="msg agent">Assalamualaikum! 👋 Main <b>RED-MIND</b> hoon — ek uncensored AI agent jo khud
      <b>search</b>, <b>real browser</b> (click/type/subscribe), <b>tools</b> aur <b>code</b> use kar ke
      aapka kaam kar sakta hai. Kuch poochein 👇</div>
  </div>

  <div class="sugg">
    <button onclick="useSugg(this)">🔍 Aaj Islamabad ka mausam kya hai?</button>
    <button onclick="useSugg(this)">📰 Latest AI news search karo</button>
    <button onclick="useSugg(this)">💻 Python se ek file bana ke usme hello likho</button>
    <button onclick="useSugg(this)">🔢 (123 * 456) + 789 calculate karo</button>
  </div>
  <div id="status"></div>

  <form id="f">
    <input id="inp" placeholder="Agent ko message likhein... (Enter to send)" autocomplete="off" autofocus>
    <button id="btn" type="submit">भेजें ➤</button>
  </form>

<script>
const chat = document.getElementById('chat');
const form = document.getElementById('f');
const inp = document.getElementById('inp');
const btn = document.getElementById('btn');
let busy = false;

function scrollDown(){ chat.scrollTop = chat.scrollHeight; }
function addDiv(cls, html){ const d=document.createElement('div'); d.className='msg '+cls;
  d.innerHTML=html; chat.appendChild(d); scrollDown(); return d; }

function useSugg(b){ if(busy) return; inp.value = b.textContent.replace(/^[^\\w]+/, ''); form.requestSubmit(); }

form.onsubmit = async (e) => {
  e.preventDefault();
  const text = inp.value.trim();
  if (!text || busy) return;
  busy = true; btn.disabled = true; inp.value = '';
  addDiv('user', esc(text));

  const thinking = document.createElement('div');
  thinking.className = 'thinking'; thinking.innerHTML = '<span class="dot"></span> Agent soch raha hai...';
  chat.appendChild(thinking); scrollDown();

  try {
    const resp = await fetch('/api/agent', { method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message: text}) });
    const reader = resp.body.getReader();
    const dec = new TextDecoder(); let buf = '';
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      buf += dec.decode(value, {stream:true});
      const lines = buf.split('\\n');
      buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data:')) continue;
        const ev = JSON.parse(line.slice(5).trim());
        handleEvent(ev, thinking);
      }
    }
  } catch(err) {
    addDiv('agent', '⚠️ Network error: ' + err.message);
  }
  thinking.remove();
  busy = false; btn.disabled = false; inp.focus();
};

function handleEvent(ev, thinking){
  if (ev.type === 'thinking') {
    thinking.innerHTML = '<span class="dot"></span> 🧠 Agent soch raha hai... (step ' + ev.step + ')';
  } else if (ev.type === 'tool_call') {
    addDiv('tool',
      '<div class="head">🔧 TOOL CALL: ' + esc(ev.name) + '</div>' +
      '<pre>args: ' + esc(JSON.stringify(ev.args, null, 2)) + '</pre>');
  } else if (ev.type === 'tool_result') {
    const preview = (ev.result || '').slice(0, 600);
    addDiv('tool',
      '<div class="head">📋 RESULT</div>' +
      '<pre>' + esc(preview) + ((ev.result||'').length>600?'\\n...[truncated]':'') + '</pre>');
  } else if (ev.type === 'answer') {
    addDiv('agent', md(esc(ev.text)));
    document.getElementById('status').textContent = '✓ Ready';
  } else if (ev.type === 'error') {
    addDiv('agent', '⚠️ ' + esc(ev.text));
  }
}

function esc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function md(s){ return s.replace(/```([\\s\\S]*?)```/g, '<pre>$1</pre>')
  .replace(/`([^`]+)`/g,'<code>$1</code>')
  .replace(/\\*\\*(.+?)\\*\\*/g,'<b>$1</b>'); }
</script>
</body>
</html>"""


@app.get("/")
async def index():
    return HTMLResponse(HTML_PAGE)


@app.get("/api/health")
async def health():
    return JSONResponse({"status": "ok", "agent": "notrack", "uncensored": True})


@app.post("/api/agent")
async def agent_endpoint(req: Request):
    """Agent ko chalata hai aur events SSE stream mein bhejta hai."""
    data = await req.json()
    message = data.get("message", "")
    history = data.get("history", [])

    async def event_stream():
        q: queue.Queue = queue.Queue()
        done_flag = {"v": False}

        def on_event(ev):
            q.put(ev)

        def worker():
            try:
                run_agent(message, history=history, on_event=on_event, max_steps=10)
            except Exception as e:
                q.put({"type": "error", "text": str(e)})
            finally:
                done_flag["v"] = True

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        while True:
            try:
                ev = q.get(timeout=0.3)
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
            except queue.Empty:
                if done_flag["v"]:
                    break
                await asyncio.sleep(0.05)
        t.join(timeout=1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/simple")
async def simple_endpoint(req: Request):
    """Simple (non-agent) chat — direct notrack.ai."""
    data = await req.json()
    try:
        answer = simple_chat(data.get("message", ""), history=data.get("history", []))
        return JSONResponse({"answer": answer})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
