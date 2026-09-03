#!/usr/bin/env bash
set -u
export LC_ALL=C
cd "$(git rev-parse --show-toplevel)"
SNAPSHOT="docs/agents/build-map-facts.snapshot"
CURRENT="$(mktemp)"
trap 'rm -f "$CURRENT"' EXIT
section() { printf '\n===== %s =====\n' "$1" >> "$CURRENT"; }
: > "$CURRENT"

section "ROUTE FILES"
find mobile/app -type f \( -name '*.tsx' -o -name '*.ts' \) ! -name '_layout.tsx' | LC_ALL=C sort >> "$CURRENT"

section "TAB AND STACK DECLARATIONS"
find mobile/app -name '_layout.tsx' -exec grep -h "Tabs.Screen\|Stack.Screen\|name=" {} + 2>/dev/null | sed 's/^[[:space:]]*//' | LC_ALL=C sort >> "$CURRENT"

section "NAVIGATION CALLS"
grep -rnE "router\.(push|replace|navigate|dismissTo|back)\(|navigation\.navigate\(|<Redirect|<Link " mobile --include="*.tsx" --include="*.ts" 2>/dev/null | grep -v node_modules | grep -v "\.expo" | sed -E 's/:[0-9]+:/: /' | sed 's/^[[:space:]]*//' | LC_ALL=C sort >> "$CURRENT"

section "OBJECT-FORM NAV TARGETS"
grep -rn "pathname:" mobile --include="*.tsx" 2>/dev/null | grep -v node_modules | grep -v "\.expo" | sed -E 's/:[0-9]+:/: /' | sed 's/^[[:space:]]*//' | LC_ALL=C sort >> "$CURRENT"

section "TAB_ICONS KEYS"
awk '/const TAB_ICONS/,/^};/' mobile/components/FloatingTabBar.tsx >> "$CURRENT"

section "CLAIM ENDPOINT STATUS FILTERS"
grep -E "_ACTIVE_CLAIM_STATUSES|Claim\.status" backend/app/routers/claims.py | sed 's/^[[:space:]]*//' >> "$CURRENT"

section "NOTIFICATION TARGET TUPLES"
sed -n '/^THREAD_TARGET_CLAIM_NOTIFICATION_TYPES/,/^)/p' backend/app/services/notification_service.py >> "$CURRENT"
sed -n '/^NOTICE_TARGET_NOTIFICATION_TYPES/,/^)/p' backend/app/services/notification_service.py >> "$CURRENT"

section "TARGET RESOLVER BODY"
sed -n '/^def resolve_notification_target/,/^def _get_unread_count/p' backend/app/services/notification_service.py | sed '$d' >> "$CURRENT"

section "HUB TERMINAL CONSTANTS"
grep -E "TERMINAL_STATUSES|TERMINAL_COPY" "mobile/app/handoff/[claimId].tsx" | sed 's/^[[:space:]]*//' >> "$CURRENT"

section "HANDOFFS BUCKET FUNCTION"
awk '/^function bucketFor/,/^}/' mobile/components/HandoffsLanding.tsx >> "$CURRENT"

section "SETTINGS STUBS"
N=$(grep -c "notYetWired" mobile/app/settings/index.tsx 2>/dev/null || echo 0)
echo "notYetWired references: $N" >> "$CURRENT"

section "PUSH TAP HANDLER PRESENCE"
C=$(grep -rlE "ResponseReceived|LastNotificationResponse" mobile --include="*.ts" --include="*.tsx" 2>/dev/null | grep -v node_modules | wc -l | tr -d ' ')
echo "files with push-response APIs: $C" >> "$CURRENT"

if [ "${1:-}" = "--update" ]; then
  cp "$CURRENT" "$SNAPSHOT"
  echo "Snapshot re-baselined at $SNAPSHOT. Commit it TOGETHER with the updated map."
  exit 0
fi
if [ ! -f "$SNAPSHOT" ]; then
  cp "$CURRENT" "$SNAPSHOT"
  echo "First run: snapshot created at $SNAPSHOT. Commit it with the map."
  exit 0
fi
if diff -u "$SNAPSHOT" "$CURRENT" > /tmp/build-map-drift.txt 2>&1; then
  echo "BUILD MAP CLEAN. Source facts match the snapshot."
  exit 0
fi
echo "BUILD MAP DRIFT. The code moved under the map:"
cat /tmp/build-map-drift.txt
echo ""
echo "Fix: update docs/agents/zelbi-build-map.md, then: tools/check-build-map.sh --update"
echo "Commit map and snapshot together."
exit 1
