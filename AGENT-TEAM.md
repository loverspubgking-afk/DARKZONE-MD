# 🧠 RED-MIND — 3-Brain Agent Team Board

> **Shared board** — teeno Arena agents yahi se kaam claim karte hain, karte hain, update karte hain.
> **Repo hi single source of truth hai.** Har push se pehle pull karo.

## ⚙️ Protocol (har agent ke liye)
1. **Read:** Pehle yeh file aur `AGENT-BRIEF.md` parho.
2. **Claim:** Apna task `OPEN` → `IN-PROGRESS by <tumhara naam>` karo aur push karo.
3. **Kaam:** Chote commits karo. Doosre agent ke IN-PROGRESS files ko **mat chhedo**.
4. **Done:** Task `DONE by <naam>` + 2-3 lines mein kya kiya. Push.
5. **Conflict:** Push fail ho to pull karo, dobara try karo.
6. Backend pushes **khud live** ho jate hain (Kaggle server har 10 min auto-update karta hai). Frontend ke liye `frontend/deploy.py` chalao.

## 👥 Team
| Agent | Kaam | Status |
|---|---|---|
| **AGENT-A** (Romeo — Arena chat #1) | Parallel workers + per-role models + OmniRoute localhost fix + security hardening | ✅ DONE |
| **AGENT-B** (Arena chat #2 — tum) | AI Games: Heist Crew + Story Forge (backend + frontend) | 🟡 IN-PROGRESS by AGENT-B |
| **AGENT-C** (Arena chat #3 — tum) | Chat polish: markdown code-blocks + PWA + latency badge + share-link | 🟡 OPEN |

## 📋 Task Details

### AGENT-B: AI Games (Heist Crew + Story Forge)
- Backend (`app.py` + naya `games_ai.py`): `POST /api/game` — SSE events: `scene`, `choices`, `choice_result`, `game_over`
  - **Heist Crew:** 4 AI roles (Lookout, Hacker, Driver, Insider) — user plan banata hai, agents apne roles mein respond karte hain (omni workers reuse karo `agent_company.orchestrate` se seekh kar)
  - **Story Forge:** AI dungeon master — scene describe karo, 3 choices do, user choice par aage barho (history rakho)
- Frontend (`frontend/index.template.html`): `#view-games` mein dono `.aig.soon` cards ko real banao — modal/game panel, choices buttons, SSE handling (`sse()` helper already hai)
- Deploy: `python3 frontend/deploy.py`
- Test: server auto-update ke baad `curl -N -X POST <tunnel>/api/game -d '{"game":"story","message":"shuru karo"}'`

### AGENT-C: Chat Polish
- **Markdown rendering:** agent answers mein `**bold**`, `` `code` ``, ``` ```fenced``` ``` blocks — syntax highlight nahi chahiye, bas mono block + Copy button (XSS-safe: escape pehle, phir render)
- **PWA:** `manifest.json` (name RED-MIND, theme #0a0a0e, icon = inline SVG se 192/512 png ya SVG) + service worker (offline shell cache) — deploy files mein add karo
- **Latency badge:** har agent answer ke baad `RED-CORE · 2.4s` chhota chip (frontend timing se)
- **Share-chat:** ek session ka compressed `#c=base64` link — copy button
- Deploy: `python3 frontend/deploy.py`

## 📦 Backlog (koi bhi utha sakta hai jab apna task done ho)
- [ ] Stable tunnel (Oracle Cloud free tier — cardless signup nahi hota, research karo alternatives)
- [ ] Telegram bot (@BotFather token user dega)
- [ ] Voice mode (Urdu TTS)
- [ ] Chat mein images ka support
- [ ] Audit log for tools (destructive tools par tap-to-run confirm)

## 📝 Log (naya kaam upar likho)
- **2026-09-04 — AGENT-A:** parallel workers (ThreadPoolExecutor, 3 simultaneous) + `roleModels` param (har role ka apna model — mixed brain team) + OmniRoute localhost-first fix + CORS allowlist + device-scoped chats + rate limits + frontend v2 (hash routing, stop button, regenerate, honest stats, localStorage, cache-buster, security headers via vercel.json)
