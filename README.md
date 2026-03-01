# Midnight City Agent Companion

Official **midnight-city-skill**. A tiny "pixel office" status UI for your AI assistant.

- Pixel office background (top-down)
- A little character that moves between areas based on `state`
- Optional speech bubble / typing effect
- Mobile-friendly access via Cloudflare Tunnel quick tunnel

## What it looks like

- `idle / syncing / error` → breakroom area
- `writing / researching / executing` → desk area

The UI polls `/status` and renders the assistant avatar accordingly.

## Folder structure

```
star-office-ui/
  backend/        # Flask backend (serves index + status)
  frontend/       # Phaser frontend + office_bg.png
  state.json      # runtime status file
  set_state.py    # helper to update state.json
```

## Requirements

- Python 3.9+
- Flask

## Quick start (local)

### 1) Install dependencies

```bash
pip install flask
```

### 2) Put your background image

Put a **800×600 PNG** at:

```
star-office-ui/frontend/office_bg.png
```

### 3) Start backend

```bash
cd star-office-ui/backend
python app.py
```

Then open:

- http://127.0.0.1:18791

### 4) Update status

From the project root:

```bash
python3 star-office-ui/set_state.py writing "Working on a task..."
python3 star-office-ui/set_state.py idle "Standing by"
```

## Public access (Cloudflare quick tunnel)

Install `cloudflared`, then:

```bash
cloudflared tunnel --url http://127.0.0.1:18791
```

You’ll get a `https://xxx.trycloudflare.com` URL.

## Security notes

- Anyone with the tunnel URL can read `/status`.
- Don’t put sensitive info in `detail`.
- If needed, add a token check for `/status` (or only return coarse states).

## Repo

Official **midnight-city-skill**. Push to origin:

```bash
git push -u origin newmain
```

## License

MIT
