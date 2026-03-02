#!/usr/bin/env bash
# Start the Star Office UI backend (Flask on port 19791).
# Run from anywhere: bash ~/.openclaw/skills/star-office-ui/start.sh
cd "$(dirname "$0")"
exec .venv/bin/python backend/app.py
