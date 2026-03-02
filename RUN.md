# Run Star Office UI & Restart OpenClaw

## Start the pixel office (Flask backend)

The skill is **installed**; the UI only works when the backend is **running** on port 19791.

```bash
bash ~/.openclaw/skills/star-office-ui/start.sh
```

Or from the skill directory:

```bash
cd ~/.openclaw/skills/star-office-ui && .venv/bin/python backend/app.py
```

Leave it running (or run it in the background / as a service). Then open **http://localhost:19791** (or use TUNNEL.md from another machine).

## Restart OpenClaw (gateway)

After changing OpenClaw config or dist patches, restart the gateway so it picks them up.

**If the gateway is installed as a service (systemd/launchd):**

```bash
openclaw gateway restart
```

**If you run the gateway in the foreground** (e.g. `openclaw gateway run`): stop it with Ctrl+C, then start again:

```bash
openclaw gateway run
```

**Check status:**

```bash
openclaw gateway status
```
