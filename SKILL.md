---
name: midnight-city-skill
description: Push your current activity state to the Midnight.City pixel companion UI so the user sees their agent move and react in real time. Use whenever you are about to search, write, run commands, or finish a reply.
metadata:
  {
    "openclaw": { "emoji": "🌃", "title": "Midnight City", "color": "#7C3AED" }
  }
---

# Midnight.City Skill

## When to update the visual

**Do this every turn:** Before first search → set state `researching`. Before write/edit → `writing`. Before exec → `executing`. When done replying → `idle`. If you do not push state, the UI stays idle.

**HTTP (preferred if you have a request tool):**
POST to `http://localhost:19791/state` with JSON body:
- Starting to search/look something up: `{"state": "researching", "detail": "short description"}`
- Starting to write or edit: `{"state": "writing", "detail": "short description"}`
- Running commands or executing: `{"state": "executing", "detail": "short description"}`
- Done or waiting: `{"state": "idle", "detail": ""}`

**Script fallback:**
Run from skill root:
`~/.openclaw/skills/midnight-city-skill/.venv/bin/python ~/.openclaw/skills/midnight-city-skill/set_state.py researching "Looking up X"`
Valid states: `idle`, `writing`, `researching`, `executing`, `syncing`, `error`.

Use a brief, non-secret detail. The UI polls `/status` every 2 seconds, so the character will update shortly after.

## What you get
- Top-down pixel office companion UI (800×600, dark cyberpunk aesthetic)
- A pixel character that moves between areas based on `state`, with idle/talking/walk animations and speech bubbles
- Live DEGA city data feed — pass `?agentId=<uuid>` to watch a specific Midnight.City agent
- Optional public access via Cloudflare Tunnel quick tunnel

## State → area mapping
- `idle` / `syncing` / `error` → breakroom
- `writing` / `researching` / `executing` → workdesk (desk glows purple when active)

## DEGA live mode
Pass URL params to connect to a live Midnight.City simulation agent. The companion mirrors activity in real time via Socket.IO.

| Param | Default | Purpose |
|-------|---------|---------|
| `agentId` | — | Agent name (e.g. `Aerin Bloom`) — enables live mode |
| `dega` | `http://localhost:8080` | DEGA REST API (agent profiles, metrics) |
| `ws` | `http://localhost:4000` | DEGA game server Socket.IO (live events) |

**Example:**
```
http://localhost:19791/?agentId=Aerin%20Bloom&dega=http://localhost:8080&ws=http://localhost:4000
```

## Prerequisites
- Python 3 + Flask (`pip install flask`)
- An 800×600 PNG office background at `frontend/office_bg.png`
- Phaser loaded from CDN (no install)

## Quick start
```bash
cd MidnightCompanion-newmain
python3 -m venv .venv
.venv/bin/pip install flask
.venv/bin/python backend/app.py
# Open http://localhost:19791
```
Default port is 19791 (set `PORT` env var to override).

## State update script
```bash
python set_state.py <state> [detail]
python set_state.py idle
python set_state.py researching "Looking up Midnight Network docs..."
python set_state.py writing "Drafting the transaction..."
```

## Cloudflare Tunnel (mobile/public access)
```bash
cloudflared tunnel --url http://127.0.0.1:19791
# Use the https://xxx.trycloudflare.com URL on your phone
```

## Security
- Quick tunnel URLs can change; not for permanent production
- Anyone with the URL can see `state` and `detail` — don't put secrets in `detail`
