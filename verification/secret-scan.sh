#!/usr/bin/env bash
# Secret scan for this repository.
#
#   verification/secret-scan.sh [--env-file PATH]
#
# Three layers, run over every file git would publish (tracked plus untracked,
# minus .gitignore'd):
#
#   1. Generic patterns, listed below in full: provider key prefixes, PEM
#      blocks, credentialed URLs, DSNs, literal secret assignments, managed-host
#      suffixes, long hex/base64 runs, email addresses, absolute home paths.
#   2. Project literals, one per line, from verification/.scan-literals. That
#      file is gitignored, so the identifiers it searches for (hosts, account
#      ids, company and person names) never land in the repository.
#   3. With --env-file, every value in that env file (8+ characters, plus the
#      host of any URL value) is searched for. Values are read into memory only;
#      they are never written out, and a hit prints the variable NAME, never
#      the value.
#
# Output: one line per hit, "class<TAB>file:line", then counts per class.
# Exit 0 always; classifying hits as benign or not is a reading job, recorded
# in MANIFEST.md §4.
set -euo pipefail
cd "$(dirname "$0")/.."
ENV_FILE=""
if [[ "${1:-}" == "--env-file" ]]; then ENV_FILE="${2:?path required}"; fi
git ls-files -co --exclude-standard -z | ENV_FILE="$ENV_FILE" python3 -c '
import os, re, sys, collections
from urllib.parse import urlparse

GENERIC = {
    "stripe-key":      r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{8,}",
    "stripe-whsec":    r"\bwhsec_[A-Za-z0-9]{8,}",
    "anthropic-key":   r"\bsk-ant-[A-Za-z0-9_-]{10,}",
    "openai-key":      r"\bsk-(?:proj-)?[A-Za-z0-9]{20,}",
    "voyage-key":      r"\bpa-[A-Za-z0-9_-]{20,}",
    "aws-access-key":  r"\bAKIA[0-9A-Z]{16}\b",
    "google-api-key":  r"\bAIza[0-9A-Za-z_-]{35}",
    "github-token":    r"\bgh[pousr]_[A-Za-z0-9]{20,}",
    "slack-token":     r"\bxox[baprs]-[A-Za-z0-9-]{10,}",
    "twilio-sid":      r"\b(?:AC|SK)[0-9a-f]{32}\b",
    "supabase-key":    r"\bsb_(?:publishable|secret)_[A-Za-z0-9_-]{10,}",
    "jwt":             r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.",
    "pem-block":       r"-----BEGIN [A-Z ]*(?:PRIVATE KEY|CERTIFICATE)-----",
    "url-credentials": r"[a-z][a-z0-9+.-]*://[^/\s:@\x27\"]+:[^@\s\x27\"]+@",
    "sentry-dsn":      r"https://[0-9a-f]{32}@[^\s\x27\"]+",
    "postgres-dsn":    r"\bpostgres(?:ql)?(?:\+\w+)?://[^\s\x27\"`)]+",
    "secret-assign":   r"(?i)\b[\w-]*(?:api_?key|secret|token|password|passwd)[\w-]*\s*[:=]\s*[\x27\"][^\x27\"\s]{8,}[\x27\"]",
    "managed-host":    r"(?i)[a-z0-9-]+\.(?:supabase\.(?:co|com)|pooler\.supabase\.com|up\.railway\.app|r2\.dev|r2\.cloudflarestorage\.com|sentry\.io)\b",
    "long-hex":        r"\b[0-9a-f]{32,}\b",
    "long-b64":        r"(?<![A-Za-z0-9+/_-])[A-Za-z0-9+/_-]{40,}={0,2}",
    "email":           r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "home-path":       r"/(?:Users|home)/[A-Za-z0-9._-]+/",
}
pats = {k: re.compile(v) for k, v in GENERIC.items()}

needles = []  # (label, lowercase needle)
lit = "verification/.scan-literals"
if os.path.exists(lit):
    for i, line in enumerate(open(lit, encoding="utf-8"), 1):
        line = line.strip()
        if line and not line.startswith("#"):
            needles.append((f"literal:{lit}:{i}", line.lower()))

envf = os.environ.get("ENV_FILE")
if envf:
    text = open(envf, encoding="utf-8").read()
    for m in re.finditer(r"(?m)^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(\"(?:[^\"\\\\]|\\\\.)*\"|\x27[^\x27]*\x27|[^\n]*)", text):
        name, val = m.group(1), m.group(2).strip()
        if val[:1] in "\"\x27": val = val[1:-1]
        cands = [val] + val.splitlines()
        if "://" in val:
            host = urlparse(val).hostname or ""
            cands.append(host)
        for c in cands:
            c = c.strip()
            if len(c) >= 8 and c.lower() not in ("development", "production", "localhost"):
                needles.append((f"env:{name}", c.lower()))

hits = collections.Counter()
files = [f for f in sys.stdin.read().split("\0") if f]
for f in files:
    if f == lit or not os.path.isfile(f): continue
    try:
        lines = open(f, encoding="utf-8").read().splitlines()
    except UnicodeDecodeError:
        continue
    for n, line in enumerate(lines, 1):
        for k, p in pats.items():
            ms = p.findall(line)
            if k == "long-b64":  # a run of letters alone is a name, not a key
                ms = [x for x in ms if re.search(r"[a-z]", x) and re.search(r"[A-Z]", x) and re.search(r"[0-9]", x)]
            if ms:
                hits[k] += 1; print(f"{k}\t{f}:{n}")
        low = line.lower()
        for label, nd in needles:
            if nd in low:
                hits[label] += 1; print(f"{label}\t{f}:{n}")
print(f"--- {len(files)} files scanned; {len(pats)} generic patterns; {len(needles)} literal/env needles")
for k in sorted(hits): print(f"{hits[k]:6d}  {k}")
print(f"{sum(hits.values()):6d}  total")
'
