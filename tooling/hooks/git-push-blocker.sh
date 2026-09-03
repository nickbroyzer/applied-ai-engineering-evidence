#!/bin/bash
# Generic git push blocker — prevents push without QA verification
# Triggered on PreToolUse when command contains "git push"
# Place in ~/.claude/hooks/ and reference from ~/.claude/settings.json

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$PROJECT_DIR" ]; then
    exit 0
fi

VERIFICATION_FLAG="$PROJECT_DIR/.claude/state/.qa-verified"

# Check if this is a git push command
if echo "$1" | grep -q "git push"; then
    if [ ! -f "$VERIFICATION_FLAG" ]; then
        echo "========================================="
        echo "  ⛔ PUSH BLOCKED — QA NOT VERIFIED"
        echo "========================================="
        echo ""
        echo "Run QA verification before pushing:"
        echo "  1. Visual verification (screenshot)"
        echo "  2. API endpoint tests (curl)"
        echo "  3. Browser console check (no errors)"
        echo "  4. Run: touch $VERIFICATION_FLAG"
        echo ""
        echo "Then retry the push."
        exit 1
    else
        # Clear the flag after successful push
        rm -f "$VERIFICATION_FLAG"
        echo "✅ QA verified — push allowed"
    fi
fi

exit 0
