#!/bin/bash
# Generic JS syntax check — runs after any .js file edit
# Triggered on PostToolUse for file edits
# Place in ~/.claude/hooks/ and reference from ~/.claude/settings.json

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$PROJECT_DIR" ]; then
    exit 0
fi

# Get the file that was just edited (passed as argument)
EDITED_FILE="$1"

# Only check JS files
if [[ "$EDITED_FILE" == *.js ]]; then
    echo "🔍 Checking JS syntax: $EDITED_FILE"
    
    if node --check "$EDITED_FILE" 2>&1; then
        echo "✅ Syntax OK"
    else
        echo "❌ SYNTAX ERROR — fix before continuing"
        exit 1
    fi
fi

# Check for console.log in production code (warning only)
if [[ "$EDITED_FILE" == *.js ]] && grep -q "console.log" "$EDITED_FILE" 2>/dev/null; then
    COUNT=$(grep -c "console.log" "$EDITED_FILE")
    echo "⚠️  Warning: $COUNT console.log statement(s) found in $EDITED_FILE"
fi

exit 0
