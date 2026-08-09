"""Phase SB — Experiment 5.2: function-preserving symmetry breaking on foreclosed checkpoints.

PRE-REGISTERED before any run.  The theory under test (program doc §5.2, arXiv:2510.00304):
foreclosure is entry into an invariant cloned-unit manifold, where duplicate hidden units make
the antisymmetric direction (w_i - w_j) unlearnable.  If so, an intervention that BREAKS the
duplication without changing what the model currently computes should reopen learning.

    w_i <- w_i + delta * ||w_i|| * v
    w_j <- w_j - delta * ||w_j|| * v          (v a fixed unit vector, seeded per parent+layer)

Applied to the top-m most-similar hidden-unit pairs of each MLP (similarity = mean of the
input-row cosine and the output-column cosine, greedy disjoint pairing).

PRECONDITION, MEASURED FIRST, NOT ASSUMED: the builder prints the pair-similarity distribution
of every foreclosed checkpoint.  If near-duplicate units do not exist (top pair cosines not
elevated vs a plastic checkpoint), the cloned-manifold account is falsified before a single
perturbation is applied, and that null is the result.

ARMS (each with a pulse arm p=1 for 4,000 steps and a p=0 control on identical bytes;
chi = Δgold_mass(pulse − ctrl), exactly as in the transplant battery):
    noop     no perturbation                                   — pipeline control
    symb     antisymmetric on the top-m MOST similar pairs      — the intervention
    randp    independent random perturbations, SAME per-row norm, same rows
                                                                — controls for "any nudge works"
    symfar   antisymmetric on the LEAST similar pairs           — controls for the OPERATION
                                                                  absent symmetry to break

FUNCTION-PRESERVATION IS CHECKED, NOT CLAIMED: every run records its pre-pulse eval.  An arm
qualifies as function-preserving only if pre-pulse query and recap stay within the declared
margins of the unperturbed foreclosed state (|dq| <= 0.02, |drecap| <= 0.005 — the program
doc's equivalence margins).  Perturbations that move behavior are reported separately and
excluded from the plasticity claim; the first-order argument only holds for exact duplicates,
so this is an empirical gate.

DECLARED READING: symb > randp ~ symfar ~ noop, with all arms function-preserving, supports the
cloned-manifold mechanism.  symb ~ randp says any perturbation of that norm helps (a jostling
effect, not symmetry).  All arms ~ 0 says the manifold account does not explain OUR foreclosure.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import sys

import torch

F_STEP, DELTA_PULSE = 24000, 4000
PARENTS = [f"q4_s{s}" for s in range(8)]
NL, PAIRS_PER_LAYER, DELTA = 6, 8, 0.10


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pair_scores(sd, layer: int):
    """(score, i, j) for every hidden-unit pair of one MLP, high score = near-duplicate."""
    win = sd[f"blocks.{layer}.mlp.0.weight"].float()           # (4d, d)
    wout = sd[f"blocks.{layer}.mlp.2.weight"].float().t()      # (4d, d) after transpose
    a = torch.nn.functional.normalize(win, dim=1)
    b = torch.nn.functional.normalize(wout, dim=1)
    s = 0.5 * (a @ a.t() + b @ b.t())
    s.fill_diagonal_(-9.0)
    return s


def greedy_pairs(s, m: int, most_similar: bool):
    used, out = set(), []
    flat = s.flatten()
    order = torch.argsort(flat, descending=most_similar)
    n = s.shape[0]
    for idx in order.tolist():
        i, j = divmod(idx, n)
        if i >= j or i in used or j in used:
            continue
        out.append((i, j, float(s[i, j])))
        used.add(i)
        used.add(j)
        if len(out) >= m:
            break
    return out


def perturb(sd, arm: str, seed: int, report: dict):
    if arm == "noop":
        return
    g = torch.Generator().manual_seed(seed)
    for layer in range(NL):
        s = pair_scores(sd, layer)
        pairs = greedy_pairs(s, PAIRS_PER_LAYER, most_similar=(arm != "symfar"))
        report.setdefault("pair_cos", []).extend(round(p[2], 4) for p in pairs)
        win = sd[f"blocks.{layer}.mlp.0.weight"]
        d = win.shape[1]
        for i, j, _ in pairs:
            v = torch.randn(d, generator=g, dtype=torch.float32)
            v = v / v.norm()
            ni = win[i].float().norm().item()
            nj = win[j].float().norm().item()
            if arm in ("symb", "symfar"):
                win[i] = (win[i].float() + DELTA * ni * v).to(win.dtype)
                win[j] = (win[j].float() - DELTA * nj * v).to(win.dtype)
            elif arm == "randp":                     # same norms, independent directions
                v2 = torch.randn(d, generator=g, dtype=torch.float32)
                v2 = v2 / v2.norm()
                win[i] = (win[i].float() + DELTA * ni * v).to(win.dtype)
                win[j] = (win[j].float() + DELTA * nj * v2).to(win.dtype)


def make(src: str, arm: str, seed: int, out_path: str) -> dict:
    ck = torch.load(src, map_location="cpu", weights_only=False)
    report: dict = {}
    perturb(ck["model"], arm, seed, report)
    ck["opt"] = {"state": {}, "param_groups": ck["opt"]["param_groups"]}   # as in transplant
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    torch.save(ck, out_path)
    side = dict(path=os.path.basename(out_path), step=ck["step"], sha256=sha256_file(out_path),
                nparam=ck["nparam"], lr=ck["lr"], manifest_hash=ck["manifest_hash"], arm=arm,
                delta=DELTA, pairs_per_layer=PAIRS_PER_LAYER,
                pair_cos_summary=(sorted(report.get("pair_cos", []))[:3],
                                  sorted(report.get("pair_cos", []))[-3:]) if report.get("pair_cos") else None)
    with open(out_path + ".manifest.json", "w") as f:
        json.dump(side, f, indent=1)
    return side


def busy_cores():
    out = set()
    for p in subprocess.run(["pgrep", "-f", "training[.]train"],
                            capture_output=True, text=True).stdout.split():
        try:
            for x in open(f"/proc/{p}/environ", "rb").read().decode(errors="ignore").split("\0"):
                if x.startswith("NEURON_RT_VISIBLE_CORES="):
                    out.add(int(x.split("=", 1)[1]))
        except Exception:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--factorial", default=os.path.expanduser("~/devaxis-work/factorial"))
    ap.add_argument("--runs", default="runs/factorial")
    ap.add_argument("--traj-runs", default="runs/tomo_traj")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cores", default="0-31")
    ap.add_argument("--src-step", type=int, default=F_STEP,
                    help="deprived-trajectory step to operate on: 24000 = the LATE "
                         "duplicated state; 12000 = dep_age 8000, where chi is already "
                         "dead but dup_frac is still 0.0000 (unit_collapse.py) — the "
                         "state that actually matters for foreclosure")
    ap.add_argument("--report-only", action="store_true",
                    help="print the duplicate-unit precondition and exit without building")
    a = ap.parse_args()

    if a.report_only:
        print("pair-similarity precondition (top-3 cosines per checkpoint):")
        for rid in PARENTS:
            for tag, path in (("plastic", os.path.join(a.runs, "ckpt", rid, f"step4000.pt")),
                              ("forecl.", os.path.join(a.traj_runs, "ckpt", f"tomotraj_{rid}",
                                                       f"step{F_STEP}.pt"))):
                if not os.path.exists(path):
                    continue
                sd = torch.load(path, map_location="cpu", weights_only=False)["model"]
                tops = []
                for layer in range(NL):
                    tops += [p[2] for p in greedy_pairs(pair_scores(sd, layer), 3, True)]
                tops.sort(reverse=True)
                print(f"  {rid} {tag}: {[round(x,4) for x in tops[:3]]}")
        return

    os.makedirs(a.out, exist_ok=True)
    lo, hi = (int(x) for x in a.cores.split("-"))
    cores = [c for c in range(lo, hi + 1) if c not in busy_cores()] or list(range(lo, hi + 1))
    queue, n = [], 0
    for si, rid in enumerate(PARENTS):
        src = os.path.join(a.traj_runs, "ckpt", f"tomotraj_{rid}", f"step{a.src_step}.pt")
        mp = os.path.join(a.factorial, f"{rid}.manifest.json")
        if not (os.path.exists(src) and os.path.exists(mp)):
            print(f"[skip] {rid}")
            continue
        pman = json.load(open(mp))
        for arm in ("noop", "symb", "randp", "symfar"):
            ck = os.path.join(a.out, "ckpts", f"{arm}_{a.src_step}_{rid}.pt")
            side = make(src, arm, seed=1000 + si, out_path=ck)
            print(f"[sb] {arm}_{rid}: pair_cos {side['pair_cos_summary']}")
            for pa, pv in (("pulse", "1.0"), ("ctrl", "0.0")):
                child = dict(pman)
                child.pop("condition", None)
                child.pop("health_gate", None)
                child.update(run_id=f"sb{a.src_step}_{arm}_{pa}_{rid}", parent_run_id=rid,
                             fork_step=a.src_step, resume_ckpt=os.path.abspath(ck),
                             p_schedule=f"0:{pv}", steps=a.src_step + DELTA_PULSE, stop_at=2.0,
                             ckpt_every=0, ckpt_at=[], out_dir="runs/symbreak",
                             data_streams=[dict(from_step=0, stream_id=rid)])
                p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
                with open(p, "w") as f:
                    json.dump(child, f, indent=1)
                queue.append(dict(manifest=p, core=cores[n % len(cores)]))
                n += 1
    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[symbreak] {n} runs -> {a.out}")


if __name__ == "__main__":
    main()
