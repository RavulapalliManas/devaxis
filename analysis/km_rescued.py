"""Corrected primary for the K=2 different-futures contrast: KM + log-rank on the RESCUED clock.

Tranche 1's arms had unequal follow-up (formed: 30k rescued steps; never-formed: ~59k) while
observed recoveries ran to 36k — a plain event-rate comparison is biased AGAINST the formed
arm.  Survival analysis on the rescued-steps clock uses every run's own censoring time, which
removes the bias without discarding data.  Event = first crossing of crit (chance + 0.5*(1 -
chance)) after rescue onset, measured in rescued steps; censoring = last eval's rescued time.

Log-rank: standard one-degree-of-freedom O-E form; p from the chi-square(1) tail
(erfc(sqrt(x/2))).  Groups: A = never-formed (k2tau10000_*), B = formed-collapsed
(k2postd10000_*), all parents with a terminal run in each arm.
"""
from __future__ import annotations
import glob
import json
import math
import os

W = os.path.expanduser("~/devaxis-work")


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def find(rid, dirs):
    for d in dirs:
        r = load(os.path.join(W, d, rid + ".json"))
        if r:
            return r
    return None


def surv_record(r, rescue_start):
    ch = r["chance_query_ctx"]
    crit = ch + 0.5 * (1 - ch)
    ev = [e for e in r.get("evals", []) if e["step"] >= rescue_start]
    if not ev:
        return None
    for e in ev:
        if e.get("query_ctx", 0) >= crit:
            return (e["step"] - rescue_start, 1)
    return (ev[-1]["step"] - rescue_start, 0)


def km_median(records):
    n = len(records)
    at_risk = n
    s = 1.0
    for t, d in sorted(records):
        if d:
            s *= (at_risk - 1) / at_risk
        at_risk -= 1
        if s <= 0.5:
            return t
    return None          # median not reached


def logrank(a, b):
    events = sorted({t for t, d in a + b if d})
    O = E = V = 0.0
    for t in events:
        na = sum(1 for x, _ in a if x >= t)
        nb = sum(1 for x, _ in b if x >= t)
        da = sum(1 for x, d in a if x == t and d)
        db = sum(1 for x, d in b if x == t and d)
        n, d = na + nb, da + db
        if n < 2:
            continue
        O += da
        E += d * na / n
        V += d * (na / n) * (nb / n) * (n - d) / (n - 1) if n > 1 else 0
    if V == 0:
        return None, None
    chi2 = (O - E) ** 2 / V
    p = math.erfc(math.sqrt(chi2 / 2))
    return chi2, p


def main():
    A, B = [], []
    for s in range(40):
        par = f"k2_s{s}"
        nv = find(f"k2tau10000_{par}", ["runs/kgen_tau", "runs/k2exp"])
        fm = find(f"k2postd10000_{par}", ["runs/k2post", "runs/k2exp"])
        if not (nv and fm and (nv.get("done") or nv.get("failed"))
                and (fm.get("done") or fm.get("failed"))):
            continue
        ra = surv_record(nv, 11000)
        rb = surv_record(fm, (fm.get("fork_step") or 0) + 10000)
        if ra and rb:
            A.append(ra)
            B.append(rb)
    ev_a, ev_b = sum(d for _, d in A), sum(d for _, d in B)
    print(f"never-formed: n={len(A)} events={ev_a} censor-times up to "
          f"{max(t for t, _ in A)} | KM median rescued-steps = {km_median(A)}")
    print(f"formed-collapsed: n={len(B)} events={ev_b} censor-times up to "
          f"{max(t for t, _ in B)} | KM median rescued-steps = {km_median(B)}")
    chi2, p = logrank(A, B)
    print(f"log-rank chi2 = {chi2:.3f}, two-sided p = {p:.4f}" if chi2 is not None
          else "log-rank undefined")


if __name__ == "__main__":
    main()
