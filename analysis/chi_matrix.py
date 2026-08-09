"""Chi(t, delta) matrix from the tomography pulses: does the deprived state still RESPOND?

chi is read on the LOGIT channel (gold_mass), not accuracy: baseline parents take 7k-31k
steps to emerge under full supervision, so an accuracy endpoint with delta <= 4k reads ~0 for
plastic and foreclosed states alike.  gold_mass moves first.  Control = the deprived
trajectory itself at the matched step (identical bytes; only the loss mask differs); for
pulses at the trajectory's final age the last trajectory logit is the control.

Instrument validation is internal: the age-4000 row IS the positive control — those pulses
fork the parent checkpoint at deprivation age zero, where plasticity is known present
(parents emerge 7-8/8 under p=1).  A matrix whose age-4000 cell is large and whose late-age
cells are ~0 is measuring plasticity decay; a flat-zero matrix would mean the instrument
failed its positive control and says nothing.

Known limits, stated: delta=250 pulses record no post-fork logit eval (logit_every=1000) and
are excluded; delta=1000 sits near the instrument floor even at age 4000 (+0.012) — the
informative probe is delta=4000.  Cells are seed means over n=8 with per-cell SD printed;
adjacent-age inversions within ~1 SD are noise, not structure.
"""
from __future__ import annotations
import argparse
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--traj", default=os.path.join(W, "runs/tomo_traj"))
    ap.add_argument("--pulse", default=os.path.join(W, "runs/tomo_pulse"))
    a = ap.parse_args()

    tr_logit, tr_last = {}, {}
    for p in glob.glob(os.path.join(a.traj, "tomotraj_*.json")):
        r = load(p)
        if not r:
            continue
        par = r["run_id"].replace("tomotraj_", "")
        for e in r.get("evals", []):
            if "logit" in e:
                tr_logit[(par, e["step"])] = e["logit"].get("gold_mass")
                tr_last[par] = (e["step"], e["logit"].get("gold_mass"))

    mat = defaultdict(list)
    skipped = 0
    for p in glob.glob(os.path.join(a.pulse, "*.json")):
        r = load(p)
        if not r or not (r.get("done") or r.get("failed")):
            continue
        rid = r["run_id"]
        age = int(rid.split("_a")[1].split("_")[0])
        d = int(rid.split("_d")[1].split("_")[0])
        par = "q4_" + rid.split("q4_")[1]
        lg = [e for e in r.get("evals", []) if "logit" in e and e["step"] > age]
        if not lg:
            skipped += 1
            continue
        gp, step = lg[-1]["logit"].get("gold_mass"), lg[-1]["step"]
        gt = tr_logit.get((par, step))
        if gt is None and par in tr_last and step >= tr_last[par][0]:
            gt = tr_last[par][1]
        if gp is None or gt is None:
            skipped += 1
            continue
        mat[(age, d)].append(gp - gt)

    ages = sorted({k[0] for k in mat})
    ds = sorted({k[1] for k in mat})
    print(f"chi(t, delta) = Δgold_mass (pulse − trajectory control); skipped={skipped} "
          f"(delta=250 has no post-fork logit)")
    print(f"{'dep_age':>8} | " + " | ".join(f"delta={d} mean±sd(n)".center(22) for d in ds))
    for age in ages:
        cells = []
        for d in ds:
            v = mat.get((age, d), [])
            if not v:
                cells.append("-".center(22))
                continue
            m = sum(v) / len(v)
            sd = (sum((x - m) ** 2 for x in v) / (len(v) - 1)) ** 0.5 if len(v) > 1 else 0.0
            cells.append(f"{m:+.4f}±{sd:.4f}({len(v)})".center(22))
        print(f"{age - 4000:>8} | " + " | ".join(cells))
    print("\n(dep_age = steps since deprivation began at 4000; row 0 = the positive control)")


if __name__ == "__main__":
    main()
