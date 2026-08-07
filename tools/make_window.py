"""Phase W — WHERE is the window?  Is this a critical PERIOD, or just "deprivation is bad"?

PRE-REGISTERED before any run.

The result so far is one deprivation window (tau = 10,000) applied at ONE developmental state
(step 4,000).  That establishes deprivation-at-4000 forecloses.  It does NOT establish a
critical period, which is a claim about DEVELOPMENTAL TIME: the same insult must matter more at
some ages than others.

So: hold the insult FIXED (tau = 10,000 deprived steps, identical schedule shape) and move the
age at which it is applied:

    fork at {1000, 2000, 4000, 8000, 12000}, then p = 0 for 10,000 steps, then p = 1.

Step 1,000-2,000 is early (read circuit still consolidating; recap saturates ~500).
Step 4,000 is the state already tested.
Step 8,000-12,000 straddles the baseline emergence band (median 9,750), so some parents will
already have the use circuit when the deprivation lands — the single most informative cell,
because an ALREADY-EMERGED model that is deprived and rescued tests whether the window closes
in one direction only.

Predictions, declared:
  CRITICAL PERIOD: foreclosure is age-dependent — worst in some middle band, absent late (an
    already-formed circuit survives deprivation), and possibly absent very early.
  NOT A PERIOD (just damage): every age forecloses equally.
  REVERSED: only late deprivation hurts — would refute the developmental framing entirely.

Each fork inherits its parent's data stream, so the only difference from the parent is the
schedule.  Parents supply their own controls: Q2 certified a no-op fork is BITWISE, so the
parent's own trajectory is the tau=0 arm at every age, for free.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess

TAU = 10000
AGES = [1000, 2000, 4000, 8000, 12000]
BUDGET = 80000


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
    ap.add_argument("--factorial", default=os.path.expanduser("~/devaxis-work/factorial"))
    ap.add_argument("--runs", default="runs/factorial")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cores", default="0-31")
    ap.add_argument("--seeds", type=int, default=5)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lo, hi = (int(x) for x in a.cores.split("-"))
    held = busy_cores()
    cores = [c for c in range(lo, hi + 1) if c not in held]
    assert cores, "no free cores"

    queue, n, skipped = [], 0, []
    for s in range(a.seeds):
        rid = f"q4_s{s}"
        mp = os.path.join(a.factorial, f"{rid}.manifest.json")
        if not os.path.exists(mp):
            continue
        pman = json.load(open(mp))
        for age in AGES:
            ck = os.path.join(a.runs, "ckpt", rid, f"step{age}.pt")
            if not os.path.exists(ck):
                skipped.append(f"{rid}@{age}")
                continue
            child = dict(pman)
            child.pop("condition", None)
            child.update(run_id=f"win{age}_{rid}", parent_run_id=rid, fork_step=age,
                         resume_ckpt=os.path.abspath(ck),
                         p_schedule=f"0:1.0,{age}:0.0,{age + TAU}:1.0",
                         steps=BUDGET, stop_at=0.90, ckpt_every=0, ckpt_at=[],
                         out_dir="runs/window",
                         data_streams=[dict(from_step=0, stream_id=rid)],
                         health_gate=dict(step=age + 2000, min_recap=0.5))
            p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
            with open(p, "w") as f:
                json.dump(child, f, indent=1)
            queue.append(dict(manifest=p, core=cores[n % len(cores)]))
            n += 1
    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[window] {n} runs ({len(AGES)} ages x {a.seeds} seeds) -> {a.out}"
          + (f" | skipped: {skipped}" if skipped else ""))


if __name__ == "__main__":
    main()
