#!/bin/bash
# Cleanup old Reasoning Engines in europe-west1.
#
# For each displayName, keep the most recently UPDATED engine,
# delete every older one.
#
# Usage:
#   ./cleanup_old_engines.sh           # dry-run (prints plan, deletes nothing)
#   ./cleanup_old_engines.sh --apply   # actually delete

set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-gb-poc-373711}"
LOCATION="${LOCATION:-europe-west1}"
APPLY=false

if [[ "${1:-}" == "--apply" ]]; then
  APPLY=true
fi

echo "Project:  ${PROJECT_ID}"
echo "Location: ${LOCATION}"
echo "Mode:     $([[ "${APPLY}" == "true" ]] && echo "APPLY (deleting)" || echo "DRY-RUN (no deletion)")"
echo

TOKEN=$(gcloud auth print-access-token)
LIST_URL="https://${LOCATION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${LOCATION}/reasoningEngines?pageSize=200"

echo "--- Fetching engines ---"
TMP_JSON=$(mktemp)
trap 'rm -f "${TMP_JSON}"' EXIT
curl -s -H "Authorization: Bearer ${TOKEN}" "${LIST_URL}" > "${TMP_JSON}"
TOTAL=$(python -c "import json; print(len(json.load(open('${TMP_JSON}')).get('reasoningEngines',[])))")
echo "Found ${TOTAL} engines."
echo

# For each displayName, identify the newest by updateTime; everything else is a delete candidate.
PLAN=$(python <<PY
import json
from collections import defaultdict

with open("${TMP_JSON}") as f:
    data = json.load(f)
engines = data.get("reasoningEngines", [])

by_name = defaultdict(list)
for e in engines:
    by_name[e.get("displayName", "<no-display-name>")].append({
        "id": e["name"].split("/")[-1],
        "updateTime": e.get("updateTime", ""),
    })

keep, delete = [], []
for display, items in by_name.items():
    items.sort(key=lambda x: x["updateTime"], reverse=True)
    keep.append((display, items[0]))
    for old in items[1:]:
        delete.append((display, old))

print(f"KEEP_COUNT={len(keep)}")
print(f"DELETE_COUNT={len(delete)}")
print("---KEEP---")
for display, e in keep:
    print(f"{display}|{e['id']}|{e['updateTime']}")
print("---DELETE---")
for display, e in delete:
    print(f"{display}|{e['id']}|{e['updateTime']}")
PY
)

KEEP_COUNT=$(echo "${PLAN}" | grep "^KEEP_COUNT=" | cut -d= -f2)
DELETE_COUNT=$(echo "${PLAN}" | grep "^DELETE_COUNT=" | cut -d= -f2)

echo "--- KEEP (${KEEP_COUNT}) ---"
echo "${PLAN}" | awk '/^---KEEP---/{p=1;next} /^---DELETE---/{p=0} p' | column -t -s '|'
echo
echo "--- DELETE (${DELETE_COUNT}) ---"
echo "${PLAN}" | awk '/^---DELETE---/{p=1;next} p' | column -t -s '|'
echo

if [[ "${APPLY}" != "true" ]]; then
  echo "Dry-run complete. Re-run with --apply to actually delete the ${DELETE_COUNT} engines."
  exit 0
fi

echo "Deleting ${DELETE_COUNT} engines..."
DELETE_IDS=$(echo "${PLAN}" | awk '/^---DELETE---/{p=1;next} p' | cut -d'|' -f2)

FAILED=0
SUCCESS=0
for ID in ${DELETE_IDS}; do
  DELETE_URL="https://${LOCATION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${LOCATION}/reasoningEngines/${ID}?force=true"
  HTTP=$(curl -s -o /tmp/del-${ID}.out -w "%{http_code}" -X DELETE -H "Authorization: Bearer ${TOKEN}" "${DELETE_URL}")
  if [[ "${HTTP}" == "200" ]]; then
    echo "  ✓ ${ID} delete kicked off (long-running operation)"
    SUCCESS=$((SUCCESS+1))
  else
    echo "  ✗ ${ID} HTTP ${HTTP} : $(head -c 200 /tmp/del-${ID}.out)"
    FAILED=$((FAILED+1))
  fi
  rm -f /tmp/del-${ID}.out
done

echo
echo "Done. ${SUCCESS} delete operations started, ${FAILED} failures."
echo "Note: deletes are long-running. Re-run the dry-run in 1-2 min to confirm."
