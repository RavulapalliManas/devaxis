"""Phase X — the experiment that could demolish the headline result. Run it first.

THE ALTERNATIVE EXPLANATION.  AdamW applies DECOUPLED weight decay: every step, every
parameter is multiplied by (1 - lr*wd), whether or not it received a task gradient.  Here
lr*wd = 3e-3 * 0.1 = 3e-4.  During deprivation the recap tokens stay supervised, so read-circuit
parameters keep getting gradient and are held up — which is exactly why recap stays 1.000.  But
any parameter serving ONLY the answer site gets no gradient and decays geometrically:

    tau      surviving multiplier (1-3e-4)^tau      observed emergence rate
      0                              1.000                             1.00
   2000                              0.549                             0.50
   5000                              0.223                             0.25
  10000                              0.050                             0.00
  20000                              0.002                             0.00

The dose-response tracks the decay curve almost exactly.  If that is the mechanism, then this
is NOT a developmental critical period at all: it is weight decay quietly erasing a sub-circuit
that has no gradient to defend it, and the "foreclosure" is erosion, not commitment.

THE TEST.  Repeat the deprivation with weight decay switched OFF from the fork onward:

  noop_wd0      p = 1, wd = 0                 control: does wd=0 alone change emergence?
  resc10k_wd0   tau = 10,000, wd = 0          the decisive arm
  resc20k_wd0   tau = 20,000, wd = 0          the arm where decay predicts total erasure

Declared interpretation, before the data:
  * If foreclosure DISAPPEARS at wd = 0 -> the mechanism is weight decay. The developmental
    framing is retired; the honest result becomes "an unsupervised sub-circuit is erased by
    decoupled weight decay at a rate set by lr*wd", which is useful, mundane, and actionable
    (it predicts the effect scales with lr*wd*tau, not with developmental state).
  * If foreclosure PERSISTS at wd = 0 -> the single most plausible mundane explanation is dead,
    and the developmental account survives its hardest test so far.
  * If it partly survives -> decompose: decay explains part, something else explains the rest.

This runs BEFORE any further elaboration of the developmental story, because if it comes back
the first way, everything built on top of that story would have to be withdrawn.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess

FORK = 4000
BUDGET = 70000
ARMS = {
    "noop_wd0":    "1.0",
    "resc10k_wd0": f"0:1.0,{FORK}:0.0,{FORK + 10000}:1.0",
    "resc20k_wd0": f"0:1.0,{FORK}:0.0,{FORK + 20000}:1.0",
}


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
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lo, hi = (int(x) for x in a.cores.split("-"))
    cores = [c for c in range(lo, hi + 1) if c not in busy_cores()]
    assert cores, "no free cores"

    queue, n = [], 0
    for s in range(8):
        rid = f"q4_s{s}"
        mp = os.path.join(a.factorial, f"{rid}.manifest.json")
        ck = os.path.join(a.runs, "ckpt", rid, f"step{FORK}.pt")
        if not (os.path.exists(mp) and os.path.exists(ck)):
            continue
        pman = json.load(open(mp))
        for arm, sched in ARMS.items():
            child = dict(pman)
            child.pop("condition", None)
            child.update(run_id=f"wd0_{arm}_{rid}", parent_run_id=rid, fork_step=FORK,
                         resume_ckpt=os.path.abspath(ck), p_schedule=sched,
                         wd=0.0,                       # THE intervention
                         steps=BUDGET, stop_at=0.90, ckpt_every=0, ckpt_at=[],
                         out_dir="runs/wd0",
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
    print(f"[wd0] {n} runs ({len(ARMS)} arms) -> {a.out}")


if __name__ == "__main__":
    main()
