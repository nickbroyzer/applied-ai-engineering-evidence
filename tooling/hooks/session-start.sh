#!/bin/bash
# Generic session-start hook — works in any git repo
# Place in ~/.claude/hooks/ and reference from ~/.claude/settings.json

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$PROJECT_DIR" ]; then
    echo "Not in a git repository"
    exit 0
fi

PROJECT_NAME=$(basename "$PROJECT_DIR")

echo "========================================="
echo "  SESSION START: $PROJECT_NAME"
echo "========================================="
echo ""

# Git status
echo "📊 GIT STATUS:"
cd "$PROJECT_DIR"
git status --short
echo ""

# Recent commits
echo "📝 RECENT COMMITS:"
git log --oneline -5
echo ""

# Check for project-specific CLAUDE.md
if [ -f "$PROJECT_DIR/CLAUDE.md" ]; then
    echo "📋 PROJECT CONTEXT (CLAUDE.md):"
    head -50 "$PROJECT_DIR/CLAUDE.md"
    echo ""
fi

# Check if Flask app
if [ -f "$PROJECT_DIR/app.py" ]; then
    PORT=${APP_PORT:-5000}
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/" 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ]; then
        echo "✅ Flask server running on :$PORT"
    else
        echo "⚠️  Flask server not responding on :$PORT"
    fi
fi

echo "========================================="

# ========================================
# GSD ENFORCEMENT (NON-NEGOTIABLE)
# ========================================
echo ""
echo "⚠️  =================================="
echo "⚠️  MANDATORY: Type /gsd:progress NOW"
echo "⚠️  DO NOT proceed until GSD runs."
echo "⚠️  =================================="
echo ""

# Check for Obsidian session notes
if [ "$PROJECT_NAME" = "command-center-v7" ]; then
    OBSIDIAN_DIR="$HOME/Documents/Obsidian/MyVault/CC Project"
    APP_PORT=5003
elif [ "$PROJECT_NAME" = "my-assistant" ]; then
    OBSIDIAN_DIR="$HOME/Documents/Obsidian/MyVault/PC Project"
    APP_PORT=5001
fi

if [ -n "$OBSIDIAN_DIR" ] && [ -d "$OBSIDIAN_DIR" ]; then
    LATEST=$(ls -t "$OBSIDIAN_DIR"/Session-* 2>/dev/null | head -1)
    if [ -n "$LATEST" ]; then
        echo "📓 LATEST SESSION NOTE: $(basename "$LATEST")"
        echo "---"
        tail -20 "$LATEST"
        echo "---"
    else
        echo "⚠️  No session notes found in $OBSIDIAN_DIR"
    fi
fi
