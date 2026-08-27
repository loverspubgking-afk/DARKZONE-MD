"""
app.py — RED-MIND v3 "NEURAL" Edition
=======================================
Professional animated UI + Live Agent view + Games + parallel tasks
"""
import json, asyncio, threading, queue, time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from agent import run_agent
from notrack_client import chat as simple_chat
import os as _os

app = FastAPI(title="RED-MIND")

ACTIVITY = []  # global live activity feed

def log_activity(ev, title=""):
    try:
        t = ev.get("type", "")
        if t == "tool_call":
            text = f"🔧 {ev.get('name')}({str(ev.get('args'))[:80]})"
        elif t == "narration":
            text = f"🧠 {str(ev.get('text'))[:110]}"
        elif t == "tool_result":
            text = f"📋 Result: {str(ev.get('result'))[:90]}"
        elif t == "thinking":
            text = f"⏳ Step {ev.get('step')}..."
        elif t == "answer":
            text = "✅ Final answer ready"
        else:
            return
        ACTIVITY.append({"t": time.time(), "chat": title, "type": t, "text": text})
        if len(ACTIVITY) > 150:
            del ACTIVITY[:50]
    except Exception:
        pass

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>RED-MIND</title>
<style>
:root{--bg:#07080c;--side:#0c0e14;--panel:rgba(18,21,30,.82);--panel2:#151924;--border:#242a38;
--text:#e8eaee;--muted:#8b91a0;--red:#ff3b48;--red2:#d92535;--glow:rgba(255,59,72,.45);--green:#22c55e;--tool:#f59e0b}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
html,body{height:100%;overflow:hidden}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text)}
#bgCanvas{position:fixed;inset:0;z-index:0;opacity:.55}
.app{display:flex;height:100vh;width:100vw;position:relative;z-index:1}

