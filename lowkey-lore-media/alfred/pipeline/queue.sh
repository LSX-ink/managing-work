#!/bin/sh
# queue.sh v1 v2 ... : render each video in turn (GPU), encoding + QC the previous one meanwhile (CPU).
# Waits for any render already running (an existing frames/ render_log without DONE) to finish first.
cd "$(dirname "$0")/.."
Q=out/queue_log.txt
for arg in "$@"; do
  v=${arg%%:*}; V=videos/$v
  while pgrep -f blender >/dev/null 2>&1 || tasklist //FI "IMAGENAME eq blender.exe" 2>/dev/null | grep -q blender.exe; do sleep 30; done
  case "$arg" in *:resume) ;; *) rm -rf $V/frames $V/cams ;; esac   # name:resume keeps frames already rendered
  rm -f $V/out/*-nopause.mp4
  echo "$(date +%H:%M) RENDER $v" >> $Q
  if .venv/Scripts/python.exe pipeline/make.py $V lint render > $V/make_log.txt 2>&1; then
    ( .venv/Scripts/python.exe pipeline/make.py $V encode pause phone sheet caption qc >> $V/make_log.txt 2>&1; echo "$(date +%H:%M) DONE $v exit=$?" >> $Q ) &
  else
    echo "$(date +%H:%M) LINT/RENDER FAILED $v" >> $Q
  fi
done
wait
echo "$(date +%H:%M) QUEUE EMPTY" >> $Q
