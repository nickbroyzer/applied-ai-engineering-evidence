#!/bin/bash
# Generic session-end hook — creates session summary
# Triggered on Stop event
# Place in ~/.claude/hooks/ and reference from ~/.claude/settings.json

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$PROJECT_DIR" ]; then
    exit 0
fi

PROJECT_NAME=$(basename "$PROJECT_DIR")
SESSION_DIR="$PROJECT_DIR/.claude/sessions"
mkdir -p "$SESSION_DIR"

DATE=$(date +%Y-%m-%d)
SESSION_FILE="$SESSION_DIR/Session-$DATE.md"

# Only create if doesn't exist (don't overwrite mid-session)
if [ ! -f "$SESSION_FILE" ]; then
    {
        echo "# Session: $DATE"
        echo "Project: $PROJECT_NAME"
        echo ""
        echo "## Git Status at Session End"
        cd "$PROJECT_DIR"
        git status --short
        echo ""
        echo "## Commits This Session"
        git log --oneline --since="$(date +%Y-%m-%d) 00:00:00" 2>/dev/null || echo "No commits today"
        echo ""
        echo "## Notes"
        echo "<!-- Add session notes here -->"
    } > "$SESSION_FILE"
    
    echo "📝 Session file created: $SESSION_FILE"
fi
