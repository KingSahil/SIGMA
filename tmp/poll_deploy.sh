#!/usr/bin/env bash
SID=srv-datudj17lnhs73ep92tg
KEY=rnd_nCkdWlCjqBvxtPR7xfYJtLVaci9R
for i in $(seq 1 90); do
  OUT=$(curl -s -H "Authorization: Bearer $KEY" -H "Accept: application/json" "https://api.render.com/v1/services/$SID/deploys?limit=1")
  STATUS=$(echo "$OUT" | python -c "import sys,json;print(json.load(sys.stdin)[0]['deploy']['status'])" 2>/dev/null)
  echo "[$i] $(date +%H:%M:%S) status=$STATUS"
  case "$STATUS" in
    live|build_failed|update_failed|canceled|pre_deploy_failed|deactivated) echo "TERMINAL:$STATUS"; break;;
  esac
  sleep 10
done
