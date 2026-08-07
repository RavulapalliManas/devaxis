"""Phase M — WHAT accumulates during deprivation and blocks the rescue?

PRE-REGISTERED before any run.

We know (p = 0.0078, paired, 7/7) that a 10k-step deprivation at a pre-emergence state prevents
the use circuit from ever forming, while the read circuit stays perfect (recap = 1.000) and the
gradient demonstrably returns (loss 0.0001 -> 0.19 at rescue).  So something the model CARRIES
blocks learning.  Three candidates, and each has a surgical test at the moment of rescue:

  plain     rescue exactly as before                       (replication arm, must fail again)
  optreset  restore WEIGHTS but not Adam moments           tests: is the block in the OPTIMIZER
                                                           state (stale second moments scaling
                                                           the answer-site gradient to nothing)?
  rewarm    restart the LR warmup ramp at the rescue step  tests: is it an optimization-scale
                                                           problem (the constant post-warmup LR
                                                           being too small to escape)?
  both      optreset + rewarm                              tests: the conjunction

Interpretation, declared in advance:
  * If `optreset` rescues and `rewarm` does not -> the blocker is OPTIMIZER STATE, not weights.
    That is a claim about training dynamics, and it predicts the effect vanishes with an
    optimizer that forgets (plain SGD) — a further falsifiable step.
  * If `rewarm` rescues -> the blocker is the LR/loss-landscape scale, i.e. the model sits in a
    basin it cannot leave at the standing learning rate.
  * If NEITHER rescues -> the block lives in the WEIGHTS themselves: a genuinely developmental
    foreclosure, not an optimizer artifact.  This is the strongest version of the result and
    the one that would make it interesting beyond this task.

Forks come from the DEPRIVED checkpoints (the deprive arm ran p=0 throughout), taken at the
step where the standard rescue would have happened, so every arm shares one parent state.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess

RESCUE_AT = 16000          # first ckpt_every=8000 boundary at/after the 14000 rescue point
BUDGET = 70000
ARMS = {
    "plain":    dict(),
    "optreset": dict(reset_optimizer=True),
    "rewarm":   dict(lr_rewarm=True),
    "both":     dict(reset_optimizer=True, lr_rewarm=True),
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
    ap.add_argument("--branchmx", default=os.path.expanduser("~/devaxis-work/branchmx"))
    ap.add_argument("--runs", default="runs/branch")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cores", default="0-31")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lo, hi = (int(x) for x in a.cores.split("-"))
    held = busy_cores()
    cores = [c for c in range(lo, hi + 1) if c not in held]
    assert cores, "no free cores"

    queue, n, skipped = [], 0, []
    for s in range(8):
        pid = f"br_deprive_q4_s{s}"
        mp = os.path.join(a.branchmx, f"{pid}.manifest.json")
        ck = os.path.join(a.runs, "ckpt", pid, f"step{RESCUE_AT}.pt")
        if not (os.path.exists(mp) and os.path.exists(ck)):
            skipped.append(pid)
            continue
        pman = json.load(open(mp))
        for arm, extra in ARMS.items():
            child = dict(pman)
            child.update(run_id=f"mech_{arm}_q4_s{s}", parent_run_id=pid,
                         fork_step=RESCUE_AT, resume_ckpt=os.path.abspath(ck),
                         p_schedule=f"0:1.0,4000:0.0,{RESCUE_AT}:1.0",
                         steps=BUDGET, stop_at=0.90, ckpt_every=0, ckpt_at=[],
                         out_dir="runs/mech",
                         health_gate=dict(step=RESCUE_AT + 2000, min_recap=0.5), **extra)
            p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
            with open(p, "w") as f:
                json.dump(child, f, indent=1)
            queue.append(dict(manifest=p, core=cores[n % len(cores)]))
            n += 1
    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[mech] {n} runs -> {a.out}" + (f" | skipped (no ckpt@{RESCUE_AT}): {skipped}"
                                           if skipped else ""))


if __name__ == "__main__":
    main()
