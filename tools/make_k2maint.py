"""Phase K2M — does the maintenance threshold scale with load?

PRE-REGISTERED before any run.  At K = 4 the maintenance dose-response is measured:
p = 0.01 -> 6/7 collapsed, p = 0.02 -> 2/7 near-collapse dips, p = 0.03 -> 2/7 dip-recover,
p = 0.04/0.05 -> 0/7.  "Keeping a capability alive costs ~3-5% of the supervision that created
it" is currently a K = 4-specific sentence.  With K = 2 formed parents now available (terminal
checkpoints, query 0.95-1.00), the same hold-at-p design runs at half the load.

DESIGN.  Fork each K = 2 parent at its terminal checkpoint and HOLD p in {0.005, 0.01, 0.03}
for 30,000 steps (no rescue — this measures the floor, not recovery).  8 parents x 3 doses =
24 runs.  p = 0.005 sits below K=4's certain-collapse dose; p = 0.01 is K=4's 6/7-collapse
dose; p = 0.03 is K=4's hold-with-dips dose.

Predictions, stated before the data:
  THRESHOLD SCALES WITH LOAD: K = 2 holds at p = 0.01 (7-8/8) where K = 4 collapsed 6/7, and
    plausibly even at 0.005 — lighter selection load is cheaper to maintain.  Combined with
    k2post (recovery works at K = 2), this makes load the master variable of the lifecycle.
  THRESHOLD IS LOAD-INVARIANT: K = 2 collapses at 0.01 like K = 4 — maintenance cost is a
    property of the training dynamics (e.g. interference from the ongoing recap objective),
    not of the circuit's size.
Endpoints: min query_ctx over the hold, and held-at-end (final query_ctx >= 0.75), per arm,
paired by parent.
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import subprocess

HOLD = 30000
DOSES = [0.005, 0.01, 0.03]


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
    ap.add_argument("--kgen", default=os.path.expanduser("~/devaxis-work/kgenmx"))
    ap.add_argument("--runs", default="runs/kgen")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cores", default="0-31")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lo, hi = (int(x) for x in a.cores.split("-"))
    cores = [c for c in range(lo, hi + 1) if c not in busy_cores()] or list(range(lo, hi + 1))

    queue, n = [], 0
    for s in range(8):
        rid = f"k2_s{s}"
        mp = os.path.join(a.kgen, f"{rid}.manifest.json")
        rj = os.path.join(a.runs, f"{rid}.json")
        cks = glob.glob(os.path.join(a.runs, "ckpt", rid, "step*.pt"))
        if not (os.path.exists(mp) and os.path.exists(rj) and cks):
            print(f"[skip] {rid}")
            continue
        T = max(int(os.path.basename(c)[4:-3]) for c in cks)
        run = json.load(open(rj))
        q_at = {e["step"]: e.get("query_ctx") for e in run.get("evals", [])}
        if q_at.get(T, 0) < 0.75:
            print(f"[skip] {rid}: q@{T}={q_at.get(T)}")
            continue
        pman = json.load(open(mp))
        for pv in DOSES:
            child = dict(pman)
            child.pop("condition", None)
            child.update(run_id=f"k2m{str(pv).replace('.', 'p')}_{rid}", parent_run_id=rid,
                         fork_step=T,
                         resume_ckpt=os.path.abspath(os.path.join(a.runs, "ckpt", rid,
                                                                  f"step{T}.pt")),
                         p_schedule=f"0:1.0,{T}:{pv}",
                         steps=T + HOLD, stop_at=2.0, ckpt_every=0, ckpt_at=[],
                         out_dir="runs/k2maint",
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
    print(f"[k2maint] {n} runs (hold p in {DOSES} for {HOLD}) -> {a.out}")


if __name__ == "__main__":
    main()
