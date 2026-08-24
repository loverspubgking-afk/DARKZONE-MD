"""
app.py  —  RED-MIND Professional Edition
=========================================
Features:
  - Professional clean UI (no cartoon)
  - Multiple chat sessions (sidebar + localStorage)
  - Memory (har chat ki history yaad rehti hai)
  - Live tool-call display
  - notrack.ai uncensored brain

Run: uvicorn app:app --host 0.0.0.0 --port 8000
"""

import json
import asyncio
import threading
import queue

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from agent import run_agent
from notrack_client import chat as simple_chat

app = FastAPI(title="RED-MIND")

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>RED-MIND</title>
<style>
  :root{
    --bg:#0b0c10; --side:#101216; --side2:#161a21; --panel:#13161c; --panel2:#1b1f27;
    --border:#262b35; --border2:#2f3540;
    --text:#e8eaed; --muted:#8b919e; --muted2:#6b7280;
    --red:#e5484d; --red2:#dc2626; --red-dim:rgba(229,72,77,.12);
    --green:#10b981; --tool:#d97706;
    --user-bubble:#1f3a5f;
  }
  *{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
  html,body{height:100%}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    background:var(--bg);color:var(--text);overflow:hidden}
  .app{display:flex;height:100vh;width:100vw}

  /* ===== SIDEBAR ===== */
  .sidebar{width:270px;background:var(--side);border-right:1px solid var(--border);
    display:flex;flex-direction:column;flex-shrink:0;transition:transform .25s ease}
  .brand{display:flex;align-items:center;gap:11px;padding:16px 18px;border-bottom:1px solid var(--border)}
  .brand .mark{width:34px;height:34px;flex-shrink:0}
  .brand .name{font-size:16px;font-weight:700;letter-spacing:.5px}
  .brand .name span{color:var(--red)}
  .brand .tag{font-size:10px;color:var(--muted2);letter-spacing:.8px;text-transform:uppercase;margin-top:1px}
  .new-chat{margin:12px;padding:11px 14px;background:var(--red);color:#fff;border:none;border-radius:9px;
    font-size:13.5px;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;
    transition:background .15s}
  .new-chat:hover{background:var(--red2)}
  .chat-list{flex:1;overflow-y:auto;padding:4px 8px}
  .chat-list::-webkit-scrollbar{width:6px}.chat-list::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px}
  .cl-head{font-size:10px;color:var(--muted2);text-transform:uppercase;letter-spacing:.8px;padding:10px 10px 6px}
  .chat-item{display:flex;align-items:center;gap:9px;padding:10px;border-radius:8px;cursor:pointer;color:var(--muted);
    font-size:13px;margin-bottom:1px;transition:background .12s;position:relative}
  .chat-item:hover{background:var(--panel2)}
  .chat-item.active{background:var(--panel2);color:var(--text)}
  .chat-item .ci-icon{flex-shrink:0;opacity:.6}
  .chat-item .ci-title{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .chat-item .ci-del{opacity:0;background:none;border:none;color:var(--muted2);cursor:pointer;font-size:15px;padding:0 2px}
  .chat-item:hover .ci-del{opacity:1}
  .chat-item .ci-del:hover{color:var(--red)}
  .side-foot{padding:11px 16px;border-top:1px solid var(--border);font-size:11px;color:var(--muted2);
    display:flex;align-items:center;gap:6px}
  .side-foot .dot{width:7px;height:7px;border-radius:50%;background:var(--green)}

  /* ===== MAIN ===== */
  .main{flex:1;display:flex;flex-direction:column;min-width:0}
  .topbar{height:54px;border-bottom:1px solid var(--border);display:flex;align-items:center;
    padding:0 18px;gap:12px;background:var(--panel)}
  .topbar .menu-btn{display:none;background:none;border:none;color:var(--muted);font-size:20px;cursor:pointer}
  .topbar .t-title{font-size:14px;font-weight:600}
  .topbar .t-model{font-size:12px;color:var(--text);padding:5px 10px;border:1px solid var(--border2);
    border-radius:8px;margin-left:auto;background:var(--panel2);outline:none;cursor:pointer;font-family:inherit}
  .topbar .t-model option{background:var(--panel2);color:var(--text)}

  .msgs{flex:1;overflow-y:auto;padding:22px 0 10px;scroll-behavior:smooth}
  .msgs::-webkit-scrollbar{width:8px}.msgs::-webkit-scrollbar-thumb{background:var(--border2);border-radius:4px}
  .msgs-inner{max-width:780px;margin:0 auto;padding:0 20px}
  .empty{padding:60px 20px;text-align:center;color:var(--muted)}
  .empty .em-mark{width:64px;height:64px;margin:0 auto 20px;opacity:.95}
  .empty h2{font-size:24px;color:var(--text);margin-bottom:8px;font-weight:600}
  .empty p{font-size:14px;line-height:1.6;max-width:420px;margin:0 auto 24px}
  .suggest{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;max-width:520px;margin:0 auto}
  .suggest button{background:var(--panel2);border:1px solid var(--border2);color:var(--text);padding:11px 15px;
    border-radius:10px;font-size:13px;cursor:pointer;transition:border-color .15s;text-align:left;line-height:1.4}
  .suggest button:hover{border-color:var(--red)}

  .msg{display:flex;gap:13px;margin-bottom:22px;animation:fade .2s ease}
  @keyframes fade{from{opacity:0;transform:translateY(5px)}to{opacity:1}}
  .avatar{width:30px;height:30px;border-radius:7px;flex-shrink:0;display:flex;align-items:center;justify-content:center;
    font-size:12px;font-weight:700}
  .av-user{background:#2d3748;color:#cbd5e0}
  .av-bot{background:linear-gradient(135deg,var(--red),#991b1b);padding:4px}
  .av-bot svg{width:100%;height:100%}
  .msg-body{flex:1;min-width:0;padding-top:3px}
  .msg-body .role{font-size:12px;font-weight:600;color:var(--muted);margin-bottom:4px}
  .msg-body .content{font-size:14.5px;line-height:1.7;color:var(--text);white-space:pre-wrap;word-wrap:break-word}
  .msg-body .content p{margin-bottom:8px}
  .msg-body .content code{background:#00000040;padding:1px 5px;border-radius:4px;font-family:"SF Mono",Consolas,monospace;font-size:13px}
  .msg-body .content pre{background:#00000055;border:1px solid var(--border);padding:12px;border-radius:8px;
    overflow-x:auto;font-family:"SF Mono",Consolas,monospace;font-size:12.5px;margin:8px 0;white-space:pre}

  .tool-card{background:var(--panel2);border:1px solid var(--border2);border-left:3px solid var(--tool);
    border-radius:8px;margin:8px 0;font-size:13px;overflow:hidden}
  .tool-card .tc-head{display:flex;align-items:center;gap:8px;padding:9px 12px;cursor:pointer;color:#fbbf24;
    font-weight:600;font-size:12.5px}
  .tool-card .tc-head .arrow{margin-left:auto;transition:transform .15s;font-size:10px;color:var(--muted)}
  .tool-card.open .tc-head .arrow{transform:rotate(90deg)}
  .tool-card .tc-body{padding:0 12px 11px;display:none;font-family:"SF Mono",Consolas,monospace;font-size:12px;
    color:var(--muted);line-height:1.55;white-space:pre-wrap;word-break:break-word;max-height:220px;overflow-y:auto}
  .tool-card.open .tc-body{display:block}

  .thinking{display:flex;gap:8px;align-items:center;color:var(--muted);font-size:13px;font-style:italic;margin-bottom:18px}
  .thinking .spinner{width:15px;height:15px;border:2px solid var(--border2);border-top-color:var(--red);
    border-radius:50%;animation:spin .7s linear infinite}
  @keyframes spin{to{transform:rotate(360deg)}}

  /* ===== INPUT ===== */
  .input-area{border-top:1px solid var(--border);padding:14px 20px 16px;background:var(--panel)}
  .input-wrap{max-width:780px;margin:0 auto;display:flex;gap:10px;align-items:flex-end;
    background:var(--panel2);border:1px solid var(--border2);border-radius:14px;padding:8px 8px 8px 16px;
    transition:border-color .15s}
  .input-wrap:focus-within{border-color:var(--red)}
  textarea{flex:1;background:none;border:none;color:var(--text);font-size:14.5px;font-family:inherit;
    resize:none;outline:none;max-height:140px;line-height:1.5;padding:6px 0}
  .send-btn{width:38px;height:38px;border-radius:10px;background:var(--red);border:none;color:#fff;cursor:pointer;
    display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:background .15s}
  .send-btn:disabled{background:var(--border2);cursor:not-allowed}
  .send-btn:hover:not(:disabled){background:var(--red2)}
  .send-btn svg{width:18px;height:18px}
  .mem-note{text-align:center;font-size:11px;color:var(--muted2);margin-top:8px;max-width:780px;margin-left:auto;margin-right:auto}
  .mem-note b{color:var(--green)}

  /* mobile */
  @media(max-width:760px){
    .sidebar{position:fixed;z-index:50;height:100%;transform:translateX(-100%);box-shadow:2px 0 20px #0008}
    .sidebar.open{transform:translateX(0)}
    .topbar .menu-btn{display:block}
    .scrim{display:none;position:fixed;inset:0;background:#000a;z-index:40}
    .scrim.show{display:block}
  }
</style>
</head>
<body>
<!-- reusable logo mark -->
<svg width="0" height="0" style="position:absolute"><defs>
  <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#e5484d"/><stop offset="1" stop-color="#991b1b"/></linearGradient>
</defs></svg>

<div class="app">
  <!-- SIDEBAR -->
  <aside class="sidebar" id="sidebar">
    <div class="brand">
      <svg class="mark" viewBox="0 0 40 40"><rect x="2" y="2" width="36" height="36" rx="10" fill="url(#lg)"/>
        <circle cx="20" cy="13" r="3" fill="#fff"/><circle cx="12" cy="28" r="3" fill="#fff"/><circle cx="28" cy="28" r="3" fill="#fff"/>
        <path d="M20 13 L12 28 M20 13 L28 28 M12 28 L28 28" stroke="#fff" stroke-width="1.6" fill="none" opacity=".85"/></svg>
      <div><div class="name">RED<span>·</span>MIND</div><div class="tag">Autonomous Agent</div></div>
    </div>
    <button class="new-chat" onclick="newChat()">＋ New Chat</button>
    <div class="chat-list" id="chatList"><div class="cl-head">Chats</div></div>
    <div class="side-foot"><span class="dot"></span> Online · Uncensored · NoTrack</div>
  </aside>
  <div class="scrim" id="scrim" onclick="closeSidebar()"></div>

  <!-- MAIN -->
  <div class="main">
    <div class="topbar">
      <button class="menu-btn" onclick="openSidebar()">☰</button>
      <div class="t-title" id="curTitle">New Chat</div>
      <select class="t-model" id="modelSel" title="Brain model">
        <option value="C">NoTrack (Uncensored)</option>
        <option value="B">ChatGPT (Smart)</option>
        <option value="A">Minimax</option>
      </select>
    </div>

    <div class="msgs" id="msgs">
      <div class="msgs-inner" id="msgsInner"></div>
    </div>

    <div class="input-area">
      <div class="input-wrap">
        <textarea id="inp" rows="1" placeholder="Message RED-MIND..." autocomplete="off"></textarea>
        <button class="send-btn" id="send" onclick="doSend()" disabled>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
        </button>
      </div>
      <div class="mem-note">Memory <b>ON</b> · agent is chat ki poori baat-cheet yaad rakhega · Enter to send</div>
    </div>
  </div>
</div>

<script>
const MARK_SVG='<svg viewBox="0 0 40 40"><rect x="2" y="2" width="36" height="36" rx="10" fill="url(#lg)"/><circle cx="20" cy="13" r="3" fill="#fff"/><circle cx="12" cy="28" r="3" fill="#fff"/><circle cx="28" cy="28" r="3" fill="#fff"/><path d="M20 13 L12 28 M20 13 L28 28 M12 28 L28 28" stroke="#fff" stroke-width="1.6" fill="none" opacity=".85"/></svg>';
let chats = JSON.parse(localStorage.getItem('rm_chats')||'{}');
let curId = localStorage.getItem('rm_cur')||null;
let busy=false;

const $=s=>document.querySelector(s);
const inp=$('#inp'),send=$('#send'),msgsInner=$('#msgsInner'),chatList=$('#chatList');

inp.addEventListener('input',()=>{inp.style.height='auto';inp.style.height=Math.min(inp.scrollHeight,140)+'px';send.disabled=busy||!inp.value.trim();});
inp.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();doSend()}});

function save(){localStorage.setItem('rm_chats',JSON.stringify(chats));localStorage.setItem('rm_cur',curId)}

function newChat(){
  curId='c'+Date.now();chats[curId]={title:'New Chat',msgs:[],created:Date.now()};
  save();renderSidebar();renderChat();closeSidebar();inp.focus();
}
function openChat(id){curId=id;save();renderSidebar();renderChat();closeSidebar();}
function delChat(id,e){e.stopPropagation();delete chats[id];if(curId===id)curId=Object.keys(chats)[0]||null;if(!curId)newChat();else{save();renderSidebar();renderChat();}}

function renderSidebar(){
  let html='<div class="cl-head">Chats</div>';
  let arr=Object.values(chats).sort((a,b)=>b.created-a.created);
  if(!arr.length){html+='<div style="padding:14px 10px;color:var(--muted2);font-size:12px">Koi chat nahi. "New Chat" dabao.</div>'}
  for(let c of arr){
    let id=Object.keys(chats).find(k=>chats[k]===c);
    html+=`<div class="chat-item ${id===curId?'active':''}" onclick="openChat('${id}')">
      <span class="ci-icon">💬</span><span class="ci-title">${esc(c.title)}</span>
      <button class="ci-del" onclick="delChat('${id}',event)">×</button></div>`;
  }
  chatList.innerHTML=html;
}

function renderChat(){
  let c=chats[curId];if(!c){msgsInner.innerHTML='';return;}
  $('#curTitle').textContent=c.title;
  if(!c.msgs.length){
    msgsInner.innerHTML=`<div class="empty"><div class="em-mark">${MARK_SVG}</div>
      <h2>RED-MIND</h2><p>Ek uncensored autonomous agent. Khud search, tools, file/code use kar ke
      aapka kaam karta hai. Niche message likhein.</p>
      <div class="suggest">
        <button onclick="quick(this)">🔍 Islamabad ka mausam search karo</button>
        <button onclick="quick(this)">💻 ek Python script banao aur chalao</button>
        <button onclick="quick(this)">📄 example.com ka data laao</button>
        <button onclick="quick(this)">🧮 (847 × 23) + 1000 nikaalo</button>
      </div></div>`;
    return;
  }
  let html='';
  for(let m of c.msgs){
    if(m.role==='tool'){html+=renderTool(m);continue;}
    let av=m.role==='user'?`<div class="avatar av-user">You</div>`:`<div class="avatar av-bot">${MARK_SVG}</div>`;
    html+=`<div class="msg">${av}<div class="msg-body"><div class="role">${m.role==='user'?'You':'RED-MIND'}</div>
      <div class="content">${md(esc(m.content))}</div></div></div>`;
  }
  msgsInner.innerHTML=html;
  scrollBottom();
}
function renderTool(m){
  let body=esc(typeof m.args==='string'?m.args:JSON.stringify(m.args,null,1));
  if(m.result)body+='\n\n── RESULT ──\n'+esc(String(m.result).slice(0,800));
  return `<div class="tool-card" onclick="this.classList.toggle('open')">
    <div class="tc-head">🔧 ${esc(m.name)} <span class="arrow">▶</span></div>
    <div class="tc-body">${body}</div></div>`;
}
function scrollBottom(){$('#msgs').scrollTop=$('#msgs').scrollHeight}

function quick(b){inp.value=b.textContent.replace(/^[^\w]+/,'');inp.dispatchEvent(new Event('input'));doSend();}

async function doSend(){
  let text=inp.value.trim();if(!text||busy)return;
  if(!curId||!chats[curId])newChat();
  let c=chats[curId];
  c.msgs.push({role:'user',content:text});
  if(c.title==='New Chat')c.title=text.slice(0,40);
  inp.value='';inp.style.height='auto';busy=true;send.disabled=true;save();
  renderSidebar();renderChat();

  let tk=document.createElement('div');tk.className='thinking';tk.id='tk';
  tk.innerHTML='<span class="spinner"></span> RED-MIND soch raha hai...';
  msgsInner.appendChild(tk);scrollBottom();

  // history bhejo (memory!) - sirf user/assistant text turns
  let history=c.msgs.filter(m=>(m.role==='user'||m.role==='assistant')).slice(0,-1).map(m=>({role:m.role,content:m.content}));

  try{
    let resp=await fetch('/api/agent',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:text,history:history,model:$('#modelSel').value})});
    let reader=resp.body.getReader(),dec=new TextDecoder(),buf='';
    while(true){
      let{done,value}=await reader.read();if(done)break;
      buf+=dec.decode(value,{stream:true});
      let lines=buf.split('\n');buf=lines.pop();
      for(let line of lines){if(!line.startsWith('data:'))continue;
        try{handleEv(JSON.parse(line.slice(5).trim()),tk)}catch(e){}}
    }
  }catch(err){c.msgs.push({role:'assistant',content:'⚠️ Network error: '+err.message});}
  let tke=document.getElementById('tk');if(tke)tke.remove();
  busy=false;send.disabled=false;inp.focus();renderChat();save();
}
function handleEv(ev,tk){
  if(ev.type==='thinking'){tk.innerHTML='<span class="spinner"></span> RED-MIND kaam kar raha hai... (step '+ev.step+')';
    let last=chats[curId].msgs[chats[curId].msgs.length-1];
    if(!last||last.role!=='tool'&&last.role!=='assistant-pending'){}
  }else if(ev.type==='tool_call'){
    let c=chats[curId];c.msgs.push({role:'tool',name:ev.name,args:ev.args});
    renderChat();
  }else if(ev.type==='tool_result'){
    let c=chats[curId];
    for(let i=c.msgs.length-1;i>=0;i--){if(c.msgs[i].role==='tool'&&!c.msgs[i].result){c.msgs[i].result=ev.result;break;}}
    renderChat();
  }else if(ev.type==='answer'){
    chats[curId].msgs.push({role:'assistant',content:ev.text});
    renderChat();
  }else if(ev.type==='error'){
    chats[curId].msgs.push({role:'assistant',content:'⚠️ '+ev.text});renderChat();
  }
}

function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function md(s){return s.replace(/```([\s\S]*?)```/g,(m,c)=>'<pre>'+c.replace(/^\n/,'')+'</pre>')
  .replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*(.+?)\*\*/g,'<b>$1</b>');}
