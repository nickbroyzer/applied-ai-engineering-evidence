#!/bin/bash
# Generic pre-compact hook — saves state before context compaction
# Place in ~/.claude/hooks/ and reference from ~/.claude/settings.json

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$PROJECT_DIR" ]; then
    exit 0
fi

STATE_DIR="$PROJECT_DIR/.claude/state"
mkdir -p "$STATE_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
STATE_FILE="$STATE_DIR/pre-compact-$TIMESTAMP.md"

{
    echo "# Pre-Compact State Snapshot"
    echo "Timestamp: $(date)"
    echo "Project: $(basename "$PROJECT_DIR")"
    echo ""
    echo "## Git Status"
    cd "$PROJECT_DIR"
    git status --short
    echo ""
    echo "## Uncommitted Changes"
    git diff --stat
    echo ""
    echo "## Recent Commits"
    git log --oneline -5
} > "$STATE_FILE"

echo "State saved to $STATE_FILE"
