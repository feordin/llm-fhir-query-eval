#!/usr/bin/env bash
# Load the full MIMIC-IV upload set into ONE Microsoft FHIR instance:
#   wipe -> verify empty -> POST $import (IncrementalLoad) -> poll -> verify counts.
# Usage: bash scripts/load_mimic_server.sh <appname> <import-body.json>
#   e.g. bash scripts/load_mimic_server.sh jaerwinllm2 /path/to/mimic-import-body.json
# Import config (Import enabled, blob RBAC) must already be set (June 2026 runbook).
set -uo pipefail
cd "$(dirname "$0")/.."
APP="$1"; BODY="$2"; URL="https://${APP}.azurewebsites.net"

count() { curl -sk --max-time 60 "$URL/$1?_summary=count" 2>/dev/null \
  | python -c "import json,sys
try: print(json.load(sys.stdin).get('total',-1))
except Exception: print(-1)"; }

echo "[$APP] wiping..."
FHIR_RELOAD_URL="$URL" python scripts/reload_phenotype.py --wipe-only anything \
  >/dev/null 2>&1 || { echo "[$APP] WIPE SCRIPT FAILED"; exit 1; }
for rt in Patient Condition Observation MedicationRequest Encounter Procedure; do
  n=$(count "$rt")
  [[ "$n" == "0" ]] || { echo "[$APP] NOT EMPTY after wipe: $rt=$n"; exit 1; }
done
echo "[$APP] wiped + verified empty"

resp_headers=$(curl -sk -D - -o /dev/null --max-time 120 -X POST "$URL/\$import" \
  -H "Content-Type: application/fhir+json" -H "Prefer: respond-async" \
  --data-binary @"$BODY")
status_url=$(echo "$resp_headers" | grep -i "^Content-Location:" | awk '{print $2}' | tr -d '\r')
code=$(echo "$resp_headers" | head -1 | awk '{print $2}')
[[ "$code" == "202" && -n "$status_url" ]] || { echo "[$APP] IMPORT NOT ACCEPTED: HTTP $code"; echo "$resp_headers" | head -5; exit 1; }
# Poll over https regardless of what the server echoes back.
status_url="${status_url/http:/https:}"
echo "[$APP] import accepted: $status_url"

t0=$(date +%s)
while true; do
  sleep 300
  pcode=$(curl -sk -o "/tmp/${APP}_import.json" -w "%{http_code}" --max-time 90 "$status_url" 2>/dev/null)
  el=$(( $(date +%s) - t0 ))
  if [[ "$pcode" == "200" ]]; then
    echo "[$APP] IMPORT COMPLETE after ${el}s"
    break
  elif [[ "$pcode" == "202" ]]; then
    echo "[$APP] ...${el}s running"
  else
    echo "[$APP] ...${el}s poll HTTP $pcode (transient, retrying)"
  fi
  if (( el > 64800 )); then echo "[$APP] TIMEOUT after 18h"; exit 1; fi
done

ok=1
for spec in Patient:299712 Condition:5655376 Encounter:929499 Observation:16596671 \
            Procedure:3354975 MedicationRequest:15416901 Medication:26027 Location:39 Organization:1; do
  rt="${spec%%:*}"; want="${spec##*:}"; got=$(count "$rt")
  if [[ "$got" == "$want" ]]; then echo "[$APP] VERIFY $rt: $got OK"
  else echo "[$APP] VERIFY $rt: got $got want $want MISMATCH"; ok=0; fi
done
[[ $ok -eq 1 ]] && echo "[$APP] ALL VERIFIED" || { echo "[$APP] VERIFICATION FAILED"; exit 1; }
