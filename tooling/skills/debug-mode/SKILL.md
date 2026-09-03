---
name: debug-mode
description: Use when a bug persists after an initial fix attempt, when root cause is unclear from the traceback alone, or when the user explicitly says "debug mode". Do NOT use for obvious single-line errors with clear tracebacks.
---

# Debug Mode

Hypothesis-driven, instrumented debugging optimized for Claude Code's terminal-first workflow.

**Announce at start:** "Entering Debug Mode. I will hypothesize, instrument, reproduce, analyze, fix, and verify."
**State Tracking:** At the top of EVERY response during this workflow, print `[Current Phase: X]`.

## Quick-Check Gate (Before the Full Loop)

Before committing to the full 8-phase loop, spend 60 seconds on a quick check:

1. Read the full error/traceback
2. `grep` the suspect line and its immediate context
3. If the root cause is obvious (typo, wrong variable, missing import, off-by-one) → fix it, verify, done

**Enter the full loop ONLY if:** the quick check doesn't reveal a clear single root cause, or a previous quick fix already failed.

---

## The Loop

```
Phase 0: SAFETY     → git stash + isolated branch
Phase 1: DISCOVER   → scan project tools, test infra, recent changes
Phase 2: HYPOTHESIZE → 3-5 ranked theories with required evidence
Phase 3: REPRODUCE  → write test/script AND COMMIT IT (isolate repro from debug logs)
Phase 4: INSTRUMENT → add [DEBUG-MODE] tagged logs (dirtying the working tree)
Phase 5: ANALYZE    → run reproduction, capture logs to file, correlate
Phase 6: RESET      → git restore . (perfectly removes all debug logs)
Phase 7: FIX        → implement fix at root cause
Phase 8: VERIFY     → mandatory red-to-green check
```

**Iron Laws:**
```
1. NO FIXES WITHOUT REPRODUCTION FIRST.
2. NO GUESSING — INSTRUMENT AND OBSERVE.
3. NEVER HANG THE TERMINAL — detach background processes safely.
4. PROTECT YOUR CONTEXT — never dump raw logs, always grep/tail to files.
5. RESET BEFORE FIXING — use git restore to remove debug logs, never manual edits.
```

---

## Phase 0: Safety Branch

**BEFORE touching any code:**

```bash
git stash push -m "pre-debug-mode-stash"
git checkout -b debug-mode/$(date +%Y%m%d-%H%M%S)
```

If git is not available, proceed but note that manual cleanup will be required in Phase 6.

---

## Phase 1: Project Discovery

Scan the environment to know your tools:

1. **Runner:** `package.json` scripts, `Makefile`, `Taskfile`, or `docker-compose.yml`
2. **Tests:** Find test directories and frameworks (jest, vitest, pytest)
3. **History:** `git log --oneline -10 -- <suspect-path>` to see recent changes

**Output:** Mental model of what you can run and what changed recently.

---

## Phase 2: Hypothesize

Generate **3-5 ranked hypotheses**.

```
H<N>: <short-name>
  Theory: <what is wrong>
  Evidence needed: <what would prove this>
  Likely files: <where to look>
```

Investigate most likely first.

---

## Phase 3: Reproduce and Isolate (CRITICAL)

A bug you cannot reproduce is a bug you cannot fix.

### Reproduction Strategies (Priority Order)

1. **Standalone repro script** (fastest) — `repro.py` or `repro.js` that imports the code and triggers the bug directly
2. **Failing unit test** (gold standard) — write a test in the native framework
3. **curl / HTTP** — for API bugs: `curl -v -X POST localhost:5000/api/endpoint -H 'Content-Type: application/json' -d '{"trigger": "bug"}'`
4. **Loop for flaky bugs** — `for i in $(seq 1 50); do python repro.py && echo "PASS" || echo "FAIL <<<"; done`
5. **Manual** (last resort) — ask user for exact reproduction steps

### Bash Safety: Background Processes

If starting a server for reproduction, **YOU MUST DETACH IT**:

```bash
nohup python app.py > server.log 2>&1 &
SERVER_PID=$!
sleep 3
curl -s localhost:5000/api/trigger-bug
kill $SERVER_PID 2>/dev/null
```

**NEVER** run `python app.py` or `flask run` without `nohup ... &`.

### The Commit Hack (KEY INSIGHT)

Once you have a failing reproduction, **commit it immediately**:

```bash
git add repro.py
git commit -m "chore: add failing reproduction for debug-mode"
```

**Why:** In Phase 6, `git restore .` instantly removes all debug instrumentation. Your repro survives because it's committed. Manual log deletion causes syntax errors and hanging brackets.

