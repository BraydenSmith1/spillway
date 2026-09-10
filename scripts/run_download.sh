#!/bin/bash
# run_download.sh — runs download_all.py under caffeinate, and restarts it
# automatically if it ever dies (network drop, crash, etc). Safe to re-run:
# download_all.py skips months already on disk.

cd "$(dirname "$0")/.."
source .venv/bin/activate

while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S')  starting download_all.py" >> logs/download_all.out
    caffeinate -i python -u scripts/download_all.py >> logs/download_all.out 2>&1
    echo "$(date '+%Y-%m-%d %H:%M:%S')  download_all.py exited (code $?) — restarting in 30s" >> logs/download_all.out
    sleep 30
done
