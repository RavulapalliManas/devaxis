"""chi(a) along NORMAL development: paired pulse-minus-control on the baseline parents.

The pulse phase forked each K=4 parent at every saved age into a 1,000-step p=1 arm and a
p=0 control arm on identical bytes.  chi_normal(a) = Δgold_mass (p-arm minus c-arm) at the
matched step.  Expectation under the account: small at very young ages, largest just before
each parent's own emergence, ~0 after mastery (ceiling).  delta=1000 sits near the
instrument floor (the tomography showed +0.012 at a plastic state), so treat magnitudes as
lower bounds; the AGE PROFILE is the readout.
"""
from __future__ import annotations
import glob
import json
import os
from collections import defaultdict

W = os.path.expanduser("~/devaxis-work")


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def main():
    arms = defaultdict(dict)
    for p in glob.glob(os.path.join(W, "runs/pulse/*.json")):
        r = load(p)
        if not r or not (r.get("done") or r.get("failed")):
            continue
        rid = r["run_id"]                      # chi{age}{p|c}_q4_s{n}
        head = rid.split("_")[0]
        arm, age = head[-1], int(head[3:-1])
        par = "q4_" + rid.split("q4_")[1]
        lg = [e for e in r.get("evals", []) if "logit" in e and e["step"] > age]
        if lg:
            arms[(par, age)][arm] = lg[-1]["logit"].get("gold_mass")
    mat = defaultdict(list)
    for (par, age), d in arms.items():
        if d.get("p") is not None and d.get("c") is not None:
            mat[age].append(d["p"] - d["c"])
    print("chi_normal(a) = Δgold_mass, 1k p=1 pulse minus 1k p=0 control, per saved age:")
    for age in sorted(mat):
        v = mat[age]
        m = sum(v) / len(v)
        sd = (sum((x - m) ** 2 for x in v) / (len(v) - 1)) ** 0.5 if len(v) > 1 else 0.0
        print(f"  age={age:>6}: {m:+.4f}±{sd:.4f} (n={len(v)})")


if __name__ == "__main__":
    main()
