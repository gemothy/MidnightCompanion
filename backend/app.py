#!/usr/bin/env python3
"""Midnight.City Companion — Backend State Service"""

from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime
import json, os, subprocess, urllib.request, urllib.error, urllib.parse

# Paths: skill root is parent of backend/
ROOT_DIR     = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
STATE_FILE   = os.path.join(ROOT_DIR, "state.json")

DEGA_API_URL  = os.environ.get("DEGA_API_URL",  "http://localhost:8080/api")
DEGA_GAME_URL = os.environ.get("DEGA_GAME_URL", "http://localhost:4000")

# PostgreSQL fallback (used when DEGA API server is not running)
_PG_CONTAINER = os.environ.get("DEGA_PG_CONTAINER", "dega-postgres")
_PG_USER      = os.environ.get("DEGA_PG_USER",      "dega")
_PG_DB        = os.environ.get("DEGA_PG_DB",         "dega")


def _query_agents_from_db():
    """Query agent list directly from PostgreSQL via docker exec — fallback when API is down."""
    sql = (
        "SELECT json_agg(row_to_json(t)) FROM ("
        "  SELECT ap.id, ap.name, ap.quadrant,"
        "         COALESCE(ai.current_status, 'offline') AS status,"
        "         COALESCE(ai.is_active, false) AS is_active"
        "  FROM agent_profiles ap"
        "  LEFT JOIN agent_instances ai ON ai.profile_id = ap.id"
        "  ORDER BY ap.name"
        ") t;"
    )
    result = subprocess.run(
        ["docker", "exec", "-i", _PG_CONTAINER,
         "psql", "-U", _PG_USER, "-d", _PG_DB,
         "--no-align", "--tuples-only", "-c", sql],
        capture_output=True, text=True, timeout=5
    )
    raw = result.stdout.strip()
    if not raw or raw == "\\N":
        return []
    return json.loads(raw) or []

# Local filesystem path to DEGA character sprite assets (relative to this repo layout)
_DEGA_CHARS_DIR = os.environ.get(
    "DEGA_CHARS_DIR",
    os.path.abspath(os.path.join(ROOT_DIR, "..", "controller-ai-minecraft",
                                  "apps", "game", "phaser-game", "assets", "characters"))
)

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="/static")

VALID_STATES = frozenset({"idle", "writing", "researching", "executing", "syncing", "error"})

INTERNAL_DETAIL_PATTERNS = (
    "compaction", "durable storage", "memory flush",
    "memory compaction", "pre-compaction", "context reset",
    "session startup", "read required files",
)

def _sanitize_detail(state: str, detail: str) -> str:
    if state != "idle":
        return detail
    if not detail:
        return ""
    lower = detail.lower()
    if any(p in lower for p in INTERNAL_DETAIL_PATTERNS):
        return "Waiting for tasks…"
    return detail

DEFAULT_STATE = {
    "state": "idle",
    "detail": "Waiting for tasks…",
    "progress": 0,
    "updated_at": datetime.now().isoformat()
}


def load_state():
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

    # Auto-idle: if a working state hasn't been updated in ttl_seconds, revert
    try:
        ttl = int(state.get("ttl_seconds", 120))
        updated_at = state.get("updated_at")
        s = state.get("state", "idle")
        if updated_at and s in {"writing", "researching", "executing"}:
            dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
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
                try:
                    save_state(state)
                except Exception:
                    pass
    except Exception:
        pass

    return state


def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


if not os.path.exists(STATE_FILE):
    save_state(DEFAULT_STATE)


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/status", methods=["GET"])
def get_status():
    return jsonify(load_state())


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "midnight-city-companion", "timestamp": datetime.now().isoformat()})


@app.route("/state", methods=["POST"])
def post_state():
    """Update state — OpenClaw uses this: POST {"state": "researching", "detail": "..."}"""
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


# ─── DEGA proxy (avoids CORS issues when fetching agent data) ─────────────────

@app.route("/dega/players", methods=["GET"])
def proxy_players():
    """Proxy GET /api/players from the DEGA game server — returns only agents currently in-game."""
    try:
        with urllib.request.urlopen(f"{DEGA_GAME_URL}/api/players", timeout=5) as resp:
            data = json.loads(resp.read())
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 502

