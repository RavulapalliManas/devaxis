"""Savings analysis: does a collapsed circuit re-form FASTER than de novo?  (X5 cross-check.)

The h100 session measured induction heads driven to behavioral zero re-forming with 92.9%
savings (12/12 faster, p=0.0005) — behavior erased, structure retained — and flagged that a
"recovered-or-not" reading depends on the follow-up window.  This computes the same paired
quantity on the K=2 binding data: for each parent, the formed-then-collapsed arm's
re-formation time (rescued steps to criterion) against the SAME parent's original de-novo
formation time (steps to criterion from scratch).

savings = 1 - reform_time / denovo_time.  Positive = the induction result's direction
(structure retained); negative = re-formation is HARDER than de novo (damage).  Runs that
never re-form within follow-up are lower bounds (savings upper-bounded using the censor time)
and counted separately.  Follow-up context: the formed arms had 30k (tranche 1) or 60k
(tranche 2) rescued steps vs a de-novo median ~3.1k — the window is 10-19x the de-novo
median, so "not watched long enough" is bounded, not assumed.
"""
from __future__ import annotations
import glob
import json
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


def t_crit(r, after=0):
    ch = r["chance_query_ctx"]
    crit = ch + 0.5 * (1 - ch)
    for e in r.get("evals", []):
        if e["step"] >= after and e.get("query_ctx", 0) >= crit:
            return e["step"]
    return None


def main():
    rows, censored = [], []
    for s in range(40):
        par = f"k2_s{s}"
        base = find(par, ["runs/kgen"])
        fm = find(f"k2postd10000_{par}", ["runs/k2post", "runs/k2exp"])
        if not (base and fm and (fm.get("done") or fm.get("failed"))):
            continue
        denovo = t_crit(base)
        if denovo is None:
            continue
        rescue_start = (fm.get("fork_step") or 0) + 10000
        reform_abs = t_crit(fm, after=rescue_start)
        if reform_abs is None:
            follow = fm["evals"][-1]["step"] - rescue_start
            censored.append((par, denovo, follow, 1 - follow / denovo))
            continue
        reform = reform_abs - rescue_start
        rows.append((par, denovo, reform, 1 - reform / denovo))
    print(f"{'parent':>8} {'denovo':>7} {'reform':>7} {'savings':>8}")
    for par, d, rf, sv in sorted(rows):
        print(f"{par:>8} {d:>7} {rf:>7} {sv:>+8.2f}")
    pos = sum(1 for *_, sv in rows if sv > 0)
    print(f"\nre-formed: {len(rows)} runs; POSITIVE savings (faster than de novo): {pos}/{len(rows)}")
    if rows:
        svs = sorted(sv for *_, sv in rows)
        print(f"median savings among re-formed: {svs[len(svs)//2]:+.2f}")
    print(f"never re-formed within follow-up: {len(censored)} runs "
          f"(follow-up {min(c[2] for c in censored) if censored else 0}-"
          f"{max(c[2] for c in censored) if censored else 0} rescued steps; savings "
          f"upper bounds all strongly negative)")
    print("\nContrast (induction, h100 X5): 92.9% savings, 12/12 faster. Same sign here would")
    print("support 'structure retained'; opposite sign supports genuine damage in binding-use.")


if __name__ == "__main__":
    main()
