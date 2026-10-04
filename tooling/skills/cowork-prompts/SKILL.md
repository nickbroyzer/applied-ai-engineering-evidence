# Cowork Prompt Standards

## Core Rule
Every Cowork prompt MUST be a single, fully copy-pasteable code block. No instructions outside the block. No multi-block sequences.

## Required Ending (every prompt, no exceptions)
The LAST two steps inside every Cowork code block must always be:

1. (second-to-last) "Display a summary of all changes made with a copy button so it can be pasted back into the Claude chat window."
2. (last) "Save a screenshot of the final result to /Users/nickbroyzer/Desktop/<project>-Screenshots/[descriptive-name].png"

## Layout Verification Variant
When verifying a CSS/layout change via Cowork, the prompt must include these steps in order:

1. Describe what CSS change was made (so Cowork has context)
2. Refresh the browser at the correct localhost URL
3. Navigate to the specific section/tab where the change applies
4. Wait for full page load
5. "Display a summary of all changes made with a copy button so it can be pasted back into the Claude chat window."
6. "Save a screenshot of the final result to /Users/nickbroyzer/Desktop/<project>-Screenshots/[descriptive-name].png"

## Screenshot Fallback
If Cowork fails (known issue: screenshot failures, random permission prompts), use manual fallback:
1. Cmd+Shift+5 to capture
2. Save to /Users/nickbroyzer/Desktop/<project>-Screenshots/
3. Drag screenshot into Claude chat

## Known Cowork Limitations
- Cannot log into sites
- Random Apple Music/microphone permission prompts — always deny
- Screenshot failures happen intermittently — retry once, then use manual fallback
- Do NOT use Cowork for tasks requiring authentication