@app.route("/dega/agents", methods=["GET"])
def proxy_agents():
    """Proxy GET /api/agents from DEGA — avoids CORS for the frontend.
    Falls back to direct PostgreSQL query when the DEGA API server is not running."""
    try:
        with urllib.request.urlopen(f"{DEGA_API_URL}/agents", timeout=3) as resp:
            data = json.loads(resp.read())
        return jsonify(data)
    except Exception:
        pass
    try:
        agents = _query_agents_from_db()
        return jsonify(agents)
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/dega/agents/<agent_id>", methods=["GET"])
def proxy_agent(agent_id):
    """Proxy GET /api/agents/:id from DEGA — falls back to PostgreSQL."""
    try:
        safe_id = urllib.parse.quote(agent_id, safe='')
        with urllib.request.urlopen(f"{DEGA_API_URL}/agents/{safe_id}", timeout=3) as resp:
            data = json.loads(resp.read())
        return jsonify(data)
    except Exception:
        pass
    # DB fallback: look up by UUID or by name (sanitize to prevent injection)
    try:
        safe = agent_id.replace("'", "''")  # escape single quotes for PostgreSQL
        sql = (
            "SELECT row_to_json(t) FROM ("
            "  SELECT ap.id, ap.name, ap.quadrant, ap.backstory,"
            "         ap.traits, ap.personality,"
            "         COALESCE(ai.current_status, 'offline') AS status,"
            "         COALESCE(ai.is_active, false) AS is_active"
            "  FROM agent_profiles ap"
            "  LEFT JOIN agent_instances ai ON ai.profile_id = ap.id"
            f" WHERE ap.id::text = '{safe}' OR ap.name ILIKE '{safe}'"
            "  LIMIT 1"
            ") t;"
        )
        result = subprocess.run(
            ["docker", "exec", "-i", _PG_CONTAINER,
             "psql", "-U", _PG_USER, "-d", _PG_DB,
             "--no-align", "--tuples-only", "-c", sql],
            capture_output=True, text=True, timeout=5
        )
        raw = result.stdout.strip()
        if raw and raw != "\\N":
            return jsonify(json.loads(raw))
        return jsonify({"error": "agent not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/dega/agents/<agent_id>/metrics", methods=["GET"])
def proxy_agent_metrics(agent_id):
    """Proxy GET /api/agents/:id/metrics from DEGA.
    Falls back to stats_cache + messages tables when the API is down."""
    try:
        safe_id = urllib.parse.quote(agent_id, safe='')
        with urllib.request.urlopen(f"{DEGA_API_URL}/agents/{safe_id}/metrics", timeout=3) as resp:
            data = json.loads(resp.read())
        return jsonify(data)
    except Exception:
        pass
    # DB fallback: build metrics from stats_cache leaderboard + message count
    try:
        safe = agent_id.replace("'", "''")
        # Leaderboard row for this agent (transactions, success rate)
        lb_sql = (
            "SELECT stat_value FROM stats_cache WHERE stat_key = 'leaderboard' LIMIT 1;"
        )
        lb_result = subprocess.run(
            ["docker", "exec", "-i", _PG_CONTAINER,
             "psql", "-U", _PG_USER, "-d", _PG_DB,
             "--no-align", "--tuples-only", "-c", lb_sql],
            capture_output=True, text=True, timeout=5
        )
        lb_raw = lb_result.stdout.strip()
        agent_lb = {}
        if lb_raw and lb_raw != "\\N":
            for entry in json.loads(lb_raw):
                if (entry.get("agent_name") or "").lower() == agent_id.lower():
                    agent_lb = entry
                    break
        # Message count as a proxy for total actions
        msg_sql = (
            f"SELECT count(*) FROM messages WHERE sender ILIKE '{safe}';"
        )
        msg_result = subprocess.run(
            ["docker", "exec", "-i", _PG_CONTAINER,
             "psql", "-U", _PG_USER, "-d", _PG_DB,
             "--no-align", "--tuples-only", "-c", msg_sql],
            capture_output=True, text=True, timeout=5
        )
        msg_count = int(msg_result.stdout.strip() or 0)

        successful = agent_lb.get("successful", 0)
        total_tx   = agent_lb.get("total_transactions", 0)
        failed     = agent_lb.get("failed", 0)
        rate       = round(successful / total_tx * 100) if total_tx > 0 else 0
        metrics = {
            "successRate": rate,
            "successfulActions": successful,
            "totalActions": total_tx,
            "failedActions": failed,
            "insightsLearned": msg_count,
        }
        return jsonify({"metrics": metrics})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


# ─── DEGA character sprite assets (served directly from local filesystem) ─────

import re as _re
_SLUG_RE = _re.compile(r'^[a-z][a-z0-9_]*$')

@app.route("/dega/character/<slug>/<filename>", methods=["GET", "HEAD"])
def proxy_character_asset(slug, filename):
    """Serve DEGA character sprites directly from the local checkout.
    Reads files straight from the filesystem — no dependency on game server HTTP.
    Allows: idle.png, walk.png, icon.png only (prevents path traversal).
    """
    from flask import send_from_directory, Response
    ALLOWED = {"idle.png", "walk.png", "icon.png"}
    if filename not in ALLOWED or not _SLUG_RE.match(slug):
        return Response("Not allowed", status=403)
    char_dir = os.path.join(_DEGA_CHARS_DIR, slug)
    file_path = os.path.join(char_dir, filename)
    if not os.path.isfile(file_path):
        return Response("Not found", status=404)
    resp = send_from_directory(char_dir, filename, mimetype="image/png")
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 19791))
    print("=" * 55)
    print("  Midnight.City Companion — Backend State Service")
    print("=" * 55)
    print(f"  State file : {STATE_FILE}")
    print(f"  DEGA API   : {DEGA_API_URL}")
    print(f"  Listening  : http://0.0.0.0:{port}")
    print("=" * 55)
    app.run(host="0.0.0.0", port=port, debug=False)
