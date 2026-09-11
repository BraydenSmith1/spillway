#!/bin/bash
# run_download.sh — keeps the ERCOT download running unattended.
#
#   caffeinate -dimsu  prevents display / idle / disk / system sleep.
#     ⚠️  On BATTERY, macOS still sleeps when the lid closes — no software
#         flag overrides that. Keep the laptop plugged in.
#
#   Watchdog: a process hung on a dead socket never exits, so restarting
#     "on exit" isn't enough. If the log goes silent for STALL_SECS we
#     assume it's wedged, kill it, and start over. download.py resumes
#     from the last saved chunk, so a restart costs minutes at most.

set -u
cd "$(dirname "$0")/.."

LOG="logs/download_all.out"
# 30 min of silence = assumed hung. This must stay comfortably above the
# time between progress log lines, or the watchdog kills healthy work: at
# 900s it once killed a job 1,600 pages into a 1,798-page month, because
# slow pages pushed the gap between log lines right up against the limit.
STALL_SECS=1800
POLL=60

# Re-exec once under caffeinate so every child process is covered.
if [ -z "${UNDER_CAFFEINATE:-}" ]; then
    export UNDER_CAFFEINATE=1
    exec caffeinate -dimsu "$0" "$@"
fi

mkdir -p logs
source .venv/bin/activate

stamp() { date '+%Y-%m-%d %H:%M:%S'; }
log_mtime() { stat -f %m "$LOG" 2>/dev/null || echo 0; }

if pmset -g batt 2>/dev/null | grep -q "Battery Power"; then
    echo "$(stamp)  ⚠️  WARNING: running on battery. macOS will sleep on lid" >> "$LOG"
    echo "$(stamp)      close and the download will stall. Plug in." >> "$LOG"
fi

while true; do
    echo "$(stamp)  starting download_all.py" >> "$LOG"
    python -u scripts/download_all.py >> "$LOG" 2>&1 &
    PID=$!

    # Watch for stalls while it runs.
    while kill -0 "$PID" 2>/dev/null; do
        sleep "$POLL"
        AGE=$(( $(date +%s) - $(log_mtime) ))
        if [ "$AGE" -gt "$STALL_SECS" ]; then
            echo "$(stamp)  no output for ${AGE}s — assuming hung, restarting" >> "$LOG"
            kill -9 "$PID" 2>/dev/null
            break
        fi
    done

    wait "$PID" 2>/dev/null
    echo "$(stamp)  download_all.py exited — restarting in 30s" >> "$LOG"
    sleep 30
done
