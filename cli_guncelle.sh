#!/usr/bin/env bash
# Weekly safe update of agy / codex / claude CLIs so new models appear, without touching settings.
# For each CLI: back up its config files, run its own update, verify it still runs; if the
# config changed or the binary is broken, restore the config (binary rollback is not possible:
# log it loudly so a human sees it).
set -u
LOG=/root/logs/alt_ajan_cli_guncelle.log
YEDEK=/root/2026-alt-ajan-secici/_yedek/$(date +%Y%m%d)
mkdir -p "$YEDEK" "$(dirname "$LOG")"
say() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }

guncelle() {  # name, update-cmd, version-cmd, config files...
  local ad=$1 upd=$2 ver=$3; shift 3
  local once; once=$($ver 2>&1 | head -1)
  for f in "$@"; do [ -f "$f" ] && cp -p "$f" "$YEDEK/$ad.$(basename "$f")"; done
  timeout 600 bash -c "$upd" >>"$LOG" 2>&1 < /dev/null || say "$ad: update komutu hata verdi (devam)"
  local sonra; sonra=$($ver 2>&1 | head -1)
  if ! timeout 60 $ver >/dev/null 2>&1; then say "$ad: KIRIK — '$ver' calismiyor, elle bak (yedek $YEDEK)"; fi
  for f in "$@"; do
    local y="$YEDEK/$ad.$(basename "$f")"
    if [ -f "$y" ] && ! cmp -s "$f" "$y"; then cp -p "$y" "$f"; say "$ad: $f degismisti -> geri yuklendi"; fi
  done
  say "$ad: $once -> $sonra"
}

guncelle claude "claude update" "claude --version" /root/.claude/settings.json
guncelle codex "codex update" "codex --version" /root/.codex/config.toml
guncelle agy "agy update" "agy --version" /root/.gemini/GEMINI.md /root/.gemini/antigravity-cli/AGENTS.md
