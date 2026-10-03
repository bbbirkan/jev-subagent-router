#!/usr/bin/env python3
"""PreToolUse hook on Agent: a subagent may start only if secici.py ran in the last 15 minutes.

Every Agent call is logged (allowed or not) so usage can be counted:
  python3 ajan_kapisi.py --rapor     # last 7 days: Agent calls vs. how many went through secici
A broken log never blocks work (fail-open), but the error is logged.
"""
import json
import sys
import time
from pathlib import Path

SECIM_LOG = Path("/root/logs/alt_ajan_secim.jsonl")
KAPI_LOG = Path("/root/logs/alt_ajan_kapi.jsonl")
PENCERE = 15 * 60
MUAF = {"fork", "claude-code-guide", "statusline-setup"}  # context forks / harness helpers, not delegated work


def son_secim() -> float:
    try:
        return json.loads(SECIM_LOG.read_text().strip().splitlines()[-1])["ts"]
    except Exception:
        return 0.0


def karar(girdi: dict, simdi: float, son: float) -> tuple:
    tip = (girdi.get("tool_input") or {}).get("subagent_type") or "general-purpose"
    if tip in MUAF:
        return True, f"muaf ({tip})"
    if simdi - son <= PENCERE:
        return True, "secici yakin zamanda calisti"
    return False, ("Önce JEV seçicisini çalıştır: python3 /root/2026-alt-ajan-secici/secici.py \"<görev>\" — "
                   "1. sıra agy/codex ise işi orada yap; claude çıkarsa Agent'ı verdiği model ile tekrar çağır.")


def main():
    try:
        girdi = json.load(sys.stdin)
    except Exception:
        return
    izin, sebep = karar(girdi, time.time(), son_secim())
    ti = girdi.get("tool_input") or {}
    try:
        with KAPI_LOG.open("a") as f:
            f.write(json.dumps({"ts": time.time(), "tip": ti.get("subagent_type"), "model": ti.get("model"),
                                "izin": izin, "sebep": sebep}, ensure_ascii=False) + "\n")
    except Exception:
        pass
    if not izin:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": "deny", "permissionDecisionReason": sebep}}))


def rapor():
    hafta = time.time() - 7 * 86400
    satirlar = [json.loads(x) for x in KAPI_LOG.read_text().splitlines() if x.strip()] if KAPI_LOG.exists() else []
    s = [x for x in satirlar if x["ts"] >= hafta and not x["sebep"].startswith("muaf")]
    izinli = sum(x["izin"] for x in s)
    print(f"son 7 gün: {len(s)} Agent çağrısı, {izinli} secici sonrası, {len(s) - izinli} kapıdan döndü")


def demo():
    g = lambda t: {"tool_input": {"subagent_type": t}}
    assert karar(g("Explore"), 1000, 0)[0] is False
    assert karar(g("Explore"), 1000, 900)[0] is True
    assert karar(g("fork"), 1000, 0)[0] is True
    assert karar({}, 1000, 0)[0] is False
    print("demo TAMAM")


if __name__ == "__main__":
    {"--demo": demo, "--rapor": rapor}.get(sys.argv[-1], main)()
