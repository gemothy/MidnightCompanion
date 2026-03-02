# MidnightCompanion

A pixel-art companion UI for the **DEGA** AI city simulation on the Midnight blockchain. Watch your chosen agent live — their location, state, conversations, and blockchain transactions — and chat with them in character, powered by Gemini.

---

## What it does

- **Live agent view** — Phaser 3 canvas streams the selected agent's sprite, room, and idle/walking/talking animations from the DEGA game server in real time
- **Status bar** — shows agent name, current state (`researching`, `executing`, `idle`, etc.) and who they're talking to, driven by Socket.IO game events
- **Event log** — compact notification feed of chat, movement, arrivals, and MCP blockchain transactions as they happen
- **Stats panel** — success rate, action count, and insight count pulled from the DEGA API (with PostgreSQL DB fallback)
- **In-character chat** — send a message; Gemini 2.0 Flash responds as the agent using their real personality traits, backstory, and recent memories fetched from DEGA
- **Lofi radio** — 📻 background music toggle with multiple streams
- **Mobile-first layout** — two-row top bar, safe-area insets, centered controls, touch-friendly targets
- **LAN access** — open from any device on the same network; DEGA connections auto-resolve from the page hostname

---

## Architecture

```
Phone / Browser
      │
      │  http://<mac-ip>:19792
      ▼
Flask backend (port 19792)
  ├─ Serves frontend/index.html (Phaser 3 + Socket.IO client)
  ├─ GET  /dega/agents          → proxy → DEGA API :8080
  ├─ GET  /dega/agents/:id      → proxy → DEGA API :8080  (avoids CORS)
  ├─ GET  /dega/agents/:id/metrics
  ├─ GET  /dega/character/:slug/:file → proxy → DEGA asset server
  └─ POST /chat                 → Gemini 2.0 Flash (in-character reply)

Frontend (browser)
  ├─ Socket.IO → DEGA game server :4000/io   (viewer events)
  ├─ Socket.IO → DEGA game server :4000/bot  (Companion bot presence)
  └─ REST      → Flask /dega/*               (agent data, chat)
```

---

## Quick start

### Requirements

- Python 3.9+
- DEGA game server running on `:4000`
- DEGA AI agent server running on `:8080`
- `GOOGLE_API_KEY` environment variable (for in-character chat)

### Install & run

```bash
cd MidnightCompanion-newmain
python -m venv .venv
.venv/bin/pip install flask flask-cors requests
.venv/bin/python backend/app.py
```

Or via Claude Code launch config:

```bash
# .claude/launch.json entry: "midnight-companion" → port 19792
```

Open in browser: **http://localhost:19792**

From your phone (same WiFi): **http://192.168.x.x:19792**

---

## URL parameters

| Param | Default | Description |
|---|---|---|
| `agentId` | — | Agent name to follow (e.g. `Avelin Verdant`) |
| `dega` | `http://<hostname>:8080` | DEGA REST API base URL |
| `ws` | `http://<hostname>:4000` | DEGA game server Socket.IO URL |

Example:
```
http://localhost:19792/?agentId=Avelin+Verdant
```

---

## In-character chat

The `/chat` endpoint:
1. Fetches the agent's profile from DEGA (`/api/agents/:id`) — personality traits, tone, backstory
2. Fetches their 6 most recent unique memories from ChromaDB
3. Builds a system prompt from that context
4. Calls Gemini 2.0 Flash and returns an in-character response

The response appears as a speech bubble above the agent sprite and in the chat log.

> **Note:** The chat bypasses the DEGA cognitive loop — it uses Gemini directly. Agent-to-agent conversations inside DEGA are the ones that affect trust scores and memories. See `INTEGRATION.md` for the roadmap to make Companion chat truly persistent.

---

## Mobile layout

```
┌─────────────────────────────────┐
│ [Avelin Verdant •] [📻] [Default]│  ← row 1: controls
│   Avelin Verdant · Talking…      │  ← row 2: status
│                                  │
│           [game canvas]          │
│                                  │
│ [stats]        [💬 Chat]  [events]│  ← bottom zone
│           MIDNIGHT.CITY          │
└─────────────────────────────────┘
```

---

## Public access

```bash
# Cloudflare quick tunnel (no account needed)
cloudflared tunnel --url http://127.0.0.1:19792
```

You'll get a `https://xxx.trycloudflare.com` URL shareable with anyone.

---

## License

MIT
