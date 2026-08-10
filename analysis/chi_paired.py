"""The registered paired test of the foreclosure clock, at the pre-declared n = 16.

DECLARED BEFORE THE EXPANSION DATA (tools/make_k4expand.py docstring): PRIMARY = delta 8000
(the probe whose age-0 positive control is far above the instrument floor); SECONDARY =
delta 4000. Two-sided exact sign test on the per-parent decline chi(dep_age 0) - mean
chi(dep_age >= 8000), pooling the 8 original and 8 expansion parents. >= 13/16 positive
-> p = 0.021; 12/16 -> p = 0.077, reported as-is with no switching between deltas.

chi is Delta gold_mass: the pulse fork minus its deprived-trajectory control at the matched
step, both on identical bytes.
"""
from __future__ import annotations
import glob
import json
import os
from collections import defaultdict
from math import comb

W = os.path.expanduser("~/devaxis-work")


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def sign_p(k, n):
    return min(1.0, 2 * sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n)


def main():
    tr_logit, tr_last = {}, {}
    for p in glob.glob(os.path.join(W, "runs/tomo_traj/tomotraj_*.json")):
        r = load(p)
        if not r:
            continue
        par = r["run_id"].replace("tomotraj_", "")
        for e in r.get("evals", []):
            if "logit" in e:
                tr_logit[(par, e["step"])] = e["logit"].get("gold_mass")
                tr_last[par] = (e["step"], e["logit"].get("gold_mass"))

    for delta, label in ((8000, "PRIMARY"), (4000, "secondary")):
        chi = defaultdict(dict)
        for p in glob.glob(os.path.join(W, f"runs/tomo_pulse/*_d{delta}_*.json")):
            r = load(p)
            if not r or not (r.get("done") or r.get("failed")):
                continue
            rid = r["run_id"]
            age = int(rid.split("_a")[1].split("_")[0])
            par = "q4_" + rid.split("q4_")[1]
            lg = [e for e in r.get("evals", []) if "logit" in e and e["step"] > age]
            if not lg:
                continue
            gp, step = lg[-1]["logit"].get("gold_mass"), lg[-1]["step"]
            gt = tr_logit.get((par, step))
            if gt is None and par in tr_last and step >= tr_last[par][0]:
                gt = tr_last[par][1]
            if gp is not None and gt is not None:
                chi[par][age - 4000] = gp - gt
        rows, pos = [], 0
        for par in sorted(chi, key=lambda x: int(x.split("_s")[1])):
            d = chi[par]
            late = [v for a, v in d.items() if a >= 8000]
            if 0 not in d or not late:
                continue
            diff = d[0] - sum(late) / len(late)
            pos += diff > 0
            rows.append((par, d[0], sum(late) / len(late), diff))
        n = len(rows)
        print(f"\n=== delta = {delta} ({label}) — n = {n} parents ===")
        for par, c0, cl, diff in rows:
            print(f"  {par:>8}: chi(0)={c0:+.4f}  mean chi(>=8k)={cl:+.4f}  "
                  f"decline={diff:+.4f} {'POS' if diff > 0 else 'neg'}")
        if n:
            print(f"  declines positive in {pos}/{n} — two-sided exact sign p = {sign_p(pos, n):.4f}"
                  + ("  [meets the declared >=13/16 bar]" if n == 16 and pos >= 13 else ""))


if __name__ == "__main__":
    main()
