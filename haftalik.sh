#!/usr/bin/env bash
# Weekly: update CLIs safely -> rebuild model catalog -> push to GitHub. Cron runs it under flock.
set -u
cd "$(dirname "$0")"
LOG_DIR=${JEV_LOG_DIR:-$HOME/.jev-router/logs}; mkdir -p "$LOG_DIR"
LOG=$LOG_DIR/alt_ajan_haftalik.log
{ echo "=== $(date '+%F %T')"
  bash cli_guncelle.sh
  export AA_API_KEY="${AA_API_KEY:-$(grep -m1 -E '^(export )?AA_API_KEY=' "${KEY_FILE:-$HOME/.env}" 2>/dev/null | cut -d= -f2- | tr -d "\"'")}"
  python3 katalog.py guncelle || echo "KATALOG GUNCELLENEMEDI (eski katalog duruyor)"
  if ! git diff --quiet -- katalog.json; then
    git add katalog.json && git commit -qm "weekly catalog $(date +%F)" && git push -q origin HEAD || echo "PUSH HATASI"
  fi
} >>"$LOG" 2>&1
