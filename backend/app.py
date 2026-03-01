#!/usr/bin/env python3
"""Star Office UI - Backend State Service"""

from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime
import json
import os

# Paths: skill root is parent of backend/
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
STATE_FILE = os.path.join(ROOT_DIR, "state.json")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="/static")

VALID_STATES = frozenset({"idle", "writing", "researching", "executing", "syncing", "error"})

# Detail text that should not be shown in the UI (internal/system messages)
INTERNAL_DETAIL_PATTERNS = (
    "compaction",
    "durable storage",
    "memory flush",
    "memory compaction",
    "pre-compaction",
    "context reset",
    "session startup",
    "read required files",
)

def _sanitize_detail(state: str, detail: str) -> str:
    """Replace internal/system detail with a generic idle message."""
    if state != "idle":
        return detail
    if not detail:
        return ""
    lower = detail.lower()
    if any(p in lower for p in INTERNAL_DETAIL_PATTERNS):
        return "Waiting for tasks…"
    return detail

# Default state
DEFAULT_STATE = {
    "state": "idle",
    "detail": "Waiting for tasks…",
    "progress": 0,
    "updated_at": datetime.now().isoformat()
}


def load_state():
    """Load state from file.

    Includes a simple auto-idle mechanism:
    - If the last update is older than ttl_seconds (default 120s)
      and the state is a "working" state, we fall back to idle.

    This avoids the UI getting stuck at the desk when no new updates arrive.
    """
    state = None
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = None

    if not isinstance(state, dict):
        state = dict(DEFAULT_STATE)

    # Normalize legacy Chinese detail to English
    d = (state.get("detail") or "").strip()
    if d in ("等待任务中...", "待命中...", "待命中"):
        state["detail"] = "Waiting for tasks…"

    # Auto-idle
    try:
        ttl = int(state.get("ttl_seconds", 120))
        updated_at = state.get("updated_at")
        s = state.get("state", "idle")
        working_states = {"writing", "researching", "executing"}
        if updated_at and s in working_states:
            # tolerate both with/without timezone
            dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            # Use UTC for aware datetimes; local time for naive.
            if dt.tzinfo:
                from datetime import timezone
                age = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds()
            else:
                age = (datetime.now() - dt).total_seconds()
            if age > ttl:
                state["state"] = "idle"
                state["detail"] = "Idle (auto-returned to breakroom)"
                state["progress"] = 0
                state["updated_at"] = datetime.now().isoformat()
                # persist the auto-idle so every client sees it consistently
                try:
                    save_state(state)
                except Exception:
                    pass
    except Exception:
        pass

    return state


def save_state(state: dict):
    """Save state to file"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# Initialize state
if not os.path.exists(STATE_FILE):
    save_state(DEFAULT_STATE)


@app.route("/", methods=["GET"])
def index():
    """Serve the pixel office UI"""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/status", methods=["GET"])
def get_status():
    """Get current state"""
    state = load_state()
    return jsonify(state)


@app.route("/health", methods=["GET"])
def health():
    """Health check"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


@app.route("/state", methods=["POST"])
def post_state():
    """Update state (for agents: POST JSON {"state": "researching", "detail": "..."})."""
    data = request.get_json(silent=True) or {}
    s = (data.get("state") or "").strip().lower()
    if s not in VALID_STATES:
        return jsonify({"error": "invalid state", "valid": list(VALID_STATES)}), 400
    state = load_state()
    state["state"] = s
    raw_detail = (data.get("detail") or "").strip() or state.get("detail", "")
    state["detail"] = _sanitize_detail(s, raw_detail) or raw_detail
    state["updated_at"] = datetime.now().isoformat()
    if "progress" in data:
        state["progress"] = int(data["progress"]) if data["progress"] is not None else 0
    save_state(state)
    return jsonify(state)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 19791))
    print("=" * 50)
    print("Star Office UI - Backend State Service")
    print("=" * 50)
    print(f"State file: {STATE_FILE}")
    print(f"Listening on: http://0.0.0.0:{port}")
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=False)
