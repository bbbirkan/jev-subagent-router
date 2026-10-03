#!/usr/bin/env python3
"""JEV subagent router: task text -> which route/model/effort, plus a fallback chain.

JEV (via /root/scripts/jev_efor.py) rates the task difficulty; that sets a minimum AA score.
Among catalog models meeting it, routes are tried free-first (agy -> codex -> claude), and
inside a route the lightest/cheapest adequate model wins, so big-model quota is saved for
hard work. A route whose quota ran out is skipped until its cooldown ends.

  python3 secici.py "summarize these three logs"     # chain, best first
  python3 secici.py --json "task"
  python3 secici.py --kota-bitti codex [hours]        # mark quota exhausted (default 5h)
  python3 secici.py --demo
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "/root/scripts")
DIR = Path(__file__).parent
KATALOG = DIR / "katalog.json"
KOTA = DIR / "kota.json"
SECIM_LOG = Path("/root/logs/alt_ajan_secim.jsonl")
ROTA_SIRA = {"agy": 0, "codex": 1, "claude": 2}
SEVIYE = ("low", "medium", "high", "xhigh", "max")
MIN_AA = {"low": 30, "medium": 38, "high": 46, "xhigh": 51, "max": 55}


def komut(k: dict) -> str:
    if k["rota"] == "agy":
        return f'agy --print "<istem>" --model {k["id"]}'
    if k["rota"] == "codex":
        return f'codex exec -m {k["id"]} -c model_reasoning_effort={k["efor"]} "<istem>"'
    return f'Agent(model="{k["id"]}")' + (f'  # effort {k["efor"]}' if k["efor"] else "")


def efor_sira(k: dict) -> int:
    e = k.get("efor") or next((x for x in SEVIYE if k["id"].endswith("-" + x)), "high")
    return SEVIYE.index(e)


def kota_kapali(simdi=None) -> set:
    try:
        d = json.loads(KOTA.read_text())
    except Exception:
        return set()  # broken/missing state must not silence routing
    simdi = simdi or time.time()
    return {r for r, bitis in d.items() if bitis > simdi}


def zincir(modeller: list, zorluk: str, kapali: set) -> list:
    esik = MIN_AA[zorluk]
    acik = [k for k in modeller if k.get("aa") is not None and k["rota"] not in kapali]
    uygun = [k for k in acik if k["aa"] >= esik]
    if not uygun:  # nothing reaches the bar: take the strongest open model instead of failing
        return sorted(acik, key=lambda k: -k["aa"])[:1]

    def anahtar(k):  # free route first, then cheaper, then less effort (quota), then smarter/newer
        fiyat = k["fiyat"][1] if k.get("fiyat") else 99
        return (ROTA_SIRA[k["rota"]], fiyat, efor_sira(k), -k["aa"])
    res, gorulen = [], set()
    for k in sorted(uygun, key=anahtar):  # lightest adequate model per route, free route first
        if k["rota"] not in gorulen:
            gorulen.add(k["rota"])
            res.append(k)
    return res


def zorluk_olc(gorev: str) -> str:
    try:
        import jev
        import jev_efor
        cevap = jev.decide({"text": gorev[:4000]}, jev_efor.SORU).get("answers")
        return jev_efor.sec(cevap, gorev, "medium")[0]
    except Exception:
        return "medium"  # JEV down: middle bar, routing still works


def main():
    a = sys.argv[1:]
    if a and a[0] == "--kota-bitti":
        d = {}
        try:
            d = json.loads(KOTA.read_text())
        except Exception:
            pass
        d[a[1]] = time.time() + float(a[2] if len(a) > 2 else 5) * 3600
        KOTA.write_text(json.dumps(d))
        print(f"{a[1]} kapali: {time.strftime('%H:%M', time.localtime(d[a[1]]))}'e kadar")
        return
    as_json = "--json" in a
    gorev = [x for x in a if x != "--json"][-1]
    zorluk = zorluk_olc(gorev)
    z = zincir(json.loads(KATALOG.read_text())["modeller"], zorluk, kota_kapali())
    with SECIM_LOG.open("a") as f:  # ajan_kapisi.py reads this: Agent is allowed only after a recent selection
        f.write(json.dumps({"ts": time.time(), "zorluk": zorluk, "ilk": z[0]["rota"] + ":" + z[0]["id"] if z else None}) + "\n")
    if as_json:
        print(json.dumps({"zorluk": zorluk, "zincir": [dict(k, komut=komut(k)) for k in z]}, ensure_ascii=False))
        return
    print(f"zorluk {zorluk} (min AA {MIN_AA[zorluk]})")
    for i, k in enumerate(z, 1):
        print(f"  {i}. {k['rota']:6} {k['ad']:32} AA {k['aa']:>5}  ->  {komut(k)}")


def demo():
    M = [{"rota": "agy", "id": "gemini-3.8-flash-high", "ad": "G38H", "efor": None, "aa": 40.9, "fiyat": [.75, 3.75]},
         {"rota": "agy", "id": "claude-opus-5-5-high", "ad": "agyOpusH", "efor": None, "aa": 53.6, "fiyat": None},
         {"rota": "codex", "id": "gpt-6-luna", "ad": "LunaMax", "efor": "max", "aa": 38.1, "fiyat": [.1, .5]},
         {"rota": "codex", "id": "gpt-6.1-sol", "ad": "SolH", "efor": "high", "aa": 50.2, "fiyat": [2, 10]},
         {"rota": "codex", "id": "gpt-6-astra", "ad": "AstraH", "efor": "high", "aa": 50.9, "fiyat": [10, 50]},
         {"rota": "claude", "id": "sonnet", "ad": "SonH", "efor": "high", "aa": 46.8, "fiyat": [2, 10]},
         {"rota": "claude", "id": "opus", "ad": "OpusX", "efor": "xhigh", "aa": 56.0, "fiyat": [4, 20]}]
    assert [k["ad"] for k in zincir(M, "medium", set())] == ["G38H", "LunaMax", "SonH"]
    assert [k["ad"] for k in zincir(M, "high", set())] == ["agyOpusH", "SolH", "SonH"]  # agy price unknown=99  # Sol over pricier Astra
    assert [k["ad"] for k in zincir(M, "xhigh", {"agy"})] == ["OpusX"]
    assert zincir(M, "max", {"agy", "claude"})[0]["ad"] == "AstraH"  # nobody >=55 open: strongest
    print("demo TAMAM")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else main()