/* SIDEBAR */
.sidebar{width:262px;background:linear-gradient(180deg,var(--side),#0a0c12);border-right:1px solid var(--border);
display:flex;flex-direction:column;flex-shrink:0;transition:transform .25s}
.brand{display:flex;align-items:center;gap:11px;padding:15px 16px;border-bottom:1px solid var(--border)}
.mark{width:36px;height:36px;filter:drop-shadow(0 0 8px var(--glow));animation:markPulse 3s infinite}
@keyframes markPulse{0%,100%{filter:drop-shadow(0 0 5px var(--glow))}50%{filter:drop-shadow(0 0 14px var(--glow))}}
.name{font-size:16px;font-weight:800;letter-spacing:1px}.name span{color:var(--red)}
.tag{font-size:9.5px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase}
.new-chat{margin:10px;padding:10px;border-radius:9px;background:linear-gradient(135deg,var(--red),var(--red2));
color:#fff;border:none;font-size:13px;font-weight:700;cursor:pointer;box-shadow:0 0 14px var(--glow)}
.chat-list{flex:1;overflow-y:auto;padding:2px 8px}
.cl-head{font-size:9.5px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;padding:9px 10px 5px}
.chat-item{display:flex;align-items:center;gap:8px;padding:9px 10px;border-radius:8px;cursor:pointer;color:var(--muted);font-size:12.5px;margin-bottom:1px}
.chat-item:hover{background:var(--panel2)}.chat-item.active{background:var(--panel2);color:var(--text);box-shadow:inset 2px 0 0 var(--red)}
.ci-title{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ci-busy{width:8px;height:8px;border-radius:50%;background:var(--red);animation:blink 1s infinite;flex-shrink:0}
@keyframes blink{50%{opacity:.25}}
.ci-del{opacity:0;background:none;border:none;color:var(--muted);cursor:pointer;font-size:14px}
.chat-item:hover .ci-del{opacity:1}.ci-del:hover{color:var(--red)}
.side-foot{padding:10px 14px;border-top:1px solid var(--border);font-size:10.5px;color:var(--muted);display:flex;gap:6px;align-items:center}
.dot{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 6px var(--green)}

/* MAIN */
.main{flex:1;display:flex;flex-direction:column;min-width:0}
.topbar{height:52px;border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 14px;gap:10px;background:rgba(10,12,18,.7);backdrop-filter:blur(8px)}
.menu-btn{display:none;background:none;border:none;color:var(--muted);font-size:21px;cursor:pointer}
.tabs{display:flex;gap:4px;background:var(--panel2);padding:3px;border-radius:9px}
.tab{padding:6px 14px;border-radius:7px;font-size:12.5px;font-weight:600;color:var(--muted);cursor:pointer;border:none;background:none;transition:.15s}
.tab.active{background:var(--red);color:#fff;box-shadow:0 0 10px var(--glow)}
.ollama-url{font-size:11.5px;padding:5px 9px;border:1px solid var(--red);border-radius:8px;background:var(--panel2);color:var(--text);outline:none;width:210px;display:none}
.t-model{font-size:11.5px;color:var(--text);padding:5px 8px;border:1px solid var(--border);border-radius:8px;margin-left:auto;background:var(--panel2);outline:none;cursor:pointer}
.view{flex:1;display:none;flex-direction:column;min-height:0}
.view.active{display:flex}

/* CHAT */
.msgs{flex:1;overflow-y:auto;padding:18px 0 8px}
.msgs-inner{max-width:760px;margin:0 auto;padding:0 18px}
.msg{display:flex;gap:12px;margin-bottom:18px;animation:slideUp .25s ease}
@keyframes slideUp{from{opacity:0;transform:translateY(8px)}to{opacity:1}}
.avatar{width:30px;height:30px;border-radius:8px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700}
.av-user{background:#2d3748;color:#cbd5e0}.av-bot{background:linear-gradient(135deg,var(--red),#7a0f18);padding:3px;box-shadow:0 0 8px var(--glow)}
.av-bot svg{width:100%;height:100%}
.role{font-size:11.5px;font-weight:700;color:var(--muted);margin-bottom:3px}
.content{font-size:14.5px;line-height:1.65;white-space:pre-wrap;word-wrap:break-word}
.content code{background:#00000050;padding:1px 5px;border-radius:4px;font-family:Consolas,monospace;font-size:13px}
.content pre{background:#00000066;border:1px solid var(--border);padding:11px;border-radius:8px;overflow-x:auto;font-family:Consolas,monospace;font-size:12.5px;margin:7px 0}
.tool-card{background:var(--panel2);border:1px solid var(--border);border-left:3px solid var(--tool);border-radius:8px;margin:7px 0;font-size:12.5px;overflow:hidden}
.tc-head{display:flex;gap:7px;padding:8px 11px;cursor:pointer;color:var(--tool);font-weight:700;font-size:12px}
.tc-body{padding:0 11px 10px;display:none;font-family:Consolas,monospace;font-size:11.5px;color:var(--muted);white-space:pre-wrap;max-height:190px;overflow-y:auto}
.tool-card.open .tc-body{display:block}
.thinking{display:flex;gap:9px;align-items:center;color:var(--muted);font-size:12.5px;font-style:italic;margin-bottom:16px}
.spinner{width:14px;height:14px;border:2px solid var(--border);border-top-color:var(--red);border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.empty{padding:44px 18px;text-align:center;color:var(--muted)}
.suggest{display:flex;flex-wrap:wrap;gap:9px;justify-content:center;max-width:500px;margin:18px auto 0}
.suggest button{background:var(--panel2);border:1px solid var(--border);color:var(--text);padding:10px 13px;border-radius:9px;font-size:12.5px;cursor:pointer}
.suggest button:hover{border-color:var(--red);box-shadow:0 0 8px var(--glow)}
.input-area{border-top:1px solid var(--border);padding:12px 18px 14px;background:rgba(10,12,18,.8);backdrop-filter:blur(8px)}
.input-wrap{max-width:760px;margin:0 auto;display:flex;gap:9px;background:var(--panel2);border:1px solid var(--border);border-radius:13px;padding:7px 7px 7px 14px;transition:.15s}
.input-wrap:focus-within{border-color:var(--red);box-shadow:0 0 12px var(--glow)}
textarea{flex:1;background:none;border:none;color:var(--text);font-size:16px;font-family:inherit;resize:none;outline:none;max-height:120px;line-height:1.45;padding:5px 0}
.send-btn{width:38px;height:38px;border-radius:10px;background:linear-gradient(135deg,var(--red),var(--red2));border:none;color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 0 10px var(--glow)}
.send-btn:disabled{background:var(--border);box-shadow:none;cursor:not-allowed}
.mem-note{text-align:center;font-size:10.5px;color:var(--muted);margin-top:7px}

/* LIVE VIEW */
.live-wrap{flex:1;overflow-y:auto;padding:22px;max-width:820px;margin:0 auto;width:100%}
.flow{display:flex;align-items:center;justify-content:center;gap:8px;flex-wrap:wrap;margin-bottom:24px}
.fnode{padding:13px 17px;border-radius:12px;background:var(--panel);border:1px solid var(--border);text-align:center;min-width:92px;transition:.3s}
.fnode .fi{font-size:22px}.fnode .fl{font-size:10.5px;color:var(--muted);margin-top:4px;letter-spacing:.5px}
.fnode.hot{border-color:var(--red);box-shadow:0 0 18px var(--glow);transform:scale(1.06)}
.farrow{color:var(--muted);font-size:18px}
.live-log{display:flex;flex-direction:column;gap:7px}
.lrow{background:var(--panel);border:1px solid var(--border);border-radius:9px;padding:9px 13px;font-size:12.5px;animation:slideUp .2s ease;display:flex;gap:9px;align-items:flex-start}
.lrow .lt{color:var(--muted);font-size:10.5px;min-width:56px;padding-top:2px}
.lrow.t-tool{border-left:3px solid var(--tool)}.lrow.t-narration{border-left:3px solid #8b5cf6}
.lrow.t-answer{border-left:3px solid var(--green)}.lrow.t-thinking{border-left:3px solid var(--red)}
.live-status{text-align:center;color:var(--muted);font-size:12px;padding:14px}

/* GAMES */
.games-wrap{flex:1;overflow-y:auto;padding:22px;display:flex;flex-direction:column;align-items:center;gap:20px}
.game-card{background:var(--panel);border:1px solid var(--border);border-radius:14px;padding:17px;width:100%;max-width:420px}
.game-card h3{font-size:14px;margin-bottom:10px;color:var(--red)}
.gbtn{background:var(--panel2);border:1px solid var(--border);color:var(--text);padding:8px 14px;border-radius:8px;cursor:pointer;font-size:12.5px}
.gbtn:hover{border-color:var(--red)}
#snakeC{background:#05060a;border:1px solid var(--border);border-radius:9px;display:block;margin:0 auto 9px}
.pad{display:grid;grid-template-columns:repeat(3,52px);gap:6px;justify-content:center;margin-top:9px}
.pad button{height:44px;border-radius:8px;background:var(--panel2);border:1px solid var(--border);color:var(--text);font-size:18px;cursor:pointer}
.ttt{display:grid;grid-template-columns:repeat(3,86px);gap:7px;justify-content:center;margin:10px 0}
.ttt button{height:86px;border-radius:11px;background:var(--panel2);border:1px solid var(--border);color:var(--text);font-size:34px;font-weight:800;cursor:pointer;transition:.15s}
.ttt button:hover{border-color:var(--red);box-shadow:0 0 8px var(--glow)}

@media(max-width:760px){
 .sidebar{position:fixed;z-index:50;height:100%;transform:translateX(-100%);box-shadow:2px 0 20px #000a}
 .sidebar.open{transform:translateX(0)}.scrim{display:none;position:fixed;inset:0;background:#000b;z-index:40}.scrim.show{display:block}
 .menu-btn{display:block}.ollama-url{width:140px}
}
</style>
</head>
<body>
<canvas id="bgCanvas"></canvas>
<svg width="0" height="0" style="position:absolute"><defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ff3b48"/><stop offset="1" stop-color="#7a0f18"/></linearGradient></defs></svg>

<div class="app">
<aside class="sidebar" id="sidebar">
 <div class="brand">
  <svg class="mark" viewBox="0 0 40 40"><rect x="2" y="2" width="36" height="36" rx="10" fill="url(#lg)"/><circle cx="20" cy="13" r="3" fill="#fff"/><circle cx="12" cy="28" r="3" fill="#fff"/><circle cx="28" cy="28" r="3" fill="#fff"/><path d="M20 13L12 28M20 13L28 28M12 28L28 28" stroke="#fff" stroke-width="1.6" opacity=".85"/></svg>
  <div><div class="name">RED<span>·</span>MIND</div><div class="tag">Neural Agent</div></div>
 </div>
 <button class="new-chat" onclick="newChat()">＋ New Task</button>
 <div class="chat-list" id="chatList"></div>
 <div class="side-foot"><span class="dot"></span> Neural Core Online</div>
</aside>
<div class="scrim" id="scrim" onclick="closeSidebar()"></div>

<div class="main">
 <div class="topbar">
  <button class="menu-btn" onclick="openSidebar()">☰</button>
  <div class="tabs">
   <button class="tab active" data-v="chat" onclick="setTab('chat')">💬 Chat</button>
   <button class="tab" data-v="live" onclick="setTab('live')">⚡ Live Agent</button>
   <button class="tab" data-v="games" onclick="setTab('games')">🎮 Games</button>
  </div>
  <input type="text" id="ollamaUrl" class="ollama-url" placeholder="Colab link (optional)">
  <select class="t-model" id="modelSel">
   <option value="C">NoTrack</option><option value="B">ChatGPT</option><option value="A">Minimax</option><option value="ollama">Dolphin (GPU)</option>
  </select>
 </div>

 <div class="view active" id="v-chat">
  <div class="msgs" id="msgs"><div class="msgs-inner" id="msgsInner"></div></div>
  <div class="input-area">
   <div class="input-wrap">
    <textarea id="inp" rows="1" placeholder="Message RED-MIND..." autocomplete="off"></textarea>
    <button class="send-btn" id="send" onclick="doSend()" disabled><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button>
   </div>
   <div class="mem-note">Memory ON · parallel tasks allowed — dusre chat mein task bhejo jab yeh chal raha ho! · Enter = send</div>
  </div>
 </div>

 <div class="view" id="v-live">
  <div class="live-wrap">
   <div class="flow">
    <div class="fnode" id="fn-user"><div class="fi">👤</div><div class="fl">USER</div></div><div class="farrow">➜</div>
    <div class="fnode" id="fn-brain"><div class="fi">🧠</div><div class="fl">AGENT</div></div><div class="farrow">➜</div>
    <div class="fnode" id="fn-tool"><div class="fi">🔧</div><div class="fl">TOOL</div></div><div class="farrow">➜</div>
    <div class="fnode" id="fn-result"><div class="fi">📋</div><div class="fl">RESULT</div></div>
   </div>
   <div class="live-status" id="liveStatus">Live feed — agent ki har harkat yahan dikhegi</div>
   <div class="live-log" id="liveLog"></div>
  </div>
 </div>

 <div class="view" id="v-games">
  <div class="games-wrap">
   <div class="game-card"><h3>🐍 Snake</h3><canvas id="snakeC" width="300" height="300"></canvas>
    <div style="text-align:center"><span id="score" style="color:var(--red);font-weight:700">0</span> <button class="gbtn" onclick="snakeStart()">Restart</button></div>
    <div class="pad"><span></span><button onclick="snakeDir(0,-1)">▲</button><span></span><button onclick="snakeDir(-1,0)">◀</button><button onclick="snakeDir(0,1)">▼</button><button onclick="snakeDir(1,0)">▶</button></div>
   </div>
   <div class="game-card"><h3>⭕ Tic-Tac-Toe</h3><div class="ttt" id="ttt"></div><div style="text-align:center" id="tttMsg">Terminator se khelo! <button class="gbtn" onclick="tttNew()">Reset</button></div></div>
  </div>
 </div>
</div>
</div>

<script>
const MARK='<svg viewBox="0 0 40 40"><rect x="2" y="2" width="36" height="36" rx="10" fill="url(#lg)"/><circle cx="20" cy="13" r="3" fill="#fff"/><circle cx="12" cy="28" r="3" fill="#fff"/><circle cx="28" cy="28" r="3" fill="#fff"/><path d="M20 13L12 28M20 13L28 28M12 28L28 28" stroke="#fff" stroke-width="1.6" opacity=".85"/></svg>';
const $=s=>document.querySelector(s);
let chats=JSON.parse(localStorage.getItem('rm3')||'{}'),curId=localStorage.getItem('rm3c')||null;
const inp=$('#inp'),send=$('#send'),msgsInner=$('#msgsInner'),chatList=$('#chatList');
inp.addEventListener('input',()=>{inp.style.height='auto';inp.style.height=Math.min(inp.scrollHeight,120)+'px';send.disabled=!canSend()});
inp.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();doSend()}});
const modelSel=$('#modelSel'),ollamaUrl=$('#ollamaUrl');
modelSel.addEventListener('change',()=>{ollamaUrl.style.display=modelSel.value==='ollama'?'block':'none'});
ollamaUrl.value=localStorage.getItem('rm3u')||'';
ollamaUrl.addEventListener('change',()=>localStorage.setItem('rm3u',ollamaUrl.value.trim()));
const save=()=>localStorage.setItem('rm3',JSON.stringify(chats));
const canSend=()=>!chats[curId].busy&&inp.value.trim().length>0;

function newChat(){curId='c'+Date.now();chats[curId]={title:'New Task',msgs:[],created:Date.now(),busy:false};save();renderSidebar();renderChat();closeSidebar();inp.focus()}
function openChat(id){curId=id;save();renderSidebar();renderChat();closeSidebar()}
function delChat(id,e){e.stopPropagation();delete chats[id];if(curId===id)curId=Object.keys(chats)[0]||null;if(!curId)newChat();else{save();renderSidebar();renderChat()}}
function renderSidebar(){let h='<div class="cl-head">Tasks (parallel allowed)</div>';
 for(let k of Object.keys(chats).sort((a,b)=>chats[b].created-chats[a].created)){
  const c=chats[k];
  h+=`<div class="chat-item ${k===curId?'active':''}" onclick="openChat('${k}')">${c.busy?'<span class="ci-busy"></span>':'<span>💬</span>'}<span class="ci-title">${esc(c.title)}</span><button class="ci-del" onclick="delChat('${k}',event)">×</button></div>`}
 chatList.innerHTML=h}

function renderChat(){const c=chats[curId];if(!c){msgsInner.innerHTML='';return}
 let h='';
 if(!c.msgs.length){h=`<div class="empty"><div style="font-size:46px;margin-bottom:8px">🧠</div><h2 style="color:var(--text);font-size:21px;margin-bottom:6px">RED-MIND Neural</h2><p style="font-size:13px">Uncensored autonomous agent — search, browser, tools, code.<br>Bore ho jao to ⚡Live Agent ya 🎮Games kholo!</p>
 <div class="suggest"><button onclick="quick(this)">🔍 Islamabad mausam</button><button onclick="quick(this)">🖥️ system_info + report</button><button onclick="quick(this)">🖼️ AI image banao</button><button onclick="quick(this)">📺 YouTube search karo</button></div></div>`}
 for(let m of c.msgs){
  if(m.role==='tool'){h+=toolCard(m);continue}
  if(m.role==='narration'){h+=`<div class="msg"><div class="avatar av-bot">${MARK}</div><div class="msg-body"><div class="role" style="color:var(--tool)">🧠 Soch raha hoon</div><div class="content" style="color:var(--muted);font-style:italic;font-size:13px">${md(esc(m.content))}</div></div></div>`;continue}
  const av=m.role==='user'?'<div class="avatar av-user">You</div>':`<div class="avatar av-bot">${MARK}</div>`;
  h+=`<div class="msg">${av}<div class="msg-body"><div class="role">${m.role==='user'?'You':'RED-MIND'}</div><div class="content">${md(esc(m.content))}</div></div></div>`}
 msgsInner.innerHTML=h;$('#msgs').scrollTop=999999}
function toolCard(m){let b=esc(typeof m.args==='string'?m.args:JSON.stringify(m.args));
 if(m.result)b+='\n── RESULT ──\n'+esc(String(m.result).slice(0,700));
 return `<div class="tool-card" onclick="this.classList.toggle('open')"><div class="tc-head">🔧 ${esc(m.name)} <span style="margin-left:auto;opacity:.6">▶</span></div><div class="tc-body">${b}</div></div>`}
function quick(b){inp.value=b.textContent.replace(/^[^\w]+/,'');inp.dispatchEvent(new Event('input'));doSend()}

async function doSend(){
 const text=inp.value.trim();if(!text)return;
 if(!curId||!chats[curId])newChat();
 const c=chats[curId];if(c.busy)return;   // sirf yeh chat busy — DOOSRE chat mein bhejo (parallel!)
 c.busy=true;c.msgs.push({role:'user',content:text});
 if(c.title==='New Task')c.title=text.slice(0,38);
 inp.value='';inp.style.height='auto';send.disabled=true;save();renderSidebar();renderChat();
 const tk=document.createElement('div');tk.className='thinking';tk.id='tk'+curId;
 tk.innerHTML='<span class="spinner"></span> Neural core kaam kar raha hai...';
 msgsInner.appendChild(tk);$('#msgs').scrollTop=999999;
 const hist=c.msgs.filter(m=>(m.role==='user'||m.role==='assistant')).slice(0,-1).map(m=>({role:m.role,content:m.content}));
 try{const resp=await fetch('/api/agent',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({message:text,history:hist,model:modelSel.value,ollamaUrl:ollamaUrl.value.trim(),title:c.title})});
  const reader=resp.body.getReader(),dec=new TextDecoder();let buf='';
  while(true){const{done,value}=await reader.read();if(done)break;buf+=dec.decode(value,{stream:true});
   const ls=buf.split('\n');buf=ls.pop();
   for(const l of ls){if(!l.startsWith('data:'))continue;try{handleEv(JSON.parse(l.slice(5).trim()),c)}catch(e){}}}
 }catch(err){c.msgs.push({role:'assistant',content:'⚠️ Network error: '+err.message})}
 const t=document.getElementById('tk'+curId);if(t)t.remove();
 c.busy=false;save();renderSidebar();renderChat();inp.focus()}
function handleEv(ev,c){
 if(ev.type==='tool_call'){c.msgs.push({role:'tool',name:ev.name,args:ev.args});renderChat()}
 else if(ev.type==='tool_result'){for(let i=c.msgs.length-1;i>=0;i--){if(c.msgs[i].role==='tool'&&!c.msgs[i].result){c.msgs[i].result=ev.result;break}}renderChat()}
 else if(ev.type==='narration'){c.msgs.push({role:'narration',content:ev.text});renderChat()}
 else if(ev.type==='answer'){c.msgs.push({role:'assistant',content:ev.text});renderChat()}
 else if(ev.type==='error'){c.msgs.push({role:'assistant',content:'⚠️ '+ev.text});renderChat()}}

/* LIVE VIEW */
let liveTimer=null;
function setTab(v){document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t.dataset.v===v));
 document.querySelectorAll('.view').forEach(x=>x.classList.remove('active'));$('#v-'+v).classList.add('active');
 clearInterval(liveTimer);
 if(v==='live'){liveTimer=setInterval(pollLive,2000);pollLive()}}
async function pollLive(){
 try{const r=await fetch('/api/activity');const a=await r.json();
  const log=$('#liveLog');let h='';
  const hot=a.current||'';
  ['user','brain','tool','result'].forEach(k=>{const el=$('#fn-'+k);if(el)el.classList.toggle('hot',hot===k)});
  for(const e of a.events.slice(-40).reverse()){
   h+=`<div class="lrow t-${e.type}"><span class="lt">${new Date(e.t*1000).toLocaleTimeString()}</span><span style="flex:1">${esc(e.text)}</span></div>`}
  log.innerHTML=h||'<div class="live-status">Koi activity nahi — Chat mein task bhejo!</div>';
  $('#liveStatus').textContent=a.running>0?`⚡ ${a.running} task(s) chal rahe hain...`:'Idle — Live feed active hai';
 }catch(e){}}

/* GAMES — SNAKE */
let sn={snake:[],dir:[1,0],food:[15,15],over:true,score:0,timer:null};
function snakeStart(){clearInterval(sn.timer);sn={snake:[[10,10],[9,10],[8,10]],dir:[1,0],food:[15,15],over:false,score:0,timer:null};
 sn.timer=setInterval(snakeTick,130)}
function snakeDir(x,y){if(sn.over)return;if(x===-sn.dir[0]&&y===-sn.dir[1])return;sn.dir=[x,y]}
function snakeTick(){if(sn.over)return;const c=$('#snakeC');if(!c)return;const ctx=c.getContext('2d');
 const h=sn.snake[0].slice();h[0]+=sn.dir[0];h[1]+=sn.dir[1];
 if(h[0]<0||h[0]>=30||h[1]<0||h[1]>=30||sn.snake.some(s=>s[0]===h[0]&&s[1]===h[1])){sn.over=true;clearInterval(sn.timer);drawSnake(ctx);return}
 sn.snake.unshift(h);
 if(h[0]===sn.food[0]&&h[1]===sn.food[1]){sn.score+=10;$('#score').textContent=sn.score;
  do{sn.food=[~~(Math.random()*30),~~(Math.random()*30)]}while(sn.snake.some(s=>s[0]===sn.food[0]&&s[1]===sn.food[1]))}
 else sn.snake.pop();drawSnake(ctx)}
function drawSnake(ctx){ctx.fillStyle='#05060a';ctx.fillRect(0,0,300,300);
 ctx.fillStyle='#ff3b48';ctx.shadowColor='#ff3b48';ctx.shadowBlur=8;
 ctx.fillRect(sn.food[0]*10,sn.food[1]*10,9,9);ctx.shadowBlur=0;
 sn.snake.forEach((s,i)=>{ctx.fillStyle=i===0?'#fff':'rgba(255,59,72,'+(1-i/sn.snake.length*.7)+')';ctx.fillRect(s[0]*10,s[1]*10,9,9)});
 if(sn.over){ctx.fillStyle='rgba(255,59,72,.9)';ctx.font='bold 20px sans-serif';ctx.textAlign='center';ctx.fillText('GAME OVER',150,145);ctx.font='12px sans-serif';ctx.fillText('Restart dabao',150,168)}}
document.addEventListener('keydown',e=>{if(document.querySelector('#v-games.active')){
 if(e.key==='ArrowUp')snakeDir(0,-1);if(e.key==='ArrowDown')snakeDir(0,1);if(e.key==='ArrowLeft')snakeDir(-1,0);if(e.key==='ArrowRight')snakeDir(1,0)}});
/* TIC TAC TOE */
let tb=Array(9).fill(''),tMy=true;
function tttRender(){const el=$('#ttt');let h='';tb.forEach((v,i)=>{h+=`<button onclick="tttMove(${i})">${v==='X'?'<span style="color:var(--red)">'+v+'</span>':v==='O'?'<span style="color:#3b82f6">'+v+'</span>':''}</button>`});el.innerHTML=h}
function tttMove(i){if(tb[i]||!tMy||tttWin())return;tb[i]='X';tMy=false;tttRender();
 const w=tttWin();if(w)return endTTT(w);
 setTimeout(()=>{const free=tb.map((v,j)=>v?-1:j).filter(j=>j>=0);
  // simple AI: jeet, block, warna random
  let mv=-1;for(const p of ['O','X']){for(let j of free){const t=tb.slice();t[j]=p;if(tttWin(t)){if(p==='O'){mv=j}else if(mv<0)mv=j}}}
  if(mv<0&&free.length)mv=free[~~(Math.random()*free.length)];
  if(mv>=0)tb[mv]='O';tMy=true;tttRender();const w2=tttWin();if(w2)endTTT(w2)},350)}
function tttWin(t){t=t||tb;const L=[[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];
 for(const[a,b,c]of L)if(t[a]&&t[a]===t[b]&&t[b]===t[c])return t[a];return t.every(v=>v)?'draw':null}
function endTTT(w){$('#tttMsg').innerHTML=(w==='X'?'🏆 Tum jeet gaye!':w==='O'?'🤖 Terminator jeeta!':'🤝 Draw!')+' <button class="gbtn" onclick="tttNew()">Reset</button>'}
function tttNew(){tb=Array(9).fill('');tMy=true;tttRender();$('#tttMsg').innerHTML='Terminator se khelo! <button class="gbtn" onclick="tttNew()">Reset</button>'}

/* BACKGROUND PARTICLES */
const cv=$('#bgCanvas'),cx=cv.getContext('2d');let P=[];
function resize(){cv.width=innerWidth;cv.height=innerHeight}
addEventListener('resize',resize);resize();
for(let i=0;i<42;i++)P.push({x:Math.random()*innerWidth,y:Math.random()*innerHeight,vx:(Math.random()-.5)*.5,vy:(Math.random()-.5)*.5});
(function anim(){cx.clearRect(0,0,cv.width,cv.height);
 for(const p of P){p.x+=p.vx;p.y+=p.vy;if(p.x<0||p.x>cv.width)p.vx*=-1;if(p.y<0||p.y>cv.height)p.vy*=-1}
 for(let i=0;i<P.length;i++){cx.beginPath();cx.arc(P[i].x,P[i].y,1.6,0,7);cx.fillStyle='rgba(255,59,72,.8)';cx.fill();
  for(let j=i+1;j<P.length;j++){const dx=P[i].x-P[j].x,dy=P[i].y-P[j].y,d=dx*dx+dy*dy;
   if(d<13000){cx.strokeStyle='rgba(255,59,72,'+(.14*(1-d/13000))+')';cx.beginPath();cx.moveTo(P[i].x,P[i].y);cx.lineTo(P[j].x,P[j].y);cx.stroke()}}}
 requestAnimationFrame(anim)})();

function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function md(s){return s.replace(/```([\s\S]*?)```/g,(m,c)=>'<pre>'+c.replace(/^\n/,'')+'</pre>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*(.+?)\*\*/g,'<b>$1</b>')}
function openSidebar(){$('#sidebar').classList.add('open');$('#scrim').classList.add('show')}
function closeSidebar(){$('#sidebar').classList.remove('open');$('#scrim').classList.remove('show')}
if(!Object.keys(chats).length)newChat();else{if(!curId||!chats[curId])curId=Object.keys(chats)[0];renderSidebar();renderChat()}
tttRender();
</script>
</body>
</html>"""


@app.get("/")
async def index():
    return HTMLResponse(HTML_PAGE)


@app.get("/api/health")
async def health():
    return JSONResponse({"status": "ok", "agent": "red-mind", "uncensored": True})


@app.get("/api/activity")
async def activity():
    running = sum(1 for _ in RUNNING)
    cur = "brain"
    if ACTIVITY:
        last = ACTIVITY[-1]
        if last["type"] == "tool_call":
            cur = "tool"
        elif last["type"] == "tool_result":
            cur = "result"
        elif last["type"] == "answer":
            cur = "brain"
    return JSONResponse({"events": ACTIVITY[-80:], "running": running, "current": cur})


RUNNING = set()


@app.get("/files/{fname}")
async def serve_file(fname: str):
    safe = _os.path.basename(fname)
    if _os.path.exists(safe) and _os.path.isfile(safe):
        return FileResponse(safe)
    return JSONResponse({"error": "file nahi mili"}, status_code=404)


@app.post("/api/agent")
async def agent_endpoint(req: Request):
    data = await req.json()
    message = data.get("message", "")
    history = data.get("history", [])
    model = data.get("model", "C")
    title = data.get("title", "")[:40]
    backend = "ollama" if model == "ollama" else "notrack"
    ollama_url = data.get("ollamaUrl") or None

    async def event_stream():
        q: queue.Queue = queue.Queue()
        done_flag = {"v": False}
        rid = time.time()
        RUNNING.add(rid)

        def on_event(ev):
            q.put(ev)
            log_activity(ev, title)

        def worker():
            try:
                run_agent(message, history=history, on_event=on_event, max_steps=10,
                          model=model, backend=backend, ollama_url=ollama_url)
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
        RUNNING.discard(rid)

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
    uvicorn.run(app, host="0.0.0.0", port=port)
