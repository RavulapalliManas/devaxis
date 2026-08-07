"""Phase C — DD10: is the value of the SAME data conditional on developmental state?

PRE-REGISTERED before any run.  This is the flagship-level experiment of the data program
(master plan section 19, DD10): the same examples, the same objective, the same optimizer
settings, the same token budget — applied from two different developmental states.

    state A = step 4000   pre-emergence, post-read: bindings maintained, not yet usable
    state B = step 12000  post-emergence for most parents: the use circuit exists

Intervention (identical in both): switch the data stream to the exact-recurrence condition
(rate 0.25, pool 64, interval 50) for the remainder of training.

    R(D*, z_A) != R(D*, z_B)  would establish that example utility is state-dependent.

Controls come free: Q2 certified that a no-op fork reproduces its parent BITWISE, so the
parent's own trajectory IS the control arm at each state — no extra compute, and no risk of a
control that silently differs.

Endpoint: change in the emergence/consolidation trajectory relative to the parent's own
trajectory over the same step interval — specifically query_ctx at matched steps after the
fork, and (where it occurs) emergence step.  Both states get the same budget so the comparison
is at matched compute, not matched wall-clock.
"""
from __future__ import annotations
import argparse
import json
import os

STATES = [4000, 12000]
BUDGET_AFTER = 30000
COND = dict(recurrence="exact", rate=0.25, pool_size=64, interval=50, order="fixed")




def busy_cores():
    """Cores already held by a live trainer.  Assigning a job to a busy NeuronCore makes it
    fail at runtime init — that is how 6 of 21 branch-matrix runs were silently lost on
    2026-08-08 when a wave was launched while the previous one still held lanes."""
    import subprocess
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

    queue, n, skipped = [], 0, []
    for s in range(8):
        rid = f"q4_s{s}"
        mp = os.path.join(a.factorial, f"{rid}.manifest.json")
        if not os.path.exists(mp):
            continue
        pman = json.load(open(mp))
        for st in STATES:
            ck = os.path.join(a.runs, "ckpt", rid, f"step{st}.pt")
            if not os.path.exists(ck):
                skipped.append(f"{rid}@{st}")
                continue
            child = dict(pman)
            child.update(run_id=f"dd10_s{st}_{rid}", parent_run_id=rid, fork_step=st,
                         resume_ckpt=os.path.abspath(ck), condition=COND,
                         steps=st + BUDGET_AFTER, stop_at=0.0, ckpt_every=0, ckpt_at=[],
                         out_dir="runs/dd10",
                         data_streams=[dict(from_step=0, stream_id=rid),
                                       dict(from_step=st, stream_id=f"dd10_{rid}_{st}")],
                         health_gate=dict(step=st + 2000, min_recap=0.5))
            p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
            with open(p, "w") as f:
                json.dump(child, f, indent=1)
            queue.append(dict(manifest=p, core=cores[n % len(cores)]))
            n += 1
    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[dd10] {n} runs -> {a.out}"
          + (f" | skipped (no ckpt): {skipped}" if skipped else ""))


if __name__ == "__main__":
    main()
