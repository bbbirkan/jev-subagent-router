#!/usr/bin/env bash
# Weekly: update CLIs safely -> rebuild model catalog -> push to GitHub. Cron runs it under flock.
set -u
cd /root/2026-alt-ajan-secici
LOG=/root/logs/alt_ajan_haftalik.log
{ echo "=== $(date '+%F %T')"
  bash cli_guncelle.sh
  export AA_API_KEY="${AA_API_KEY:-$(grep -m1 -E '^(export )?AA_API_KEY=' "$HOME/.sovereign_env" 2>/dev/null | cut -d= -f2- | tr -d "\"'")}"
  python3 katalog.py guncelle || echo "KATALOG GUNCELLENEMEDI (eski katalog duruyor)"
  if ! git diff --quiet -- katalog.json; then
    git add katalog.json && git commit -qm "weekly catalog $(date +%F)" && git push -q origin HEAD || echo "PUSH HATASI"
  fi
} >>"$LOG" 2>&1
