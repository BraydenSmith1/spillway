#!/bin/bash
# run_sced.sh — catches up the 60-day SCED disclosure downloads.
#
# download_sced.py writes one file per day and skips days already on disk,
# so this both backfills old gaps and pulls newly-published days. It is not
# part of download_all.py, which is why it fell 100+ days behind.
#
# Same protections as run_download.sh: caffeinate so the Mac stays awake,
# and restart if it dies. Per-day files mean a restart loses one day at most.

set -u
cd "$(dirname "$0")/.."

LOG="logs/sced_catchup.log"

if [ -z "${UNDER_CAFFEINATE:-}" ]; then
    export UNDER_CAFFEINATE=1
    exec caffeinate -dimsu "$0" "$@"
fi

mkdir -p logs
source .venv/bin/activate

stamp() { date '+%Y-%m-%d %H:%M:%S'; }

while true; do
    echo "$(stamp)  starting download_sced.py" >> "$LOG"
    python -u scripts/download_sced.py >> "$LOG" 2>&1
    CODE=$?
    echo "$(stamp)  download_sced.py exited (code $CODE)" >> "$LOG"

    # Clean exit means it walked every day in range — nothing left to do.
    if [ "$CODE" -eq 0 ]; then
        echo "$(stamp)  caught up. stopping." >> "$LOG"
        break
    fi
    echo "$(stamp)  restarting in 30s" >> "$LOG"
    sleep 30
done
