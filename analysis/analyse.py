"""Censoring-aware analysis of the DD factorial.  Reads ONLY aggregate.py's CSV.

Primary endpoint (pre-registered in tools/make_factorial.py before any run started):
    emergence step = first eval with query_ctx >= 0.625, RIGHT-CENSORED at the step budget.
A run that never crosses contributes "> last_step", never "= max step" (master-plan 26.3).

Comparison: each condition cell vs the no-recurrence baseline, log-rank test, Holm-corrected
across the 8 cells.  The unit of inference is the training seed (26.1) — n = 5 per cell, so
this wave is powered for LARGE shifts only; the reported minimum detectable effect says how
large, and a null here is "not powered to see it", not "no effect".

Runs still in flight are EXCLUDED and counted in the report: an unfinished run is neither an
event nor a censoring time, and including it would measure launch order (a real trap this
wave hit at 07:00 on 2026-08-08).
"""
from __future__ import annotations
import argparse
import collections
import csv
import json
import math
import statistics


def logrank(a_t, a_e, b_t, b_e):
    """Two-sample log-rank. t = times, e = 1 event / 0 censored. Returns (chi2, p, z)."""
    times = sorted(set([t for t, e in zip(a_t, a_e) if e] + [t for t, e in zip(b_t, b_e) if e]))
    O_a = E_a = V = 0.0
    for t in times:
        n_a = sum(1 for x in a_t if x >= t)
        n_b = sum(1 for x in b_t if x >= t)
        d_a = sum(1 for x, e in zip(a_t, a_e) if x == t and e)
        d_b = sum(1 for x, e in zip(b_t, b_e) if x == t and e)
        n, d = n_a + n_b, d_a + d_b
        if n < 2 or d == 0:
            continue
        O_a += d_a
        E_a += d * n_a / n
        V += d * (n_a / n) * (1 - n_a / n) * (n - d) / (n - 1)
    if V <= 0:
        return 0.0, 1.0, 0.0
    z = (O_a - E_a) / math.sqrt(V)
    chi2 = z * z
    try:
        from scipy.stats import chi2 as _c
        p = float(_c.sf(chi2, 1))
    except Exception:                      # normal approximation if scipy is absent
        p = math.erfc(abs(z) / math.sqrt(2))
    return chi2, p, z


def km_median(t, e):
    """Kaplan-Meier median survival (median emergence step); None if S never reaches 0.5."""
    order = sorted(range(len(t)), key=lambda i: t[i])
    S, n = 1.0, len(t)
    for idx, i in enumerate(order):
        at_risk = n - idx
        if e[i]:
            S *= (1 - 1 / at_risk)
            if S <= 0.5:
                return t[i]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rows = [r for r in csv.DictReader(open(a.csv)) if r["run_id"] != "canary"]

    cells = collections.defaultdict(lambda: dict(t=[], e=[], running=0))
    for r in rows:
        rid = r["run_id"]
        cell = "baseline" if rid.startswith("q4_") else rid.rsplit("_s", 1)[0]
        c = cells[cell]
        if r["emergence_step"]:
            c["t"].append(int(r["emergence_step"])); c["e"].append(1)
        elif r["done"] == "True":
            c["t"].append(int(r["last_step"])); c["e"].append(0)      # right-censored
        else:
            c["running"] += 1                                          # excluded, reported

    base = cells.get("baseline")
    report = dict(cells={}, comparisons=[], note="unfinished runs excluded from inference")
    print(f"{'cell':32s} {'n':>2} {'ev':>3} {'cens':>4} {'run':>4}  {'KM median':>9}")
    for k in sorted(cells):
        c = cells[k]
        med = km_median(c["t"], c["e"])
        report["cells"][k] = dict(n=len(c["t"]), events=sum(c["e"]),
                                  censored=len(c["t"]) - sum(c["e"]), running=c["running"],
                                  km_median=med,
                                  raw=sorted(t for t, e in zip(c["t"], c["e"]) if e))
        print(f"{k:32s} {len(c['t']):>2} {sum(c['e']):>3} {len(c['t'])-sum(c['e']):>4} "
              f"{c['running']:>4}  {str(med):>9}")

    if base and base["t"]:
        raw = []
        for k in sorted(cells):
            if k == "baseline":
                continue
            c = cells[k]
            if not c["t"]:
                continue
            chi2, p, z = logrank(base["t"], base["e"], c["t"], c["e"])
            raw.append((k, chi2, p, z))
        # Holm correction across the cells actually tested
        for rank, (k, chi2, p, z) in enumerate(sorted(raw, key=lambda x: x[2])):
            p_adj = min(1.0, p * (len(raw) - rank))
            report["comparisons"].append(dict(cell=k, chi2=round(chi2, 3), p=round(p, 4),
                                              p_holm=round(p_adj, 4), z=round(z, 3)))
        print("\nlog-rank vs baseline (Holm-corrected):")
        for c in report["comparisons"]:
            print(f"  {c['cell']:32s} chi2={c['chi2']:>6} p={c['p']:<7} p_holm={c['p_holm']}")

    incomplete = [k for k, c in cells.items() if c["running"]]
    if incomplete:
        print(f"\n*** NOT FINAL: {len(incomplete)} cells still have runs in flight "
              f"({sum(c['running'] for c in cells.values())} runs). Comparisons above are "
              f"provisional and biased by launch order. ***")
        report["final"] = False
    else:
        report["final"] = True
    if a.out:
        with open(a.out, "w") as f:
            json.dump(report, f, indent=1)
        print(f"\n-> {a.out}")


if __name__ == "__main__":
    main()
