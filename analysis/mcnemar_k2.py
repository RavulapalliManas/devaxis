"""Confirmatory paired analysis of the gap-matched K=2 different-futures contrast.

PRE-REGISTERED (make_k2expand.py docstring, before any expansion run): per-parent PAIRED
outcome — never-formed (fork@1000, p=0 for 10k, rescue to 70k budget) vs formed-collapsed
(fork at terminal ckpt, p=0 for 10k, rescue 30k) — exact two-sided McNemar over 24 pairs:
8 original parents (arms in runs/kgen_tau + runs/k2post) + 16 expansion parents (both arms
in runs/k2exp).  Secondary: pooled Fisher.  A pair where the never-formed arm fails counts
against the dissociation.
"""
from __future__ import annotations
import glob
import json
import os
from math import comb

W = os.path.expanduser("~/devaxis-work")


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def recovered(r, after):
    ch = r["chance_query_ctx"]
    crit = ch + 0.5 * (1 - ch)
    return any(e["step"] >= after and e.get("query_ctx", 0) >= crit for e in r.get("evals", []))


def find(rid, dirs):
    for d in dirs:
        r = load(os.path.join(W, d, rid + ".json"))
        if r:
            return r
    return None


def main():
    pairs = []
    for s in range(24):
        par = f"k2_s{s}"
        nv = find(f"k2tau10000_{par}", ["runs/kgen_tau", "runs/k2exp"])
        fm = find(f"k2postd10000_{par}", ["runs/k2post", "runs/k2exp"])
        if not (nv and fm):
            print(f"  MISSING pair for {par}: never={bool(nv)} formed={bool(fm)}")
            continue
        if not ((nv.get("done") or nv.get("failed")) and (fm.get("done") or fm.get("failed"))):
            print(f"  NON-TERMINAL pair for {par} — excluded this pass")
            continue
        a = recovered(nv, after=11000)
        b = recovered(fm, after=(fm.get("fork_step") or 0) + 10000)
        pairs.append((par, a, b))
        print(f"  {par}: never={'REC' if a else 'frozen'}  formed={'REC' if b else 'frozen'}")
    n = len(pairs)
    nv_rec = sum(a for _, a, _ in pairs)
    fm_rec = sum(b for _, _, b in pairs)
    b01 = sum(1 for _, a, b in pairs if a and not b)   # never recovers, formed frozen
    b10 = sum(1 for _, a, b in pairs if b and not a)
    m = b01 + b10
    p_mc = min(1.0, 2 * sum(comb(m, k) for k in range(b01, m + 1)) / 2 ** m) if m else 1.0
    print(f"\nn_pairs={n}  never-formed recovered {nv_rec}/{n}  formed-collapsed {fm_rec}/{n}")
    print(f"discordant: never-only={b01}, formed-only={b10}  "
          f"exact McNemar two-sided p = {p_mc:.5f}")


if __name__ == "__main__":
    main()
