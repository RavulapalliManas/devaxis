"""Unit-population collapse: is foreclosure entry into a cloned-unit manifold?

Measures, per MLP layer of a checkpoint:
  dup_frac  = fraction of hidden-unit pairs with combined input/output cosine > 0.9999
  erank     = effective rank of the input weight matrix, exp(entropy of the normalized
              singular-value spectrum) — a duplication-free measure of the same collapse

THE CONFOUND THIS SCRIPT EXISTS TO KILL: the first observation compared a plastic checkpoint at
step 4,000 with a deprived one at step 24,000, which differ in deprivation AND in 20,000 steps
of age.  Collapse could simply be what long training does.  So every deprived checkpoint is
reported beside SUPERVISED checkpoints of the same parent at matched steps (baselines keep
ckpt_every=4000 while they train under p=1).  Deprivation is implicated only if, at matched
step, the deprived checkpoint collapses and the supervised one does not.

The trajectory view is the second product: dup_frac against deprivation age, to compare with
the measured chi(t) decay (chi falls ~30-100x over the first ~8k steps).  A collapse on the
same timescale is a mechanism candidate; a collapse that finishes long after chi has already
died is not the cause of foreclosure.
"""
from __future__ import annotations
import argparse
import glob
import os
import re

import torch
import torch.nn.functional as F

NL = 6


def stats(path: str, layers=range(NL)) -> tuple[float, float]:
    sd = torch.load(path, map_location="cpu", weights_only=False)["model"]
    dups, eranks = [], []
    for L in layers:
        win = sd[f"blocks.{L}.mlp.0.weight"].float()
        wout = sd[f"blocks.{L}.mlp.2.weight"].float().t()
        a, b = F.normalize(win, dim=1), F.normalize(wout, dim=1)
        s = 0.5 * (a @ a.t() + b @ b.t())
        s.fill_diagonal_(-9.0)
        n = s.shape[0]
        dups.append(((s > 0.9999).sum().item() / 2) / (n * (n - 1) / 2))
        sv = torch.linalg.svdvals(win)
        p = sv / sv.sum()
        eranks.append(float(torch.exp(-(p * torch.log(p + 1e-12)).sum())))
    return sum(dups) / len(dups), sum(eranks) / len(eranks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=os.path.expanduser("~/devaxis-work"))
    ap.add_argument("--parents", default="q4_s0,q4_s1,q4_s2")
    a = ap.parse_args()
    W = a.work

    print("=== AGE-MATCHED CONTROL: supervised (p=1) vs deprived (p=0) at the SAME step ===")
    print(f"{'parent':>7} {'step':>7} {'supervised dup/erank':>26} {'deprived dup/erank':>24}")
    for rid in a.parents.split(","):
        sup = {int(re.search(r"step(\d+)", p).group(1)): p
               for p in glob.glob(os.path.join(W, "runs/factorial/ckpt", rid, "step*.pt"))}
        dep = {int(re.search(r"step(\d+)", p).group(1)): p
               for p in glob.glob(os.path.join(W, "runs/tomo_traj/ckpt", f"tomotraj_{rid}",
                                               "step*.pt"))}
        for step in sorted(set(sup) & set(dep)):
            ds, es = stats(sup[step])
            dd, ed = stats(dep[step])
            print(f"{rid:>7} {step:>7} {ds:>14.4f} / {es:>7.1f} {dd:>14.4f} / {ed:>7.1f}")
        only_dep = sorted(set(dep) - set(sup))
        if only_dep:
            print(f"{rid:>7}  (deprived-only steps, no supervised match: {only_dep[:3]}...)")

    print("\n=== TRAJECTORY: collapse vs deprivation age (compare with chi(t) decay) ===")
    rid = a.parents.split(",")[0]
    dep = {int(re.search(r"step(\d+)", p).group(1)): p
           for p in glob.glob(os.path.join(W, "runs/tomo_traj/ckpt", f"tomotraj_{rid}",
                                           "step*.pt"))}
    base = os.path.join(W, "runs/factorial/ckpt", rid, "step4000.pt")
    if os.path.exists(base):
        d0, e0 = stats(base)
        print(f"  dep_age      0: dup={d0:.4f} erank={e0:.1f}   (fork point, chi=+0.51)")
    for step in sorted(dep)[:24]:
        d, e = stats(dep[step])
        print(f"  dep_age {step-4000:>6}: dup={d:.4f} erank={e:.1f}")


if __name__ == "__main__":
    main()