| Bug Type | Best Strategy |
|----------|--------------|
| Logic error | 1 (standalone) or 2 (test) |
| API response wrong | 3 (curl) |
| Race condition / flaky | 4 (loop 50x) |
| State corruption | 1 (repro script) |
| Caching | 2 (test) |

**CRITICAL:** Do NOT proceed to instrumentation until you can reproduce the bug.

---

## Phase 4: Instrument

Add **hypothesis-tagged** debug logs to suspect code paths.

### Log Format

```
[DEBUG-MODE][H<N>-<hypothesis-name>][<function-name>] <message>
```

### Language Patterns

**Python (stderr):**
```python
import sys
print(f'[DEBUG-MODE][H1-stale-cache][get_user_profile] cache_key={cache_key} hit={cached is not None}', file=sys.stderr)
```

**JavaScript/TypeScript (stderr):**
```typescript
console.error('[DEBUG-MODE][H1-stale-cache][getUserProfile] cache key:', cacheKey, 'hit:', !!cached);
```

### What to Log

For each hypothesis, instrument the **decision points**:
- Function entry (arguments received)
- Branch taken (which if/else path)
- External call (what was sent, what came back)
- State mutation (before and after)
- Function exit (return value)

---

## Phase 5: Analyze (Protect Context)

Run the reproduction with instrumentation in place.

### Context Window Protection

**DO NOT dump raw logs to stdout.** Route to a file and query it:

```bash
python repro.py > debug.log 2>&1
grep '\[DEBUG-MODE\]' debug.log
grep '\[DEBUG-MODE\]\[H1' debug.log | tail -n 20
```

**NEVER** let a command dump unbounded output. Always pipe through `grep`, `head`, or `tail`.

### Analysis Verdict

For each hypothesis:
```
H<N> ANALYSIS:
  Expected: <what logs should show if hypothesis is correct>
  Actual:   <what logs actually show>
  Verdict:  CONFIRMED / REFUTED / INCONCLUSIVE
  Evidence: <paste relevant log lines>
```

**Max 3 instrumentation iterations.** If still inconclusive after 3 rounds, re-evaluate hypotheses and consider asking user for more context.

---

## Phase 6: Reset (Clean Slate)

Once a hypothesis is CONFIRMED:

```bash
git restore .
```

Your repro test/script survives because you committed it in Phase 3. All `[DEBUG-MODE]` logs vanish instantly.

---

## Phase 7: Fix

**Only after hypothesis is CONFIRMED and workspace is CLEAN (Phase 6).**

1. Fix at ROOT CAUSE, not symptom
2. Minimal change — don't refactor during a bugfix
3. Fix ONLY what the log evidence pointed to

---

## Phase 8: Verify (Red to Green)

```bash
# 1. Run the repro — MUST PASS (GREEN)
python repro.py

# 2. Temporarily stash the fix
git stash push -m "temp-verify-fix"

# 3. Run the repro — MUST FAIL (RED)
python repro.py

# 4. Restore the fix
git stash pop
```

**If the test passes without the fix, it's a bad test.** Rewrite it.

### Finalize

1. Integrate repro scripts into the actual test suite as permanent regression tests
2. Delete temporary files (`repro.py`, `debug.log`, `server.log`)
3. Run full test suite — no regressions
4. Commit:

```
fix: <short description>

Root cause: <one sentence>
Evidence: <what logs/tests revealed>
Regression test: <test file and test name>
```

---

## Quick Reference

```
QUICK-CHECK GATE:
  Read traceback → grep context → obvious? Fix and verify. Done.
  Not obvious or quick fix failed? → Enter full loop.

FULL LOOP:
  0. git stash + branch
  1. Discover project tools
  2. Hypothesize (3-5 ranked theories)
  3. Reproduce AND COMMIT the repro
  4. Instrument ([DEBUG-MODE][H<N>-name][func] key=value)
  5. Analyze (logs to file, grep, protect context)
  6. Reset (git restore .)
  7. Fix (root cause only, minimal change)
  8. Verify (green → stash → red → pop)

BASH SAFETY:
  nohup python app.py > server.log 2>&1 &
  NEVER run long processes without detaching.

CONTEXT SAFETY:
  Always: command > file.log 2>&1 then grep
  Never: let raw output flood stdout
```

---

## Red Flags — STOP

- "Let me just try a quick fix..." → STOP. Did you reproduce?
- "Obviously it's..." → STOP. Where's the evidence?
- "I don't need to instrument..." → STOP. Instrument anyway.
- "The test passes so we're done..." → STOP. Did you verify red-to-green?
- "I'll clean up the logs manually..." → STOP. Use `git restore .`
- Starting a server without `nohup ... &` → STOP. You'll hang.
- Dumping raw logs to stdout → STOP. Route to file, then grep.
