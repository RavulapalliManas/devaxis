"""Phase T — pre-emergence plasticity tomography: WHEN does the ability to learn die?

PRE-REGISTERED before any run of this phase.  Named hypothesis under test (Manas, 2026-08-09):

    CAPABILITY FORECLOSURE HYPOTHESIS.  During pretraining, the ability to acquire a capability
    can disappear before the capability is ever behaviorally expressed.

The K=4 dose-response already implies a foreclosure event somewhere in the deprivation window:
tau=2k -> 4/8 rescued, 5k -> 2/8, 10k -> 0/20, 20k -> 0/16.  But those arms measure only the
integrated outcome of a 56k-step rescue.  This phase localizes the transition in TIME and in
PULSE SIZE: chi(t, delta) = does a delta-step burst of full supervision at deprivation age t
still move the use circuit?

Two stages, one builder.

STAGE traj (run first): 8 deprived trajectories with dense checkpoints — fork each K=4 parent
at 4,000, p = 0 thereafter, NO rescue, 24,000 steps, checkpoint every 1,000.  These are the
states the tau arms threw away (they saved no checkpoints, which is why this cannot be done
retroactively).  The trajectory run doubles as the CONTROL for every pulse: chi(t, delta) =
U_pulse(t + delta) - U_traj(t + delta), no separate control forks needed, identical bytes.

STAGE pulse (run when traj checkpoints exist): fork at ages t in {4k, 6k, 8k, 10k, 12k, 16k,
20k, 24k} (4k = the parent checkpoint itself, deprivation age zero) x delta in {250, 1000,
4000} steps of p = 1.  8 parents x 8 ages x 3 deltas = 192 short forks.

MEASUREMENT NOTE, stated now: on the deprived trajectory U sits at chance BY DESIGN (there is
no supervision to express), so "plasticity dies before behavior" must be clocked against the
parent's counterfactual emergence distribution, not against the trajectory's own flat U.
The claim shape is: chi(t, delta) > 0 for t < t* and ~0 for t > t*, with t* + (delay already
measured in the tau arms) well before the ages at which these same parents emerge under p = 1.

Predictions, stated before the data:
  SHARP FORECLOSURE: chi collapses at some t* in [6k, 14k] for ALL deltas at once — a
    transition, matching the dose-response knee.
  DOSE-CONTINUOUS: chi(t, 4000) stays positive long after chi(t, 250) dies — "plasticity" is a
    curve over delta (outcome B of the state-space fork), and the tau arms' failure is about
    total dose, not a switch.
  NO DECAY: chi flat in t — foreclosure lives in the RESCUE dynamics, not the deprived state,
    and the hidden-state story needs a different instrument.
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import subprocess

FORK = 4000
TRAJ_STEPS = 24000
AGES = [4000, 6000, 8000, 10000, 12000, 16000, 20000, 24000]
DELTAS = [250, 1000, 4000]


def busy_cores():
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["traj", "pulse"], required=True)
    ap.add_argument("--factorial", default=os.path.expanduser("~/devaxis-work/factorial"))
    ap.add_argument("--runs", default="runs/factorial")
    ap.add_argument("--traj-runs", default="runs/tomo_traj")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cores", default="0-31")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lo, hi = (int(x) for x in a.cores.split("-"))
    held = busy_cores()
    cores = [c for c in range(lo, hi + 1) if c not in held]
    print(f"[cores] avoiding busy {sorted(held)}; using {len(cores)}")
    assert cores, "no free cores"

    queue, n = [], 0
    for s in range(8):
        rid = f"q4_s{s}"
        mp = os.path.join(a.factorial, f"{rid}.manifest.json")
        pk = os.path.join(a.runs, "ckpt", rid, f"step{FORK}.pt")
        if not (os.path.exists(mp) and os.path.exists(pk)):
            print(f"[skip] {rid}")
            continue
        pman = json.load(open(mp))

        if a.stage == "traj":
            child = dict(pman)
            child.pop("condition", None)
            child.update(run_id=f"tomotraj_{rid}", parent_run_id=rid, fork_step=FORK,
                         resume_ckpt=os.path.abspath(pk),
                         p_schedule=f"0:1.0,{FORK}:0.0",
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
        else:
            for age in AGES:
                ck = (os.path.abspath(pk) if age == FORK else
                      os.path.abspath(os.path.join(a.traj_runs, "ckpt", f"tomotraj_{rid}",
                                                   f"step{age}.pt")))
                if not os.path.exists(ck):
                    print(f"[skip] {rid} age {age}: no ckpt")
                    continue
                for d in DELTAS:
                    child = dict(pman)
                    child.pop("condition", None)
                    child.pop("health_gate", None)
                    child.update(run_id=f"tomo_a{age}_d{d}_{rid}", parent_run_id=rid,
                                 fork_step=age, resume_ckpt=ck,
                                 p_schedule="0:1.0", steps=age + d, stop_at=2.0,
                                 ckpt_every=0, ckpt_at=[], out_dir="runs/tomo_pulse",
                                 data_streams=[dict(from_step=0, stream_id=rid)])
                    p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
                    with open(p, "w") as f:
                        json.dump(child, f, indent=1)
                    queue.append(dict(manifest=p, core=cores[n % len(cores)]))
                    n += 1
    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[tomo:{a.stage}] {n} runs -> {a.out}")


if __name__ == "__main__":
    main()
