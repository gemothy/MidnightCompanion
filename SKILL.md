---
name: star-office-ui
slug: midnight-city-skill
description: Push your current activity to the Star Office pixel UI (researching, writing, executing, idle) so the human sees the character move. Use whenever you are about to search, write, run commands, or finish a reply.
metadata:
  {
    "openclaw": { "emoji": "🏢", "title": "Star Office", "color": "#ff6b35", "official": true }
  }
---

# Star Office UI Skill

## When to update the visual

**Do this every turn:** Before first search → set state researching. Before write/edit → writing. Before exec → executing. When done replying → idle. If you do not push state, the UI stays idle.**

**Option A – HTTP (preferred if you have a request tool):**  
POST to `http://localhost:19791/state` with JSON body:
- Starting to search/look something up: `{"state": "researching", "detail": "short description"}`
- Starting to write or edit: `{"state": "writing", "detail": "short description"}`
- Running commands or executing: `{"state": "executing", "detail": "short description"}`
- Done or waiting: `{"state": "idle", "detail": ""}`

**Option B – Script:**  
Run from skill root, e.g.  
`~/.openclaw/skills/star-office-ui/.venv/bin/python ~/.openclaw/skills/star-office-ui/set_state.py researching "Looking up X"`  
Valid states: `idle`, `writing`, `researching`, `executing`, `syncing`, `error`.

Use a brief, non-secret detail. The UI polls `/status` every few seconds, so the character will update shortly after.

## What you get
- Top-down pixel office background (draw your own, generate with AI, or use stock art)
- A pixel character that moves between areas based on `state`, with idle/talking animations and speech bubbles
- Optional public access via Cloudflare Tunnel quick tunnel

## Prerequisites
- A machine that can run Python (server or local)
- An 800×600 PNG office background (top-down pixel style works best)
- Python 3 + Flask
- Phaser from CDN (no install; frontend loads it)

## Quick start

### 1. Directory layout
```bash
mkdir -p star-office-ui/backend star-office-ui/frontend
```

### 2. Background image
Put your office background at `star-office-ui/frontend/office_bg.png`

### 3. Backend (Flask)
Create `star-office-ui/backend/app.py` (see repo for full code). It serves:
- `/` — the pixel office UI (index.html)
- `/status` — current state JSON
- `/health` — health check

### 4. Frontend (Phaser)
The frontend loads the office background and the character sprite sheets (idle + talking). It maps states to areas (workdesk vs breakroom) and shows bubbles and a typewriter status line.

### 5. State update script
Use `set_state.py` in the skill root:
```bash
python set_state.py <state> [detail]
```
Valid states: `idle`, `writing`, `researching`, `executing`, `syncing`, `error`

Examples:
```bash
python set_state.py idle
python set_state.py researching "Looking up docs..."
python set_state.py writing "Drafting the report..."
```

### 6. Run the backend
```bash
cd star-office-ui
python3 -m venv .venv
.venv/bin/pip install flask
.venv/bin/python backend/app.py
```
Default port is 19791 (set `PORT` if needed). Open http://localhost:19791

### 7. Cloudflare Tunnel (optional, for mobile/public access)
- Install cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/tunnel-guide/local/
- Run a quick tunnel:
  ```bash
  cloudflared tunnel --url http://127.0.0.1:19791
  ```
- Use the `https://xxx.trycloudflare.com` URL on your phone

## State → area mapping (customizable)
- `idle` / `syncing` / `error` → breakroom
- `writing` / `researching` / `executing` → workdesk

## Security
- Quick tunnel URLs can change; not for permanent production
- Anyone with the URL can see `state` and `detail` — don’t put secrets in `detail`
- For stricter privacy: add auth on `/status`, or return only coarse state

## Effects (included)
- Random small steps within the current area
- Idle vs talking animation (sprite sheets)
- Occasional speech bubbles (short phrases per state)
- Typewriter effect on the status line
- Slight vertical wobble while moving
