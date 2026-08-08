"""Phase K2-post — collapse and attempted recovery of a FORMED circuit at K = 2.

PRE-REGISTERED before any run of this phase.

At K = 4 the two halves of the lifecycle are both irreversible: formation is foreclosed by a
10k-step gap (0/20 recomputed 2026-08-08) and a formed circuit collapses under p = 0 within
750-1,750 steps and never recovers when full supply returns (postresc 0/7).  Tonight's K = 2
data broke the symmetry ON THE FORMATION SIDE: after a 2k gap, 8/8 K = 2 models still form the
circuit.  This phase asks whether the RECOVERY side breaks too.

DESIGN.  Fork every K = 2 parent at its terminal checkpoint (query_ctx 0.95-1.00), cut supply
entirely for 3,000 steps (comfortably past the K = 4 collapse latency), then restore p = 1.0
for 30,000 steps.  One run measures both the collapse latency and the recovery outcome.  Dense
checkpoints are saved through collapse and early rescue so the collapsed state itself is
preserved for transplantation and rewinding — the K = 4 collapse was never checkpointed.

WHY THIS MATTERS more than another cell: together with the K = 2 tau = 10,000 arm now running,
it composes the same-behavior-different-futures contrast at K = 2 —

    A: deprived, never formed, at chance, then given p = 1   (kgen_tau, running)
    B: formed, collapsed, at chance, then given p = 1        (this phase)

If A emerges and B does not, two at-chance models under identical future supervision have
opposite futures — the hidden-state result — at matched load, on identical byte streams.
Caveat, stated now: A and B are age- and cumulative-supervision-UNMATCHED in this first pass
(A got ~1k supervised steps, B got ~its full formation).  If the dissociation appears, the
exactly-matched construction (same age, same total supervised count, arranged differently)
is the confirmatory experiment, not this one.

Predictions, stated before the data:
  K=4 ACCOUNT TRANSPLANTS:  collapse in ~1k steps, recovery 0/8 — irreversibility is a
    property of collapse itself, and K = 2's formation-side plasticity does not help.
  LOAD GOVERNS EVERYTHING:  collapse then RECOVERY at high rate — K = 4's irreversibility is a
    capacity-pressure phenomenon, not a general law of interrupted supervision.
  NO COLLAPSE:  the K = 2 circuit survives 3k of p = 0 — maintenance cost also scales with
    load, and the K = 4 maintenance threshold (~3-5%) is itself load-specific.
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import subprocess

DEP = 3000
RESCUE = 30000


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
    ap.add_argument("--kgen", default=os.path.expanduser("~/devaxis-work/kgenmx"))
    ap.add_argument("--runs", default="runs/kgen")
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
        rid = f"k2_s{s}"
        mp = os.path.join(a.kgen, f"{rid}.manifest.json")
        rj = os.path.join(a.runs, f"{rid}.json")
        cks = glob.glob(os.path.join(a.runs, "ckpt", rid, "step*.pt"))
        if not (os.path.exists(mp) and os.path.exists(rj) and cks):
            print(f"[skip] {rid}: missing manifest/run/ckpts")
            continue
        T = max(int(os.path.basename(c)[4:-3]) for c in cks)
        run = json.load(open(rj))
        q_at = {e["step"]: e.get("query_ctx") for e in run.get("evals", [])}
        if q_at.get(T, 0) < 0.75:
            print(f"[skip] {rid}: q@{T}={q_at.get(T)} < 0.75 — not a formed fork point")
            continue
        pman = json.load(open(mp))
        child = dict(pman)
        child.pop("condition", None)
        child.update(run_id=f"k2post_{rid}", parent_run_id=rid, fork_step=T,
                     resume_ckpt=os.path.abspath(os.path.join(a.runs, "ckpt", rid,
                                                              f"step{T}.pt")),
                     p_schedule=f"0:1.0,{T}:0.0,{T + DEP}:1.0",
                     steps=T + DEP + RESCUE, stop_at=2.0, ckpt_every=0,
                     ckpt_at=[T + 500, T + 1000, T + 1500, T + 2000, T + 3000,
                              T + 4000, T + 6000],
                     out_dir="runs/k2post",
                     data_streams=[dict(from_step=0, stream_id=rid)],
                     health_gate=dict(step=T + 2000, min_recap=0.5))
        p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
        with open(p, "w") as f:
            json.dump(child, f, indent=1)
        queue.append(dict(manifest=p, core=cores[n % len(cores)]))
        n += 1
    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[k2post] {n} runs (deprive {DEP} then rescue {RESCUE} from terminal ckpt) -> {a.out}")


if __name__ == "__main__":
    main()
