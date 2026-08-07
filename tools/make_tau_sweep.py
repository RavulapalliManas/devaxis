"""Phase B — critical-period DOSE-RESPONSE: how long a deprivation before development changes?

PRE-REGISTERED before any run.

The branch matrix asks one question at one dose (tau = 10,000 deprived steps).  A single dose
cannot distinguish "deprivation postpones" from "deprivation forecloses" — only the SHAPE of
the response across doses can, and a monotone dose-response is much harder to explain by
chance than a single contrast.

Every baseline parent is forked at step 4000 (pre-emergence for all, post-read for all) and
deprived of use supply (p = 0) for tau steps, then rescued (p = 1) for the remainder:

    p(step) = 1.0 for step < 4000 ; 0.0 for 4000 <= step < 4000+tau ; 1.0 after

tau in {2000, 5000, 20000}; tau = 10000 is already running in the branch matrix, giving a
four-point curve.  tau = 0 is the parent itself, which Q2 certified is reproduced BITWISE by a
no-op fork — so the parent trajectory is the tau=0 arm and needs no extra compute.

Primary endpoint: emergence delay in USE-SUPPLIED steps, i.e. (emergence_step - (4000+tau)),
compared against the parent's own (emergence_step - 4000).  This age-matching is the whole
argument: at equal use-supplied time, a delay means the window degraded, not merely shifted.

Predictions, stated before the data:
  DELAY  (no critical period): use-supplied delay is FLAT in tau, P(emerge) unchanged.
  DAMAGE (critical period):    use-supplied delay RISES with tau and/or P(emerge) falls.
"""
from __future__ import annotations
import argparse
import json
import os

FORK_STEP = 4000
TAUS = [2000, 5000, 20000]
BUDGET = 70000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--factorial", default=os.path.expanduser("~/devaxis-work/factorial"))
    ap.add_argument("--runs", default="runs/factorial")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cores", default="0-31")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lo, hi = (int(x) for x in a.cores.split("-"))
    cores = list(range(lo, hi + 1))

    parents = []
    for s in range(8):
        rid = f"q4_s{s}"
        if (os.path.exists(os.path.join(a.runs, "ckpt", rid, f"step{FORK_STEP}.pt"))
                and os.path.exists(os.path.join(a.factorial, f"{rid}.manifest.json"))):
            parents.append(rid)

    queue, n = [], 0
    for rid in parents:
        pman = json.load(open(os.path.join(a.factorial, f"{rid}.manifest.json")))
        for tau in TAUS:
            child = dict(pman)
            child.pop("condition", None)
            child.update(run_id=f"tau{tau}_{rid}", parent_run_id=rid, fork_step=FORK_STEP,
                         resume_ckpt=os.path.abspath(os.path.join(a.runs, "ckpt", rid,
                                                                  f"step{FORK_STEP}.pt")),
                         p_schedule=f"0:1.0,{FORK_STEP}:0.0,{FORK_STEP + tau}:1.0",
                         steps=BUDGET, stop_at=0.90, ckpt_every=0, ckpt_at=[],
                         out_dir="runs/tau", data_streams=[dict(from_step=0, stream_id=rid)],
                         health_gate=dict(step=FORK_STEP + 2000, min_recap=0.5))
            p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
            with open(p, "w") as f:
                json.dump(child, f, indent=1)
            queue.append(dict(manifest=p, core=cores[n % len(cores)]))
            n += 1
    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[tau] {n} runs ({len(parents)} parents x {len(TAUS)} taus) -> {a.out}")


if __name__ == "__main__":
    main()
