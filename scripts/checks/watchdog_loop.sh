#!/bin/bash
set -u

cd /home/wyy/pet-action-recognition

while true; do
  ./scripts/checks/monitor_pipeline.sh > /tmp/monitor_latest.log 2>&1
  rc=$?
  if (( rc != 0 )); then
    echo "[WATCHDOG $(date '+%Y-%m-%d %H:%M:%S')] ALARM: monitor_pipeline returned $rc" >> .run/logs/alarms.log
    cat /tmp/monitor_latest.log >> .run/logs/alarms.log
  fi
  sleep 120
done
