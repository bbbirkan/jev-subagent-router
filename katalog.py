#!/usr/bin/env python3
"""Weekly model catalog for the three free/subscription routes: agy, codex, claude.

For every model+reasoning level the CLIs currently offer, attach the Artificial Analysis
intelligence score and the OpenRouter price (relative cost; the CLIs are quota, not dollars).
New models show up automatically: agy/codex are listed by their own CLIs, Claude Sonnet/Opus
are taken as the newest versions AA knows.

  python3 katalog.py guncelle    # writes katalog.json (fails if coverage is too low)
  python3 katalog.py goster      # prints the catalog
  python3 katalog.py --demo      # no network
"""
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import os
AA_URL = "https://artificialanalysis.ai/api/v2/data/llms/models"
KATALOG = Path(__file__).with_name("katalog.json")
ROTA_SIRA = {"agy": 0, "codex": 1, "claude": 2}  # free first, Opus-quota last
SEVIYE = ("low", "medium", "high", "xhigh", "max")


def _tok(s: str) -> set:
    return set(re.sub(r"[^a-z0-9.]+", " ", s.lower().replace("-", " ")).split()) - {"", "effort", "adaptive", "reasoning"}


def aa_eslestir(ad: str, aa: list):
    """Pick the AA entry whose name contains every token of `ad` with the fewest extra tokens."""
    hedef = _tok(ad)
    aday = [(len(_tok(m["name"]) - hedef), m) for m in aa if hedef <= _tok(m.get("name", ""))]
    if not aday:
        return None
    m = min(aday, key=lambda x: x[0])[1]
    return (m.get("evaluations") or {}).get("artificial_analysis_intelligence_index")


def agy_modelleri() -> list:
    out = subprocess.run(["agy", "models"], capture_output=True, text=True, timeout=120).stdout
    seen, res = set(), []
    for line in out.splitlines():
        m = re.match(r"^([a-z0-9][a-z0-9.\-]+)\t(.+)$", line.strip())
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            res.append({"rota": "agy", "id": m.group(1), "ad": m.group(2).strip(), "efor": None})
    return res


def codex_modelleri() -> list:
    out = subprocess.run(["codex", "debug", "models"], capture_output=True, text=True, timeout=120).stdout
    res = []
    for m in json.loads(out[out.index("{"):])["models"]:
        if m.get("visibility") != "list":
            continue
        for lv in m.get("supported_reasoning_levels", []):
            e = lv["effort"]
            if e in SEVIYE:
                res.append({"rota": "codex", "id": m["slug"], "ad": f"{m['display_name'].replace('-', ' ')} ({e})", "efor": e})
    return res


def claude_modelleri(aa: list) -> list:
    """Newest Sonnet and Opus AA knows (= what the 'sonnet'/'opus' aliases resolve to) + Haiku."""
    res = []
    for aile in ("Sonnet", "Opus"):
        surumler = {re.search(rf"Claude {aile} ([\d.]+)", m["name"]).group(1)
                    for m in aa if re.search(rf"^Claude {aile} [\d.]+ \(", m.get("name", ""))}
        if not surumler:
            continue
        v = max(surumler, key=lambda s: tuple(int(x) for x in s.split(".")))
        for e in SEVIYE:
            res.append({"rota": "claude", "id": aile.lower(), "ad": f"Claude {aile} {v} ({e})", "efor": e,
                        "or_id": f"anthropic/claude-{aile.lower()}-{v}"})
    res.append({"rota": "claude", "id": "haiku", "ad": "Claude 4.5 Haiku (Reasoning)", "efor": None,
                "or_id": "anthropic/claude-haiku-4.5"})
    return res


def or_fiyatlari() -> dict:
    with urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=60) as r:
        data = json.loads(r.read())["data"]
    return {m["id"]: (float(m["pricing"]["prompt"]) * 1e6, float(m["pricing"]["completion"]) * 1e6) for m in data}


def or_bul(k: dict, fiyat: dict):
    if k.get("or_id") in fiyat:
        return fiyat[k["or_id"]]
    base = re.sub(r"-(low|medium|high|xhigh|max)$", "", k["id"])
    for oid, p in fiyat.items():
        if oid.split("/")[-1].replace(".", "-") == base.replace(".", "-"):
            return p
    return None


def aa_getir() -> list:
    """AA model list. Key from env AA_API_KEY (free at artificialanalysis.ai)."""
    anahtar = os.environ.get("AA_API_KEY")
    if not anahtar:
        raise SystemExit("AA_API_KEY yok: export AA_API_KEY=... (artificialanalysis.ai, free)")
    req = urllib.request.Request(AA_URL, headers={"x-api-key": anahtar})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["data"]


def guncelle():
    aa = aa_getir()
    fiyat = or_fiyatlari()
    modeller = agy_modelleri() + codex_modelleri() + claude_modelleri(aa)
    for k in modeller:
        k["aa"] = aa_eslestir(k["ad"], aa)
        p = or_bul(k, fiyat)
        k["fiyat"] = list(p) if p else None
    olculen = [k for k in modeller if k["aa"] is not None]
    rotalar = {k["rota"] for k in olculen}
    # Swallowed error = fake result: refuse to overwrite a good catalog with a broken one.
    if len(olculen) < len(modeller) * 0.5 or rotalar != set(ROTA_SIRA):
        raise SystemExit(f"KAPSAM YETERSIZ: {len(olculen)}/{len(modeller)} AA eslesti, rotalar={sorted(rotalar)} — katalog yazilmadi")
    KATALOG.write_text(json.dumps({"tarih": time.strftime("%Y-%m-%d %H:%M"), "modeller": modeller},
                                  indent=1, ensure_ascii=False))
    print(f"katalog: {len(modeller)} model, {len(olculen)} AA olculu -> {KATALOG}")


def goster():
    d = json.loads(KATALOG.read_text())
    print(f"katalog tarihi {d['tarih']}")
    for k in sorted(d["modeller"], key=lambda k: -(k["aa"] or -1)):
        f = f"{k['fiyat'][0]:.2f}/{k['fiyat'][1]:.2f}" if k["fiyat"] else "-"
        print(f"  {k['rota']:6} {k['ad']:42} AA {k['aa'] if k['aa'] is not None else '-':>5}  $ {f}")


def demo():
    aa = [{"name": "GPT-6.1 Sol (High)", "evaluations": {"artificial_analysis_intelligence_index": 50.2}},
          {"name": "GPT-6.1 Sol (Max)", "evaluations": {"artificial_analysis_intelligence_index": 51.8}},
          {"name": "Claude Sonnet 5.5 (Adaptive Reasoning, High Effort)", "evaluations": {"artificial_analysis_intelligence_index": 46.8}},
          {"name": "Claude Sonnet 5 (Adaptive Reasoning, High Effort)", "evaluations": {"artificial_analysis_intelligence_index": 40}},
          {"name": "Gemini 3.8 Flash (High)", "evaluations": {"artificial_analysis_intelligence_index": 40.9}}]
    assert aa_eslestir("GPT 6.1 Sol (high)", aa) == 50.2
    assert aa_eslestir("Claude Sonnet 5.5 (high)", aa) == 46.8
    assert aa_eslestir("Gemini 3.8 Flash (High)", aa) == 40.9
    assert aa_eslestir("Gemini 9 Ultra", aa) is None
    assert claude_modelleri(aa)[0]["ad"] == "Claude Sonnet 5.5 (low)"
    print("demo TAMAM")


if __name__ == "__main__":
    {"guncelle": guncelle, "goster": goster, "--demo": demo}.get(sys.argv[-1], demo)()
