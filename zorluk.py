#!/usr/bin/env python3
"""Task difficulty via JEV, OpenRouter's public decision model (~typesafe/jev-latest).

JEV returns a structured choice with probabilities, not prose: ~0.3 s and a tiny fraction of a
cent per call. Needs OPENROUTER_API_KEY. Biased low on purpose: a level is only raised when JEV
is confident, and risky topics (data loss, security, real money, irreversible) get at least `high`.

  python3 zorluk.py "find the root cause of this bug"
  python3 zorluk.py --demo
"""
import json
import os
import re
import sys
import urllib.request

URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = "~typesafe/jev-latest"
SEVIYELER = ("low", "medium", "high", "xhigh", "max")
MEDIUM_ESIK, HIGH_ESIK, XHIGH_ESIK = 0.8, 0.9, 0.75
RISK = re.compile(r"data loss|security|leak|real money|live account|irreversible|delete prod|"
                  r"veri kayb|g[uü]venlik|s[ıi]z[ıi]nt|ger[cç]ek para|geri al[ıi]namaz", re.I)
SORU = {"efor": {
    "type": "choice",
    "instructions": ("Pick the reasoning effort a strong coding assistant needs for this user request. "
                     "Prefer the cheapest level that fully handles it."),
    "criteria": {
        "low": "trivial: greeting, yes/no, continue, tiny lookup or status question",
        "medium": "routine edit, short explanation, simple command",
        "high": "multi-step task, debugging, several files, careful analysis",
        "xhigh": "hard design decision, subtle bug, strategy or money at stake",
    }}}


def decide(state: dict, questions: dict) -> dict:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    req = urllib.request.Request(URL, data=json.dumps({"model": MODEL, "state": state, "questions": questions}).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def sec(cevap: dict, metin: str) -> str:
    """JEV answer -> level, raising only on confidence; risky topics floor at high."""
    c = (cevap or {}).get("efor", {})
    secim, p = c.get("choice"), c.get("probabilities", {})
    if secim not in SEVIYELER:
        secim = "medium"
    p_x = p.get("xhigh", 0) + p.get("max", 0)
    if secim in ("xhigh", "max"):
        secim = "xhigh" if p_x >= XHIGH_ESIK else "high"
    if secim == "high" and p.get("high", 0) + p_x < HIGH_ESIK:
        secim = "medium"
    if secim == "medium" and 1 - p.get("low", 0) < MEDIUM_ESIK:
        secim = "low"
    if RISK.search(metin) and SEVIYELER.index(secim) < 2:
        secim = "high"
    return secim


def zorluk(metin: str) -> str:
    try:
        return sec(decide({"text": metin[:4000]}, SORU).get("answers"), metin)
    except Exception:
        return "medium"  # JEV unreachable: middle bar, routing still works


def demo():
    J = lambda s, p: {"efor": {"choice": s, "probabilities": p}}
    assert sec(J("low", {"low": .99}), "fix typo") == "low"
    assert sec(J("high", {"medium": .45, "high": .55}), "write a test") == "medium"
    assert sec(J("xhigh", {"high": .21, "xhigh": .79}), "redesign the engine") == "xhigh"
    assert sec(J("medium", {"medium": .9}), "migrate the DB without data loss") == "high"
    assert sec(None, "anything") == "medium"
    print("demo TAMAM")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else print(zorluk(sys.argv[-1]))
