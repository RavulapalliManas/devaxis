"""Phase K4X — parent expansion for the foreclosure clock: the sign test escapes n=8.

PRE-REGISTERED before any run of this phase.

The paired plasticity decline (chi(age 0) > mean chi(age >= 8k), per parent) reads 7/8 at
BOTH probe widths, with different dissenting parents (s3 at delta=4000, s1 at delta=8000);
the registered two-sided exact sign test is pinned at p = 0.070 because 7/8 is the best
non-unanimous outcome n = 8 allows.  This phase adds 8 fresh K=4 parents (seeds 8-15) and
runs the identical trajectory + pulse protocol, giving n = 16 paired declines.

DECLARED DECISION RULE (before any tranche-2 data): PRIMARY = delta=8000 (the probe whose
age-0 positive control is far above floor, +0.513±0.301); SECONDARY = delta=4000.  Two-sided
exact sign test over all 16 parents, old and new pooled: >= 13/16 positive -> p = 0.021;
12/16 -> p = 0.077 (reported as-is, no switching between deltas after seeing results).
A parent whose chi(0) ~ 0 (slow emerger under-probed) counts AGAINST, as before.

STAGE base:  8 K=4 baselines, seeds 8-15, identical config to q4_s0-7.
STAGE traj:  gated on all 8 base runs terminal — deprived trajectories, fork@4000, p=0,
             24,000 steps, checkpoint every 1,000 (identical to tomotraj).
STAGE pulse: gated on trajectory checkpoints — delta in {4000, 8000} x ages {4000, 12000,
             20000} x 8 parents = 48 forks into runs/tomo_pulse (tomo_a{age}_d{delta}_q4_s{n}
             naming, so chi_matrix.py and the paired analysis pick them up unchanged).
Gates exit nonzero when unmet (program retries next cycle; no silent partial design).
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys

SEEDS = range(8, 16)
FORK, TRAJ_STEPS = 4000, 24000
AGES, DELTAS = [4000, 12000, 20000], [4000, 8000]

BASE = dict(model=dict(d=256, nl=6, nh=8), bs=128, lr=3e-3, wd=0.1, warmup=500,
            p_schedule="1.0", steps=120000, eval_every=250, logit_every=1000, stop_at=0.90,
            mask_value="finite", ckpt_every=4000, ckpt_at=[1000, 2000, 3000],
            health_gate=dict(step=2000, min_recap=0.5))


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
    ap.add_argument("--stage", choices=["base", "traj", "pulse"], required=True)
    ap.add_argument("--runs", default="runs/factorial")
    ap.add_argument("--traj-runs", default="runs/tomo_traj")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cores", default="0-31")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lo, hi = (int(x) for x in a.cores.split("-"))
    cores = [c for c in range(lo, hi + 1) if c not in busy_cores()] or list(range(lo, hi + 1))
    queue, n = [], 0

    if a.stage == "base":
        for s in SEEDS:
            man = dict(BASE, run_id=f"q4_s{s}", init_seed=s, task=dict(K=4, D=32),
                       out_dir="runs/factorial")
            p = os.path.join(a.out, f"q4_s{s}.manifest.json")
            with open(p, "w") as f:
                json.dump(man, f, indent=1)
            queue.append(dict(manifest=p, core=cores[n % len(cores)]))
            n += 1

    elif a.stage == "traj":
        missing = []
        for s in SEEDS:
            rid = f"q4_s{s}"
            rj = os.path.join(a.runs, f"{rid}.json")
            ck = os.path.join(a.runs, "ckpt", rid, f"step{FORK}.pt")
            r = json.load(open(rj)) if os.path.exists(rj) else None
            if not (r and (r.get("done") or r.get("failed")) and os.path.exists(ck)):
                missing.append(rid)
                continue
            man = dict(BASE, run_id=rid, init_seed=s, task=dict(K=4, D=32),
                       out_dir="runs/factorial")
            child = dict(man)
            child.update(run_id=f"tomotraj_{rid}", parent_run_id=rid, fork_step=FORK,
                         resume_ckpt=os.path.abspath(ck), p_schedule=f"0:1.0,{FORK}:0.0",
                         steps=TRAJ_STEPS, stop_at=2.0, ckpt_every=0,
                         ckpt_at=list(range(FORK + 1000, TRAJ_STEPS + 1, 1000)),
                         out_dir="runs/tomo_traj",
                         data_streams=[dict(from_step=0, stream_id=rid)],
                         health_gate=dict(step=FORK + 2000, min_recap=0.5))
            p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
            with open(p, "w") as f:
                json.dump(child, f, indent=1)
            queue.append(dict(manifest=p, core=cores[n % len(cores)]))
            n += 1
        if missing:
            print(f"[k4x:traj] NOT READY — {missing}")
            sys.exit(1)

    else:
        missing = []
        for s in SEEDS:
            rid = f"q4_s{s}"
            for age in AGES:
                ck = (os.path.abspath(os.path.join(a.runs, "ckpt", rid, f"step{age}.pt"))
                      if age == FORK else
                      os.path.abspath(os.path.join(a.traj_runs, "ckpt", f"tomotraj_{rid}",
                                                   f"step{age}.pt")))
                if not os.path.exists(ck):
                    missing.append(f"{rid}@{age}")
                    continue
                for d in DELTAS:
                    child = dict(BASE, run_id=f"tomo_a{age}_d{d}_{rid}", init_seed=s,
                                 task=dict(K=4, D=32), parent_run_id=rid, fork_step=age,
                                 resume_ckpt=ck, p_schedule="0:1.0", steps=age + d,
                                 stop_at=2.0, ckpt_every=0, ckpt_at=[],
                                 out_dir="runs/tomo_pulse",
                                 data_streams=[dict(from_step=0, stream_id=rid)])
                    child.pop("health_gate", None)
                    p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
                    with open(p, "w") as f:
                        json.dump(child, f, indent=1)
                    queue.append(dict(manifest=p, core=cores[n % len(cores)]))
                    n += 1
        if missing:
            print(f"[k4x:pulse] NOT READY — {missing}")
            sys.exit(1)

    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[k4x:{a.stage}] {n} runs -> {a.out}")


if __name__ == "__main__":
    main()
