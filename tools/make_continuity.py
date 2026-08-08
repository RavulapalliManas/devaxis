"""Phase C-shape — matched-dose continuity: does WHEN supervision arrives matter at fixed HOW MUCH?

PRE-REGISTERED before any run of this phase.  This is the decisive form of the question phase Z
only brackets.  Two facts motivate it: full supply restored after a hard gap never recovers the
circuit (0 of ~21 runs), while CONTINUOUS 3% supply recovered two circuits from chance
(thr003_q4_s5/s6).  Phase Z varies the dose; this phase HOLDS THE DOSE FIXED and varies only its
temporal shape, which is the only design that can separate continuity from quantity.

DESIGN.  Fork every K=4 parent at step 4,000 (pre-emergence, as in the tau sweep).  In the
window [4,000, 14,000) every arm receives the SAME expected supervision dose, D = 300
p-step-equivalents (= 3% duty over 10k steps), arranged four ways:

    cont003  p = 0.03 throughout the window            max gap     0
    micro    10 bursts of 30 steps at p = 1, 1/1000    max gap   970
    bstart   one 300-step p = 1 burst at window start  max gap 9,700
    bend     one 300-step p = 1 burst at window end    max gap 9,700

then p = 1.0 from step 14,000, budget 70,000, stop_at 0.90 — identical to the tau sweep, whose
tau = 10,000 arm (0/7 emerged) is the D = 0 reference.  Identical bytes in all arms (data is a
pure function of (stream, step)); only the loss-mask schedule differs.  Dose matching is exact
in expectation and ±0.5% realized (Bernoulli at bs = 128: sd/mean = sqrt(npq)/np ~ 0.005).

PREDICTIONS, stated before the data:
  CONTINUITY (max gap governs):  cont003 and micro emerge at high rate (gap 0 / 970, both below
    the tau = 2,000 half-lethal dose); bstart and bend fall to ~0/8 like tau = 10,000 (gap 9,700
    ~ 10,000).  Sharpest signature: micro >> bstart at identical dose.
  DOSE (integrated supply governs):  all four arms equal within noise — 300 p-steps is 300
    p-steps however arranged.  This outcome kills the continuity pillar and with it the
    "non-zero lifeline" recommendation; the account reduces to dose bookkeeping.
  RECENCY (supervision near the rescue matters):  bend >> bstart, other arms intermediate.

Primary endpoint: P(emerge by budget) per arm, paired by parent (8 parents x 4 arms = 32 runs).
Secondary: emergence step on the use-supplied clock.  Dense checkpoints are saved through the
window and early rescue so the formation-under-shape trajectories support transplantation and
rewinding later; the tau arms saved none, which is why the mechanistic work cannot be done on
them retroactively.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess

FORK = 4000
WIN_END = 14000
DOSE = 300
BUDGET = 70000
CKPTS = [6000, 8000, 10000, 12000, 14000, 16000, 20000]


def busy_cores():
    """Cores held by a live trainer; assigning onto one kills the job at init with no record."""
    out = set()
    for p in subprocess.run(["pgrep", "-f", "training[.]train"],
                            capture_output=True, text=True).stdout.split():
        try:
            env = open(f"/proc/{p}/environ", "rb").read().decode(errors="ignore").split("\0")
            for x in env:
                if x.startswith("NEURON_RT_VISIBLE_CORES="):
                    out.add(int(x.split("=", 1)[1]))
        except Exception:
            pass
    return out


def schedules():
    micro = ["0:1.0"]
    for j in range(10):
        w = FORK + 1000 * j
        micro += [f"{w}:1.0", f"{w + 30}:0.0"]
    micro.append(f"{WIN_END}:1.0")
    return {
        "cont003": f"0:1.0,{FORK}:0.03,{WIN_END}:1.0",
        "micro": ",".join(micro),
        "bstart": f"0:1.0,{FORK + DOSE}:0.0,{WIN_END}:1.0",
        "bend": f"0:1.0,{FORK}:0.0,{WIN_END - DOSE}:1.0",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--factorial", default=os.path.expanduser("~/devaxis-work/factorial"))
    ap.add_argument("--runs", default="runs/factorial")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cores", default="0-31")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lo, hi = (int(x) for x in a.cores.split("-"))
    held = busy_cores()
    cores = [c for c in range(lo, hi + 1) if c not in held]
    if held:
        print(f"[cores] avoiding busy cores {sorted(held)}; using {len(cores)}")
    assert cores, "no free cores"

    queue, n = [], 0
    for s in range(8):
        rid = f"q4_s{s}"
        mp = os.path.join(a.factorial, f"{rid}.manifest.json")
        ck = os.path.join(a.runs, "ckpt", rid, f"step{FORK}.pt")
        if not (os.path.exists(mp) and os.path.exists(ck)):
            print(f"[skip] {rid}: manifest={os.path.exists(mp)} ckpt={os.path.exists(ck)}")
            continue
        pman = json.load(open(mp))
        for arm, sched in schedules().items():
            child = dict(pman)
            child.pop("condition", None)
            child.update(run_id=f"{arm}_{rid}", parent_run_id=rid, fork_step=FORK,
                         resume_ckpt=os.path.abspath(ck), p_schedule=sched,
                         steps=BUDGET, stop_at=0.90, ckpt_every=0, ckpt_at=CKPTS,
                         out_dir="runs/continuity",
                         data_streams=[dict(from_step=0, stream_id=rid)],
                         health_gate=dict(step=FORK + 2000, min_recap=0.5))
            p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
            with open(p, "w") as f:
                json.dump(child, f, indent=1)
            queue.append(dict(manifest=p, core=cores[n % len(cores)]))
            n += 1
    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[continuity] {n} runs (4 matched-dose shapes x parents) -> {a.out}")


if __name__ == "__main__":
    main()