function openSidebar(){$('#sidebar').classList.add('open');$('#scrim').classList.add('show')}
function closeSidebar(){$('#sidebar').classList.remove('open');$('#scrim').classList.remove('show')}

// init
if(!Object.keys(chats).length)newChat();else{if(!curId||!chats[curId])curId=Object.keys(chats)[0];renderSidebar();renderChat();}
inp.focus();
</script>
</body>
</html>"""


@app.get("/")
async def index():
    return HTMLResponse(HTML_PAGE)


@app.get("/api/health")
async def health():
    return JSONResponse({"status": "ok", "agent": "red-mind", "uncensored": True})


@app.post("/api/agent")
async def agent_endpoint(req: Request):
    data = await req.json()
    message = data.get("message", "")
    history = data.get("history", [])
    model = data.get("model", "C")

    async def event_stream():
        q: queue.Queue = queue.Queue()
        done_flag = {"v": False}

        def on_event(ev):
            q.put(ev)

        def worker():
            try:
                run_agent(message, history=history, on_event=on_event, max_steps=10, model=model)
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
    data = await req.json()
    try:
        answer = simple_chat(data.get("message", ""), history=data.get("history", []))
        return JSONResponse({"answer": answer})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import os, uvicorn
    port = int(os.environ.get("SERVER_PORT") or os.environ.get("PORT") or 8000)
    print(f"RED-MIND starting on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
