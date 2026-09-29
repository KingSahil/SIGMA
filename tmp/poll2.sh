#!/usr/bin/env bash
SID=srv-datudj17lnhs73ep92tg
KEY=rnd_nCkdWlCjqBvxtPR7xfYJtLVaci9R
for i in $(seq 1 60); do
  OUT=$(curl -s -H "Authorization: Bearer $KEY" -H "Accept: application/json" "https://api.render.com/v1/services/$SID/deploys?limit=1")
  S=$(echo "$OUT" | python -c "import sys,json;print(json.load(sys.stdin)[0]['deploy']['status'])" 2>/dev/null)
  C=$(echo "$OUT" | python -c "import sys,json;print(str(json.load(sys.stdin)[0]['deploy'].get('commit',{}).get('id',''))[:8])" 2>/dev/null)
  echo "[$i] $(date +%H:%M:%S) $C status=$S"
  case "$S" in live|build_failed|update_failed|canceled|pre_deploy_failed) echo "TERMINAL:$S"; break;; esac
  sleep 10
done
