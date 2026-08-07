"""Branch matrix: deprivation and rescue from a fixed developmental state.

PRE-REGISTERED HERE, before any branch run starts.

Design.  Every baseline run is forked at step 4000 — a state that is PRE-EMERGENCE for all of
them (the earliest baseline emergence measured in this wave is 7000) but POST-READ (recap
saturates by ~500).  So each fork starts from a model that maintains its bindings and cannot
yet use them.  Three arms, identical in every respect except the use-supply schedule p:

  noop      p = 1.0 throughout           control; must reproduce the parent (Q2 certified T0
                                         bitwise, so any divergence here is a real defect)
  deprive   p -> 0 at 4000, permanent    positive control: with no use supply the use circuit
                                         should not form (lag_law p=0 result)
  rescue10k p -> 0 at 4000, -> 1 at 14000  the question: after a 10k-step deprivation window,
                                         does the use circuit still form, and how much later?

Primary endpoint: emergence step (query_ctx >= 0.625), right-censored at the budget.
Secondary: emergence delay measured in USE-SUPPLIED steps since rescue — the age-matched
comparison that separates "a window closed" from "a clock started late" (critical_period.py's
central argument).  A raw comparison at equal wall-clock step confounds the two and is not the
endpoint.

Falsifier: if rescue10k emerges at the same use-supplied delay as noop, deprivation only
postpones — no critical period on this task at this state.
"""
from __future__ import annotations
import argparse
import json
import os

FORK_STEP = 4000
DEPRIVE_UNTIL = 14000
BUDGET = 60000

ARMS = {
    "noop":      "1.0",
    "deprive":   f"0:1.0,{FORK_STEP}:0.0",
    "rescue10k": f"0:1.0,{FORK_STEP}:0.0,{DEPRIVE_UNTIL}:1.0",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--factorial", default=os.path.expanduser("~/devaxis-work/factorial"))
    ap.add_argument("--runs", default="runs/factorial")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cores", default="9-31", help="inclusive core range for these lanes")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lo, hi = (int(x) for x in a.cores.split("-"))
    cores = list(range(lo, hi + 1))

    parents = []
    for s in range(8):
        rid = f"q4_s{s}"
        ck = os.path.join(a.runs, "ckpt", rid, f"step{FORK_STEP}.pt")
        rec = os.path.join(a.runs, f"{rid}.json")
        if os.path.exists(ck) and os.path.exists(rec):
            r = json.load(open(rec))
            if r.get("done"):
                parents.append(rid)
    print(f"[branch] eligible parents (done + ckpt@{FORK_STEP}): {parents}")

    queue, n = [], 0
    for rid in parents:
        pman = json.load(open(os.path.join(a.factorial, f"{rid}.manifest.json")))
        for arm, sched in ARMS.items():
            child = dict(pman)
            child.pop("condition", None)
            child.update(run_id=f"br_{arm}_{rid}", parent_run_id=rid, fork_step=FORK_STEP,
                         resume_ckpt=os.path.abspath(os.path.join(a.runs, "ckpt", rid,
                                                                  f"step{FORK_STEP}.pt")),
                         p_schedule=sched, steps=BUDGET, stop_at=0.90,
                         ckpt_every=8000, ckpt_at=[], out_dir="runs/branch",
                         data_streams=[dict(from_step=0, stream_id=rid)],
                         health_gate=dict(step=6000, min_recap=0.5))
            p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
            with open(p, "w") as f:
                json.dump(child, f, indent=1)
            queue.append(dict(manifest=p, core=cores[n % len(cores)]))
            n += 1
    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[branch] {n} runs ({len(parents)} parents x {len(ARMS)} arms) over "
          f"{len(cores)} cores -> {a.out}")


if __name__ == "__main__":
    main()
