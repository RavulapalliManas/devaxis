"""Phase K-tau — is the deprivation dose-response K-general, or a K=4 artefact?

PRE-REGISTERED before any run of this phase.

The headline result is measured entirely at K = 4: forking a pre-emergence model and cutting
use-supply for tau steps forecloses formation, monotonically in tau (tau = 0 -> 7/7 emerged,
2k -> 4/8, 5k -> 2/8, 10k -> 0/7, 20k -> 0/8; Cochran-Armitage p = 7.8e-05).  Fresh K = 2
baselines have now emerged 8/8 (steps 1,750-8,500), so the same fork-and-deprive design can be
run at half the binding load with nothing new to build.

DESIGN.  Mirror `make_tau_sweep.py` exactly, changing only what the load forces:

  * fork age.  The K = 4 sweep forks at 4,000, which is pre-emergence for every K = 4 parent.
    K = 2 develops ~4x faster (median emergence ~3,100 vs ~12,000), so 4,000 is POST-emergence
    for most K = 2 parents and would silently convert a formation experiment into a maintenance
    one.  Forking at 1,000 preserves the design property that matters -- pre-emergence for all
    8 parents (earliest emergence 1,750) -- rather than the raw number.
  * everything else is held: p(step) = 1 before the fork, 0 for tau steps, 1 after; the same
    70,000-step budget; the same stop_at = 0.90 mastery bar; the same health gate; the parent's
    own data stream, so the child sees the same tokens it would have seen.

tau in {2000, 5000, 10000}: the three absolute doses the K = 4 sweep also ran, so the two curves
are directly comparable dose by dose.  tau = 0 needs no compute -- it is the parent trajectory
(8/8 emerged), which Q2 certified is reproduced bitwise by a no-op fork.

PREDICTIONS, stated before the data, and they differ:

  SUPPLY-DEPENDENCE (dose in absolute steps is what matters).  The K = 2 curve tracks the K = 4
    curve: ~4/8 at tau = 2k, ~2/8 at 5k, ~0/8 at 10k.
  DEVELOPMENTAL TIMESCALE (dose relative to the load's own emergence time is what matters).
    K = 2 is MORE fragile at equal absolute tau, because 2,000 steps is ~0.6 of its median
    emergence time but only ~0.17 of K = 4's.  Concretely: K = 2 at tau = 2k should already sit
    at or below K = 4's tau = 5k rate.
  NULL.  All three K = 2 arms emerge 8/8 -> the foreclosure is specific to K = 4 and the account
    is narrower than it has been stated.  This one would force a retraction, so it is worth
    running for that reason alone.

Primary endpoint, as in the K = 4 sweep: P(emerge) per tau, plus emergence delay measured in
USE-SUPPLIED steps, (emergence_step - (1000 + tau)) against the parent's (emergence_step - 1000).
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess

FORK_STEP = 1000
TAUS = [2000, 5000, 10000]
BUDGET = 70000


def busy_cores():
    """Cores already held by a live trainer.  Assigning a job to a busy NeuronCore makes it fail
    at runtime init and leave no run JSON at all -- that is how 6 branch-matrix runs went
    silently absent on 2026-08-08."""
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
    print(f"[cores] avoiding busy cores {sorted(held)}; using {len(cores)}")
    assert cores, "no free cores"

    parents = []
    for s in range(8):
        rid = f"k2_s{s}"
        ck = os.path.join(a.runs, "ckpt", rid, f"step{FORK_STEP}.pt")
        man = os.path.join(a.kgen, f"{rid}.manifest.json")
        if os.path.exists(ck) and os.path.exists(man):
            parents.append(rid)
        else:
            print(f"[skip] {rid}: ckpt={os.path.exists(ck)} manifest={os.path.exists(man)}")

    queue, n = [], 0
    for rid in parents:
        pman = json.load(open(os.path.join(a.kgen, f"{rid}.manifest.json")))
        for tau in TAUS:
            child = dict(pman)
            child.pop("condition", None)
            child.update(run_id=f"k2tau{tau}_{rid}", parent_run_id=rid, fork_step=FORK_STEP,
                         resume_ckpt=os.path.abspath(os.path.join(a.runs, "ckpt", rid,
                                                                  f"step{FORK_STEP}.pt")),
                         p_schedule=f"0:1.0,{FORK_STEP}:0.0,{FORK_STEP + tau}:1.0",
                         steps=BUDGET, stop_at=0.90, ckpt_every=0, ckpt_at=[],
                         out_dir="runs/kgen_tau",
                         data_streams=[dict(from_step=0, stream_id=rid)],
                         health_gate=dict(step=FORK_STEP + 2000, min_recap=0.5))
            p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
            with open(p, "w") as f:
                json.dump(child, f, indent=1)
            queue.append(dict(manifest=p, core=cores[n % len(cores)]))
            n += 1
    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[kgen_tau] {n} runs ({len(parents)} parents x {len(TAUS)} taus) -> {a.out}")


if __name__ == "__main__":
    main()
