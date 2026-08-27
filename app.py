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

from fastapi.middleware.cors import CORSMiddleware
import time as _tm
BOOT_T = _tm.time()
app = FastAPI(title="RED-MIND")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
:root{--bg:#0d1117;--surface:#161b22;--surface2:#1c2129;--border:#30363d;--text:#e6edf3;--muted:#8b949e;
--red:#f85149;--red-dark:#b62324;--green:#3fb950;--blue:#58a6ff;--orange:#d29922;--purple:#bc8cff;--glow:0 0 20px rgba(248,81,73,.35)}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent;touch-action:manipulation}
html,body{height:100%;overflow:hidden}
body{background:var(--bg);color:var(--text);font-family:-apple-system,'Segoe UI',Roboto,sans-serif}
#bg{position:fixed;inset:0;z-index:0;opacity:.45}
.app{position:relative;z-index:1;display:flex;height:100vh}
/* SIDEBAR */
.sidebar{width:250px;background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0;transition:transform .25s}
.brand{display:flex;gap:10px;align-items:center;padding:14px}
.logo{width:38px;height:38px;filter:drop-shadow(0 0 8px rgba(248,81,73,.5));animation:breath 4s infinite}
@keyframes breath{50%{filter:drop-shadow(0 0 16px rgba(248,81,73,.75))}}
.bn{font-size:17px;font-weight:800}.bn b{color:var(--red)}
.bs{font-size:9px;color:var(--muted);letter-spacing:2px;text-transform:uppercase}
.new-task{margin:8px 12px;padding:10px;border-radius:10px;border:none;background:linear-gradient(135deg,var(--red),var(--red-dark));color:#fff;font-weight:700;font-size:12.5px;cursor:pointer;box-shadow:var(--glow);font-family:inherit}
.chat-list{flex:1;overflow-y:auto;padding:4px 8px}
.cl-head{font-size:9.5px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;padding:9px 10px 4px}
.ci{display:flex;gap:8px;align-items:center;padding:9px 10px;border-radius:8px;cursor:pointer;color:var(--muted);font-size:12.5px;margin-bottom:1px}
.ci:hover{background:var(--surface2)}.ci.active{background:var(--surface2);color:var(--text);box-shadow:inset 2px 0 0 var(--red)}
.ci-t{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ci-busy{width:8px;height:8px;border-radius:50%;background:var(--red);animation:pulse 1s infinite;flex-shrink:0}
@keyframes pulse{50%{opacity:.3}}
.ci-x{opacity:0;border:none;background:none;color:var(--muted);cursor:pointer;font-size:14px}
.ci:hover .ci-x{opacity:1}.ci-x:hover{color:var(--red)}
.side-foot{padding:10px 14px;border-top:1px solid var(--border);font-size:10.5px;color:var(--muted);display:flex;gap:6px;align-items:center}
.dot{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 6px var(--green)}
/* MAIN */
.main{flex:1;display:flex;flex-direction:column;min-width:0}
.topbar{height:54px;border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 12px;gap:8px;background:rgba(22,27,34,.9);backdrop-filter:blur(10px)}
.menu-btn{display:none;background:none;border:none;color:var(--muted);font-size:21px;cursor:pointer}
.tabs{display:flex;gap:3px;background:var(--surface);border:1px solid var(--border);padding:3px;border-radius:10px}
.tab{border:none;background:none;color:var(--muted);font-size:12px;font-weight:700;padding:7px 12px;border-radius:7px;cursor:pointer;font-family:inherit}
.tab.active{background:linear-gradient(135deg,var(--red),var(--red-dark));color:#fff;box-shadow:var(--glow)}
.ollama-url{font-size:11px;padding:5px 8px;border:1px solid var(--red);border-radius:8px;background:var(--surface2);color:var(--text);outline:none;width:170px;display:none}
.t-model{font-size:11px;color:var(--text);padding:5px 7px;border:1px solid var(--border);border-radius:8px;margin-left:auto;background:var(--surface2);outline:none;font-family:inherit}
.view{flex:1;display:none;flex-direction:column;min-height:0}
.view.active{display:flex}
/* CHAT */
.msgs{flex:1;overflow-y:auto;padding:16px 0 6px}
.mi{max-width:740px;margin:0 auto;padding:0 16px}
.msg{display:flex;gap:11px;margin-bottom:16px;animation:slideUp .25s}
@keyframes slideUp{from{opacity:0;transform:translateY(8px)}}
.av{width:32px;height:32px;border-radius:9px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:10.5px;font-weight:800}
.av.u{background:#21262d;color:var(--muted);border:1px solid var(--border)}
.av.b{background:linear-gradient(135deg,var(--red),var(--red-dark));box-shadow:var(--glow);padding:3px}.av.b svg{width:100%;height:100%}
.who{font-size:11px;font-weight:700;color:var(--muted);margin-bottom:4px}
.bubble{background:var(--surface);border:1px solid var(--border);border-radius:13px;padding:12px 15px;font-size:14px;line-height:1.6;flex:1;min-width:0}
.content{white-space:pre-wrap;word-wrap:break-word}
.content code{background:#00000055;padding:1px 5px;border-radius:4px;font-family:Consolas,monospace;font-size:13px}
.content pre{background:#00000066;border:1px solid var(--border);padding:10px;border-radius:8px;overflow-x:auto;font-family:Consolas,monospace;font-size:12px;margin:6px 0}
.toolcard{background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--orange);border-radius:9px;margin:6px 0;font-size:12px;overflow:hidden}
.tc-h{display:flex;gap:7px;padding:8px 11px;cursor:pointer;color:var(--orange);font-weight:700;font-size:11.5px}
.tc-b{padding:0 11px 9px;display:none;font-family:Consolas,monospace;font-size:11px;color:var(--muted);white-space:pre-wrap;max-height:170px;overflow-y:auto}
.toolcard.open .tc-b{display:block}
.thinking{display:flex;gap:9px;align-items:center;color:var(--muted);font-size:12.5px;font-style:italic;margin-bottom:14px}
.spin{width:14px;height:14px;border:2px solid var(--border);border-top-color:var(--red);border-radius:50%;animation:rot .7s linear infinite}
@keyframes rot{to{transform:rotate(360deg)}}
.waitbar{max-width:740px;margin:0 auto 8px;background:linear-gradient(145deg,rgba(248,81,73,.1),var(--surface));border:1px solid rgba(248,81,73,.4);border-radius:12px;padding:11px 15px;display:none;align-items:center;gap:10px;font-size:12.5px;animation:fadeIn .3s}
@keyframes fadeIn{from{opacity:0}}
.waitbar.show{display:flex}
.waitbar button{margin-left:auto;border:none;background:linear-gradient(135deg,var(--red),var(--red-dark));color:#fff;padding:7px 14px;border-radius:8px;font-size:12px;font-weight:700;cursor:pointer;font-family:inherit}
.empty{padding:30px 16px;text-align:center;color:var(--muted)}
.sug{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;max-width:480px;margin:14px auto 0}
.sug button{background:var(--surface);border:1px solid var(--border);color:var(--text);padding:9px 12px;border-radius:9px;font-size:12px;cursor:pointer;font-family:inherit}
.sug button:hover{border-color:var(--red)}
.input-area{border-top:1px solid var(--border);padding:11px 16px 13px;background:rgba(22,27,34,.9)}
.ib{max-width:740px;margin:0 auto;display:flex;gap:8px;background:var(--surface);border:1px solid var(--border);border-radius:13px;padding:7px 7px 7px 14px;transition:.2s}
.ib:focus-within{border-color:var(--red);box-shadow:var(--glow)}
textarea{flex:1;background:none;border:none;color:var(--text);font-size:16px;font-family:inherit;resize:none;outline:none;max-height:110px;line-height:1.4;padding:5px 0}
.sb{width:38px;height:38px;border-radius:10px;border:none;background:linear-gradient(135deg,var(--red),var(--red-dark));color:#fff;font-size:16px;cursor:pointer;font-family:inherit}
.sb:disabled{background:var(--border);cursor:not-allowed}
.memnote{text-align:center;font-size:10px;color:var(--muted);margin-top:6px}
/* MISSION */
.mission-wrap{flex:1;overflow-y:auto;padding:18px}
.mc{max-width:760px;margin:0 auto;background:linear-gradient(145deg,var(--surface),#10151c);border:1px solid var(--border);border-radius:15px;padding:17px 19px;position:relative;overflow:hidden;margin-bottom:12px}
.mc::before{content:'';position:absolute;top:0;left:-60%;width:60%;height:2px;background:linear-gradient(90deg,transparent,var(--red),transparent);animation:scan 3s linear infinite}
@keyframes scan{to{left:110%}}
.m-top{display:flex;align-items:center;gap:9px;font-size:10.5px;color:var(--muted);letter-spacing:2px;text-transform:uppercase}
.ld{width:8px;height:8px;border-radius:50%;background:var(--red);box-shadow:0 0 8px var(--red);animation:pulse 1.2s infinite}
.m-title{font-size:18px;font-weight:700;margin-top:8px}
.tree{max-width:760px;margin:0 auto;position:relative;padding:4px 0}
.spine{position:absolute;left:25px;top:0;bottom:0;width:2px;background:linear-gradient(180deg,var(--red),var(--border));opacity:.4}
.node{position:relative;display:flex;gap:13px;padding:9px 0;animation:slideUp .4s}
.n-ico{width:48px;height:48px;border-radius:13px;background:var(--surface);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:21px;flex-shrink:0;position:relative;z-index:2}
.node.act .n-ico{border-color:var(--red);box-shadow:var(--glow)}
.node.dn .n-ico{border-color:var(--green)}
.n-body{flex:1;background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:10px 13px;min-width:0}
.node.act .n-body{border-color:rgba(248,81,73,.5)}
.node.dn .n-body{border-color:rgba(63,185,80,.3)}
.n-head{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.n-name{font-size:13.5px;font-weight:700}
.n-chip{margin-left:auto;font-size:10px;font-weight:700;padding:3px 9px;border-radius:12px}
.chip-run{background:rgba(248,81,73,.15);color:var(--red)}
.chip-done{background:rgba(63,185,80,.15);color:var(--green)}
.n-det{font-size:12px;color:var(--muted);margin-top:4px;line-height:1.5;word-break:break-word}
/* GAMES */
.games-wrap{flex:1;overflow-y:auto;padding:18px;display:flex;flex-direction:column;align-items:center;gap:16px}
.gc{background:var(--surface);border:1px solid var(--border);border-radius:15px;padding:16px;width:100%;max-width:400px;text-align:center}
.gc h3{font-size:13.5px;margin-bottom:10px}
.gc h3 b{color:var(--red)}
.gc canvas{background:#080b10;border:1px solid var(--border);border-radius:11px;touch-action:none;max-width:100%}
.gbtn{background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:8px 16px;border-radius:9px;cursor:pointer;font-size:12px;font-weight:600;font-family:inherit}
.gbtn:hover{border-color:var(--red)}
.gbtn.p{background:linear-gradient(135deg,var(--red),var(--red-dark));border:none;box-shadow:var(--glow)}
.sb2{display:flex;justify-content:center;gap:18px;margin:10px 0;font-size:12px;color:var(--muted)}
.sb2 b{color:var(--red)}
.pad{display:grid;grid-template-columns:repeat(3,54px);gap:6px;justify-content:center;margin-top:8px}
.pad button{height:44px;border-radius:10px;background:var(--surface2);border:1px solid var(--border);color:var(--text);font-size:18px;cursor:pointer}
.foot{text-align:center;color:var(--muted);font-size:10.5px;padding:14px;border-top:1px solid var(--border);margin-top:20px}
@media(max-width:740px){
.sidebar{position:fixed;z-index:50;height:100%;transform:translateX(-100%);box-shadow:2px 0 20px #000a}
.sidebar.open{transform:translateX(0)}.scrim{display:none;position:fixed;inset:0;background:#000b;z-index:40}.scrim.show{display:block}
.menu-btn{display:block}.tab{padding:7px 8px;font-size:11px}}
</style>
</head>
<body>
<canvas id="bg"></canvas>
<svg width="0" height="0" style="position:absolute"><defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f85149"/><stop offset="1" stop-color="#8b1d1f"/></linearGradient></defs></svg>
<div class="app">
<aside class="sidebar" id="sidebar">
 <div class="brand">
  <svg class="logo" viewBox="0 0 64 64"><path d="M32 7 C24 7 20 12 19 17 C13 18 10 23 11 28 C7 31 6 37 9 41 C7 46 10 51 15 52 C16 57 21 60 26 58 C28 61 33 61 35 58 C40 60 45 57 46 52 C51 51 54 46 52 41 C55 37 54 31 50 28 C51 23 48 18 42 17 C41 12 37 7 32 7 Z" fill="url(#lg)"/><g stroke="#fff" stroke-width="1.3" opacity=".9" fill="none" stroke-linecap="round"><path d="M32 13L26 21L32 29L26 39L32 51"/><path d="M32 29L40 23M32 29L41 35M26 21L18 25M26 39L17 43M41 35L47 43"/></g><g fill="#fff"><circle cx="32" cy="13" r="2.1"/><circle cx="26" cy="21" r="2.1"/><circle cx="32" cy="29" r="2.8"/><circle cx="26" cy="39" r="2.1"/><circle cx="32" cy="51" r="2.1"/><circle cx="40" cy="23" r="2.1"/><circle cx="41" cy="35" r="2.1"/><circle cx="47" cy="43" r="2.1"/><circle cx="18" cy="25" r="1.7"/><circle cx="17" cy="43" r="1.7"/></g></svg>
  <div><div class="bn">RED<b>·</b>MIND</div><div class="bs">Neural Agent</div></div>
 </div>
 <button class="new-task" onclick="newChat()">＋ New Task</button>
 <div class="chat-list" id="chatList"></div>
 <div class="side-foot"><span class="dot"></span> <span id="connStatus">Neural Core Online</span></div>
</aside>
<div class="scrim" id="scrim" onclick="closeSidebar()"></div>
<div class="main">
 <div class="topbar">
  <button class="menu-btn" onclick="openSidebar()">☰</button>
  <div class="tabs">
   <button class="tab active" data-v="chat" onclick="setTab('chat')">💬 Chat</button>
   <button class="tab" data-v="mission" onclick="setTab('mission')">⚡ Mission</button>
   <button class="tab" data-v="games" onclick="setTab('games')">🎮 Arcade</button>
  </div>
  <input type="text" id="ollamaUrl" class="ollama-url" placeholder="GPU link (optional)">
  <select class="t-model" id="modelSel">
   <option value="ollama">🧠 Neural 14B</option><option value="C">NoTrack</option><option value="B">ChatGPT</option><option value="A">Minimax</option>
  </select>
 </div>
 <div class="view active" id="v-chat">
  <div class="msgs" id="msgs"><div class="mi" id="msgsInner"></div></div>
  <div class="waitbar" id="waitbar"><span class="spin"></span><span id="waitTxt">Agent kaam kar raha hai...</span><button onclick="stopTask()" style="background:linear-gradient(135deg,#6e7681,#30363d)">⛔ STOP</button><button onclick="setTab('games')">🎮 Games KHELO</button></div>
  <div class="input-area">
   <div class="ib"><textarea id="inp" rows="1" placeholder="Message RED-MIND..." autocomplete="off"></textarea>
   <button class="sb" id="send" onclick="doSend()" disabled>➤</button></div>
   <div class="memnote">Memory ON · parallel tasks (dusre chat mein bhejo jab yeh busy ho) · Enter = send</div>
  </div>
 </div>
 <div class="view" id="v-mission">
  <div class="mission-wrap">
   <div class="mc"><div class="m-top"><span class="ld"></span> LIVE MISSION FEED</div>
    <div class="m-title">🎯 Agent ki har harkat real-time</div>
    <div style="font-size:11.5px;color:var(--muted);margin-top:6px" id="mStat">Idle — Chat mein task bhejo, yahan tree banti jayegi</div></div>
   <div class="tree" id="tree"><div class="spine"></div></div>
  </div>
 </div>
 <div class="view" id="v-games">
  <div class="games-wrap">
   <div class="gc"><h3>🐍 <b>NEON</b> Snake</h3><canvas id="gc1" width="300" height="300"></canvas>
    <div class="sb2"><span>SCORE <b id="s1">0</b></span><span>BEST <b id="b1">0</b></span></div>
    <button class="gbtn p" onclick="g1start()">▶ Start</button>
    <div class="pad"><span></span><button onclick="g1d(0,-1)">▲</button><span></span><button onclick="g1d(-1,0)">◀</button><button onclick="g1d(0,1)">▼</button><button onclick="g1d(1,0)">▶</button></div></div>
   <div class="gc"><h3>🏎️ <b>TURBO</b> Racer</h3><canvas id="gc2" width="300" height="340"></canvas>
    <div class="sb2"><span>SCORE <b id="s2">0</b></span><span>BEST <b id="b2">0</b></span></div>
    <button class="gbtn p" onclick="g2start()">▶ Start</button>
    <div class="pad"><span></span><button onclick="g2d(-1)">◀</button><span></span><span></span><button onclick="g2d(1)">▶</button><span></span></div>
    <p style="color:var(--muted);font-size:10.5px;margin-top:6px">Gari chalao, traffic dodge karo!</p></div>
   <div class="gc"><h3>🐦 <b>NEON</b> Jump</h3><canvas id="gc3" width="300" height="300"></canvas>
    <div class="sb2"><span>SCORE <b id="s3">0</b></span><span>BEST <b id="b3">0</b></span></div>
    <button class="gbtn p" onclick="g3start()">▶ Start</button>
    <p style="color:var(--muted);font-size:10.5px;margin-top:6px">Tap / button dabao — udte raho!</p></div>
   <div class="gc"><h3>🧱 <b>BRICK</b> Breaker</h3><canvas id="gc4" width="300" height="300"></canvas>
    <div class="sb2"><span>SCORE <b id="s4">0</b></span><span>BEST <b id="b4">0</b></span></div>
    <button class="gbtn p" onclick="g4start()">▶ Start</button>
    <div class="pad"><button onclick="g4d(-1)">◀</button><span></span><button onclick="g4d(1)">▶</button></div></div>
   <div class="foot">RED·MIND v4 · GitHub Dark · Neural Brain · © 2026</div>
  </div>
 </div>
</div></div>
<script>
const LOGO='<svg viewBox="0 0 64 64"><path d="M32 7 C24 7 20 12 19 17 C13 18 10 23 11 28 C7 31 6 37 9 41 C7 46 10 51 15 52 C16 57 21 60 26 58 C28 61 33 61 35 58 C40 60 45 57 46 52 C51 51 54 46 52 41 C55 37 54 31 50 28 C51 23 48 18 42 17 C41 12 37 7 32 7 Z" fill="url(#lg)"/><g stroke="#fff" stroke-width="1.3" opacity=".9" fill="none"><path d="M32 13L26 21L32 29L26 39L32 51"/><path d="M32 29L40 23M32 29L41 35M26 21L18 25M26 39L17 43M41 35L47 43"/></g><g fill="#fff"><circle cx="32" cy="13" r="2.1"/><circle cx="26" cy="21" r="2.1"/><circle cx="32" cy="29" r="2.8"/><circle cx="26" cy="39" r="2.1"/><circle cx="32" cy="51" r="2.1"/><circle cx="40" cy="23" r="2.1"/><circle cx="41" cy="35" r="2.1"/><circle cx="47" cy="43" r="2.1"/></g></svg>';
const $=s=>document.querySelector(s);
let chats=JSON.parse(localStorage.getItem('rm4')||'{}'),curId=localStorage.getItem('rm4c')||null;
const inp=$('#inp'),send=$('#send'),msgsInner=$('#msgsInner'),chatList=$('#chatList');
inp.addEventListener('input',()=>{inp.style.height='auto';inp.style.height=Math.min(inp.scrollHeight,110)+'px';send.disabled=!(chats[curId]&&!chats[curId].busy&&inp.value.trim())});
inp.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();doSend()}});
const modelSel=$('#modelSel'),ourl=$('#ollamaUrl');
modelSel.addEventListener('change',()=>{ourl.style.display=modelSel.value==='ollama'?'block':'none'});
ourl.value=localStorage.getItem('rm4u')||'';ourl.addEventListener('change',()=>localStorage.setItem('rm4u',ourl.value.trim()));
const save=()=>localStorage.setItem('rm4',JSON.stringify(chats));
function newChat(){curId='c'+Date.now();chats[curId]={title:'New Task',msgs:[],created:Date.now(),busy:false};save();renderS();renderC();closeSidebar();inp.focus()}
function openChat(id){curId=id;save();renderS();renderC();closeSidebar()}
function delChat(id,e){e.stopPropagation();delete chats[id];if(curId===id)curId=Object.keys(chats)[0]||null;if(!curId)newChat();else{save();renderS();renderC()}}
function renderS(){let h='<div class="cl-head">Tasks (parallel)</div>';
 Object.keys(chats).sort((a,b)=>chats[b].created-chats[a].created).forEach(k=>{const c=chats[k];
 h+=`<div class="ci ${k===curId?'active':''}" onclick="openChat('${k}')">${c.busy?'<span class="ci-busy"></span>':'💬'}<span class="ci-t">${esc(c.title)}</span><button class="ci-x" onclick="delChat('${k}',event)">×</button></div>`});
 chatList.innerHTML=h}
function renderC(){const c=chats[curId];if(!c)return;
 let h='';
 if(!c.msgs.length){h=`<div class="empty" style="padding-top:36px"><div style="width:70px;height:70px;margin:0 auto 12px;filter:drop-shadow(0 0 14px rgba(248,81,73,.5))">${LOGO}</div><h2 style="font-size:21px;color:var(--text)">RED·MIND <span style="font-size:12px;color:var(--muted)">v4 Neural</span></h2><p style="font-size:12.5px;margin-top:7px">Uncensored agent — search, browser, code, tools<br>Wait lage to 🎮 Arcade kholo!</p><div class="sug"><button onclick="quick(this)">🔍 Mausam search karo</button><button onclick="quick(this)">🖥️ System report banao</button><button onclick="quick(this)">🖼️ AI image banao</button><button onclick="quick(this)">🧮 Calculator test</button></div></div>`}
 for(const m of c.msgs){
  if(m.role==='tool'){let b=esc(typeof m.args==='string'?m.args:JSON.stringify(m.args));if(m.result)b+='\n── RESULT ──\n'+esc(String(m.result).slice(0,600));
   h+=`<div class="toolcard" onclick="this.classList.toggle('open')"><div class="tc-h">🔧 ${esc(m.name)} <span style="margin-left:auto;opacity:.5">▶</span></div><div class="tc-b">${b}</div></div>`;continue}
  if(m.role==='narration'){h+=`<div class="msg"><div class="av b">${LOGO}</div><div class="bubble"><div class="who" style="color:var(--purple)">🧠 Thinking</div><div class="content" style="color:var(--muted);font-style:italic;font-size:13px">${md(esc(m.content))}</div></div></div>`;continue}
  const av=m.role==='user'?'<div class="av u">YOU</div>':`<div class="av b">${LOGO}</div>`;
  h+=`<div class="msg">${av}<div class="bubble"><div class="who">${m.role==='user'?'You':'RED-MIND'}</div><div class="content">${md(esc(m.content))}</div></div></div>`}
 msgsInner.innerHTML=h;$('#msgs').scrollTop=9e6;updateWait()}
let wTimer=null;
function updateWait(){const c=chats[curId];const w=$('#waitbar');
 if(c&&c.busy){w.classList.add('show');
  $('#waitTxt').textContent='⏳ Command mil gaya! Agent kaam kar raha hai — '+(c.title.slice(0,26)||'task')+'...';
  clearInterval(wTimer);
  wTimer=setInterval(()=>{if(chats[curId]&&chats[curId].busy&&chats[curId].t0){
   const s=Math.floor((Date.now()-chats[curId].t0)/1000);
   $('#waitTxt').textContent='⏳ '+s+'s — Agent kaam kar raha hai — '+(chats[curId].title.slice(0,22)||'task')+'...'}},1000)}
 else{w.classList.remove('show');clearInterval(wTimer)}}
function stopTask(){const c=chats[curId];if(c&&c.ctrl){try{c.ctrl.abort()}catch(e){}}}
function quick(b){inp.value=b.textContent.replace(/^[^\w]+/,'');inp.dispatchEvent(new Event('input'));doSend()}
async function doSend(){const text=inp.value.trim();if(!text)return;
 if(!curId||!chats[curId])newChat();const c=chats[curId];if(c.busy)return;
 c.busy=true;c.t0=Date.now();c.ctrl=new AbortController();c.msgs.push({role:'user',content:text});
 if(c.title==='New Task')c.title=text.slice(0,36);
 inp.value='';inp.style.height='auto';send.disabled=true;save();renderS();renderC();
 const hist=c.msgs.filter(m=>m.role==='user'||m.role==='assistant').slice(0,-1).map(m=>({role:m.role,content:m.content}));
 try{const resp=await fetch('/api/agent',{method:'POST',headers:{'Content-Type':'application/json'},
  signal:c.ctrl.signal,
  body:JSON.stringify({message:text,history:hist,model:modelSel.value,ollamaUrl:ourl.value.trim(),title:c.title})});
  const reader=resp.body.getReader(),dec=new TextDecoder();let buf='';
  while(true){const{done,value}=await reader.read();if(done)break;buf+=dec.decode(value,{stream:true});
   const ls=buf.split('\n');buf=ls.pop();
   for(const l of ls){if(!l.startsWith('data:'))continue;try{const ev=JSON.parse(l.slice(5).trim());hEv(ev,c)}catch(e){}}}
 }catch(err){
  if(err.name==='AbortError'){c.msgs.push({role:'assistant',content:'⛔ Task stopped (user ne cancel kiya). Naya task bhejo jab ready ho.'})}
  else{c.msgs.push({role:'assistant',content:'⚠️ Network error: '+err.message})}}
 c.busy=false;save();renderS();renderC();inp.focus()}
function hEv(ev,c){
 if(ev.type==='tool_call'){c.msgs.push({role:'tool',name:ev.name,args:ev.args})}
 else if(ev.type==='tool_result'){for(let i=c.msgs.length-1;i>=0;i--){if(c.msgs[i].role==='tool'&&!c.msgs[i].result){c.msgs[i].result=ev.result;break}}}
 else if(ev.type==='narration'){c.msgs.push({role:'narration',content:ev.text})}
 else if(ev.type==='answer'){c.msgs.push({role:'assistant',content:ev.text})}
 else if(ev.type==='error'){c.msgs.push({role:'assistant',content:'⚠️ '+ev.text})}
 renderC()}
/* MISSION (real events) */
let missionNodes=[];
function setTab(v){document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t.dataset.v===v));
 document.querySelectorAll('.view').forEach(x=>x.classList.remove('active'));$('#v-'+v).classList.add('active');
 clearInterval(lt);if(v==='mission'){lt=setInterval(pollMission,2000);pollMission()}}
let lt=null,seen=new Set();
async function pollMission(){try{const r=await fetch('/api/activity');const a=await r.json();
 $('#mStat').textContent=a.running>0?`⚡ ${a.running} task(s) chal rahe hain — tree live hai`:'Idle — Chat mein task bhejo';
 const tr=$('#tree');
 for(const e of a.events){const key=e.t+'|'+e.text;
  if(seen.has(key))continue;seen.add(key);
  const el=document.createElement('div');
  let ic='🧠',nm='Thinking',cls='act';
  if(e.type==='tool_call'){ic='🔧';nm=e.text.split('(')[0].replace('🔧','').trim()||'Tool';cls='act'}
  else if(e.type==='narration'){ic='💭';nm='Plan';cls='act'}
  else if(e.type==='tool_result'){ic='📋';nm='Result';cls='dn'}
  else if(e.type==='answer'){ic='✅';nm='Complete';cls='dn'}
  el.className='node '+cls;
  el.innerHTML=`<div class="n-ico">${ic}</div><div class="n-body"><div class="n-head"><span class="n-name">${esc(nm)}</span>
   <span class="n-chip ${cls==='dn'?'chip-done':'chip-run'}">${cls==='dn'?'✓':'RUN'}</span></div>
   <div class="n-det">${esc(e.text)}</div></div>`;
  tr.appendChild(el);
  if(seen.size>40){const f=tr.querySelector('.node');if(f&&tr.children.length>26)f.remove()}}
 }catch(e){}}
/* ===== GAMES ===== */
function best(k,v){const b=+(localStorage.getItem(k)||0);if(v>b)localStorage.setItem(k,v);return Math.max(b,v)}
/* SNAKE */
let S1={s:[[10,10]],d:[1,0],f:[15,15],sc:0,tm:null,dead:true};
const c1=$('#gc1'),x1=c1.getContext('2d');
function g1start(){clearInterval(S1.tm);S1={s:[[10,10],[9,10],[8,10]],d:[1,0],f:[15,15],sc:0,tm:null,dead:false};$('#s1').textContent=0;S1.tm=setInterval(g1t,125)}
function g1d(x,y){if(S1.dead)return;if(x===-S1.d[0]&&y===-S1.d[1])return;S1.d=[x,y]}
function g1t(){if(S1.dead){clearInterval(S1.tm);g1draw();return}
 const h=[S1.s[0][0]+S1.d[0],S1.s[0][1]+S1.d[1]];
 if(h[0]<0||h[0]>=25||h[1]<0||h[1]>=25||S1.s.some(s=>s[0]===h[0]&&s[1]===h[1])){S1.dead=true;$('#b1').textContent=best('g1',S1.sc);g1draw();return}
 S1.s.unshift(h);
 if(h[0]===S1.f[0]&&h[1]===S1.f[1]){S1.sc+=10;$('#s1').textContent=S1.sc;do{S1.f=[~~(Math.random()*25),~~(Math.random()*25)]}while(S1.s.some(s=>s[0]===S1.f[0]&&s[1]===S1.f[1]))}else S1.s.pop();g1draw()}
function g1draw(){x1.fillStyle='#080b10';x1.fillRect(0,0,300,300);
 x1.shadowColor='#f85149';x1.shadowBlur=12;x1.fillStyle='#f85149';x1.beginPath();x1.arc(S1.f[0]*12+6,S1.f[1]*12+6,5,0,7);x1.fill();x1.shadowBlur=0;
 S1.s.forEach((s,i)=>{x1.fillStyle=i===0?'#fff':`rgba(248,81,73,${1-i/S1.s.length*.7})`;if(i===0){x1.shadowColor='#fff';x1.shadowBlur=8}x1.fillRect(s[0]*12+1,s[1]*12+1,10,10);x1.shadowBlur=0});
 if(S1.dead){x1.fillStyle='rgba(248,81,73,.95)';x1.font='800 20px Segoe UI';x1.textAlign='center';x1.fillText('GAME OVER',150,145);x1.font='11px Segoe UI';x1.fillStyle='#8b949e';x1.fillText('Restart dabao',150,166)}}
$('#b1').textContent=localStorage.getItem('g1')||0;g1draw();
let t1x=null,t1y=null;c1.addEventListener('touchstart',e=>{t1x=e.touches[0].clientX;t1y=e.touches[0].clientY});
c1.addEventListener('touchend',e=>{const dx=e.changedTouches[0].clientX-t1x,dy=e.changedTouches[0].clientY-t1y;if(Math.abs(dx)>Math.abs(dy))g1d(dx>0?1:-1,0);else g1d(0,dy>0?1:-1)});
/* RACER */
let R={lane:1,obs:[],sc:0,tm:null,dead:true,sp:3};
const c2=$('#gc2'),x2=c2.getContext('2d');
function g2start(){clearInterval(R.tm);R={lane:1,obs:[],sc:0,tm:null,dead:false,sp:3};$('#s2').textContent=0;R.tm=setInterval(g2t,50)}
function g2d(d){if(R.dead)return;R.lane=Math.max(0,Math.min(2,R.lane+d))}
function g2t(){if(R.dead)return;R.sc+=1;if(R.sc%100===0)R.sp+=.25;$('#s2').textContent=R.sc;
 if(Math.random()<.05+R.sp*.008)R.obs.push({l:~~(Math.random()*3),y:-40});
 R.obs.forEach(o=>o.y+=R.sp);R.obs=R.obs.filter(o=>o.y<360);
 if(R.obs.some(o=>o.l===R.lane&&o.y>240&&o.y<300)){R.dead=true;clearInterval(R.tm);$('#b2').textContent=best('g2',R.sc)}
 g2draw()}
function g2draw(){x2.fillStyle='#080b10';x2.fillRect(0,0,300,340);
 x2.strokeStyle='#30363d';x2.setLineDash([14,16]);for(let i=1;i<3;i++){x2.beginPath();x2.moveTo(i*100,0);x2.lineTo(i*100,340);x2.stroke()}x2.setLineDash([]);
 R.obs.forEach(o=>{x2.fillStyle='#58a6ff';x2.shadowColor='#58a6ff';x2.shadowBlur=10;x2.fillRect(o.l*100+28,o.y,44,60);x2.shadowBlur=0});
 x2.fillStyle='#f85149';x2.shadowColor='#f85149';x2.shadowBlur=16;x2.fillRect(R.lane*100+24,252,52,64);x2.shadowBlur=0;
 x2.fillStyle='#fff';x2.fillRect(R.lane*100+40,264,20,12);
 if(R.dead){x2.fillStyle='rgba(248,81,73,.95)';x2.font='800 20px Segoe UI';x2.textAlign='center';x2.fillText('CRASHED!',150,160);x2.font='11px Segoe UI';x2.fillStyle='#8b949e';x2.fillText('Restart dabao',150,180)}}
$('#b2').textContent=localStorage.getItem('g2')||0;g2draw();
/* FLAPPY */
let F={y:150,v:0,ps:[],sc:0,tm:null,dead:true};
const c3=$('#gc3'),x3=c3.getContext('2d');
function g3start(){clearInterval(F.tm);F={y:150,v:0,ps:[{x:320,g:~~(Math.random()*180)+50}],sc:0,tm:null,dead:false};$('#s3').textContent=0;F.tm=setInterval(g3t,30)}
function g3jump(){if(!F.dead)F.v=-6.2}
c3.addEventListener('pointerdown',g3jump);
function g3t(){if(F.dead)return;F.v+=.42;F.y+=F.v;
 if(F.y<8||F.y>292){F.dead=true;clearInterval(F.tm);$('#b3').textContent=best('g3',F.sc);g3draw();return}
 F.ps.forEach(p=>p.x-=2.6);if(F.ps[F.ps.length-1].x<170)F.ps.push({x:320,g:~~(Math.random()*180)+50});
 F.ps=F.ps.filter(p=>p.x>-60);
 for(const p of F.ps){if(p.x<50&&p.x+52>18&&(F.y-12<p.g||F.y+12>p.g+80)){F.dead=true;clearInterval(F.tm);$('#b3').textContent=best('g3',F.sc)}}
 if(!F.dead){F.ps.forEach(p=>{if(p.x+52<18&&!p.p){p.p=1;F.sc++;$('#s3').textContent=F.sc}})}
 g3draw()}
function g3draw(){x3.fillStyle='#080b10';x3.fillRect(0,0,300,300);
 F.ps.forEach(p=>{x3.fillStyle='#3fb950';x3.shadowColor='#3fb950';x3.shadowBlur=8;
  x3.fillRect(p.x,0,52,p.g);x3.fillRect(p.x,p.g+80,52,300);x3.shadowBlur=0});
 x3.fillStyle='#f85149';x3.shadowColor='#f85149';x3.shadowBlur=14;x3.beginPath();x3.arc(18,F.y,11,0,7);x3.fill();x3.shadowBlur=0;
 x3.fillStyle='#fff';x3.beginPath();x3.arc(22,F.y-3,3.5,0,7);x3.fill();
 if(F.dead){x3.fillStyle='rgba(248,81,73,.95)';x3.font='800 20px Segoe UI';x3.textAlign='center';x3.fillText('GAME OVER',150,140);x3.font='11px Segoe UI';x3.fillStyle='#8b949e';x3.fillText('Restart dabao',150,160)}}
$('#b3').textContent=localStorage.getItem('g3')||0;g3draw();
/* BREAKOUT */
let B={px:130,bx:150,by:220,vx:3,vy:-3.4,br:[],sc:0,tm:null,dead:true};
const c4=$('#gc4'),x4=c4.getContext('2d');
function g4start(){clearInterval(B.tm);B={px:130,bx:150,by:220,vx:3,vy:-3.4,sc:0,tm:null,dead:false,br:[]};
 for(let r=0;r<4;r++)for(let c=0;c<6;c++)B.br.push({x:12+c*47,y:30+r*20,on:true});
 $('#s4').textContent=0;B.tm=setInterval(g4t,28)}
function g4d(d){B.px=Math.max(0,Math.min(240,B.px+d*30))}
let t4x=null;c4.addEventListener('touchstart',e=>{t4x=e.touches[0].clientX});
c4.addEventListener('touchmove',e=>{e.preventDefault();const dx=e.touches[0].clientX-t4x;B.px=Math.max(0,Math.min(240,B.px+dx*.6));t4x=e.touches[0].clientX});
function g4t(){if(B.dead)return;
 B.bx+=B.vx;B.by+=B.vy;
 if(B.bx<7||B.bx>293)B.vx*=-1;if(B.by<7)B.vy*=-1;
 if(B.by>282&&B.bx>B.px&&B.bx<B.px+60)B.vy=-Math.abs(B.vy);
 if(B.by>300){B.dead=true;clearInterval(B.tm);$('#b4').textContent=best('g4',B.sc)}
 for(const b of B.br){if(b.on&&B.bx>b.x-6&&B.bx<b.x+46&&B.by>b.y-6&&B.by<b.y+16){b.on=false;B.vy*=-1;B.sc+=5;$('#s4').textContent=B.sc}}
 if(B.br.every(b=>!b.on))g4start();
 g4draw()}
function g4draw(){x4.fillStyle='#080b10';x4.fillRect(0,0,300,300);
 B.br.forEach(b=>{if(b.on){x4.fillStyle=['#f85149','#d29922','#3fb950','#58a6ff'][~~(b.y/20)%4];x4.shadowColor=x4.fillStyle;x4.shadowBlur=6;x4.fillRect(b.x,b.y,44,12);x4.shadowBlur=0}});
 x4.fillStyle='#e6edf3';x4.shadowColor='#fff';x4.shadowBlur=8;x4.fillRect(B.px,288,60,7);x4.shadowBlur=0;
 x4.fillStyle='#f85149';x3.shadowBlur=0;x4.beginPath();x4.arc(B.bx,B.by,6,0,7);x4.fill();
 if(B.dead){x4.fillStyle='rgba(248,81,73,.95)';x4.font='800 20px Segoe UI';x4.textAlign='center';x4.fillText('GAME OVER',150,140)}}
$('#b4').textContent=localStorage.getItem('g4')||0;g4draw();
addEventListener('keydown',e=>{if(document.querySelector('#v-games.active')){
 if(e.key==='ArrowUp')g1d(0,-1);if(e.key==='ArrowDown')g1d(0,1);if(e.key==='ArrowLeft'){g1d(-1,0);g2d(-1);g4d(-1)}if(e.key==='ArrowRight'){g1d(1,0);g2d(1);g4d(1)}
 if(e.key===' '){e.preventDefault();g3jump()}}});
/* BG */
const cv=$('#bg'),cx=cv.getContext('2d');let P=[];
function rs(){cv.width=innerWidth;cv.height=innerHeight}addEventListener('resize',rs);rs();
for(let i=0;i<42;i++)P.push({x:Math.random()*innerWidth,y:Math.random()*innerHeight,vx:(Math.random()-.5)*.4,vy:(Math.random()-.5)*.4});
(function bg(){cx.clearRect(0,0,cv.width,cv.height);
 for(const p of P){p.x+=p.vx;p.y+=p.vy;if(p.x<0||p.x>cv.width)p.vx*=-1;if(p.y<0||p.y>cv.height)p.vy*=-1}
 for(let i=0;i<P.length;i++){cx.beginPath();cx.arc(P[i].x,P[i].y,1.4,0,7);cx.fillStyle='rgba(248,81,73,.7)';cx.fill();
  for(let j=i+1;j<P.length;j++){const dx=P[i].x-P[j].x,dy=P[i].y-P[j].y,d=dx*dx+dy*dy;
   if(d<14000){cx.strokeStyle='rgba(248,81,73,'+(.1*(1-d/14000))+')';cx.beginPath();cx.moveTo(P[i].x,P[i].y);cx.lineTo(P[j].x,P[j].y);cx.stroke()}}}
 requestAnimationFrame(bg)})();
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function md(s){return s.replace(/```([\s\S]*?)```/g,(m,c)=>'<pre>'+c.replace(/^\n/,'')+'</pre>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*(.+?)\*\*/g,'<b>$1</b>')}
function openSidebar(){$('#sidebar').classList.add('open');$('#scrim').classList.add('show')}
function closeSidebar(){$('#sidebar').classList.remove('open');$('#scrim').classList.remove('show')}
if(!Object.keys(chats).length)newChat();else{if(!curId||!chats[curId])curId=Object.keys(chats)[0];renderS();renderC()}
</script>
</body>
</html>
"""


@app.get("/")
async def index():
    return HTMLResponse(HTML_PAGE)


@app.get("/api/health")
async def health():
    return JSONResponse({"status": "ok", "agent": "red-mind", "uncensored": True, "uptime": int(_tm.time() - BOOT_T)})


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
