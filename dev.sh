#!/bin/bash
# Launch backend (top) + frontend (bottom) in a tmux split
# Usage: ./dev.sh [--mock]

SESSION="dash"
DIR="$(cd "$(dirname "$0")" && pwd)"

# Kill existing session if any
tmux kill-session -t "$SESSION" 2>/dev/null

if [ "$1" = "--mock" ]; then
    API_CMD="NO_ROBOT=1 uv run uvicorn server.main:app --reload --port 8543"
else
    API_CMD="uv run uvicorn server.main:app --reload --port 8543"
fi

WEB_CMD="cd frontend && pnpm dev"

# Create session with backend in top pane
tmux new-session -d -s "$SESSION" -c "$DIR" "$API_CMD"
tmux rename-window -t "$SESSION" "dev"

# Split horizontally (top/bottom) and run frontend in bottom pane
tmux split-window -v -t "$SESSION" -c "$DIR" "$WEB_CMD"

# Give top pane (api) 60% height
tmux select-layout -t "$SESSION" even-vertical

# Select top pane
tmux select-pane -t "$SESSION:0.0"

# Attach
tmux attach -t "$SESSION"
