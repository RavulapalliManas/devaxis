"""Phase K2X — confirmatory seed expansion of the gap-matched K=2 different-futures contrast.

PRE-REGISTERED before any run of this phase.

The exploratory result (n = 8 parents): with an IDENTICAL 10k supervision gap at K = 2,
never-formed models reacquired 8/8 while formed-then-collapsed models recovered 4/8
(k2postd10000: s1/s2/s6/s7 recovered at 3.7k/13k/11.5k/25k rescued steps; s0/s3/s4/s5 frozen
at chance through 30k rescued steps, recap 1.000).  Fisher two-sided p ~ 0.077 — the direction
of the CLD doc's Outcome A, below the bar.  Per that doc's own sample-size standard (>=24
parents for the decisive comparison), this phase adds 16 fresh parents and runs BOTH arms on
each, giving n = 24 per arm with every parent contributing a matched pair.

STAGE base: 16 fresh K = 2 baselines (seeds 8-23), identical config to the original eight
(they emerged 8/8 at steps 1,750-8,500).

STAGE arms (builds only when ALL 16 base runs are terminal — exits nonzero otherwise, which
the program runner treats as retry-next-cycle, so no silent partial design):
  * formed-collapsed: fork at the parent's terminal checkpoint (query >= 0.75), p = 0 for
    10,000, then p = 1 for 30,000 — the k2postd10000 construction, dense collapse ckpts;
  * never-formed:    fork at step 1,000 (pre-emergence for every original parent; verified
    per-parent here too), p = 0 until 11,000, then p = 1, budget 70,000 — the kgen_tau
    tau = 10k construction.
Both arms of one parent share the parent's byte stream.  All 32 arm runs write to
runs/k2exp so the phase has a single queue-vs-results diff.

PRIMARY ENDPOINT, declared now: per-parent PAIRED outcome (reacquired within budget:
never-formed vs formed-collapsed), exact McNemar over the 24 pairs (8 original + 16 new);
secondary: pooled Fisher, recovery-time distributions.  A pair where the never-formed arm
fails is evidence AGAINST the dissociation and is counted, not excused.
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import subprocess
import sys

SEEDS = range(8, 24)
DEP, RESCUE = 10000, 30000
TAU_FORK, TAU, TAU_BUDGET = 1000, 10000, 70000

BASE = dict(model=dict(d=256, nl=6, nh=8), bs=128, lr=3e-3, wd=0.1, warmup=500,
            p_schedule="1.0", steps=120000, eval_every=250, logit_every=1000, stop_at=0.90,
            mask_value="finite", ckpt_every=4000, ckpt_at=[1000, 2000, 3000],
            health_gate=dict(step=2000, min_recap=0.5))


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
    ap.add_argument("--stage", choices=["base", "arms"], required=True)
    ap.add_argument("--runs", default="runs/kgen")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cores", default="0-31")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lo, hi = (int(x) for x in a.cores.split("-"))
    cores = [c for c in range(lo, hi + 1) if c not in busy_cores()] or list(range(lo, hi + 1))
    queue, n = [], 0

    if a.stage == "base":
        for s in SEEDS:
            man = dict(BASE, run_id=f"k2_s{s}", init_seed=s, task=dict(K=2, D=32),
                       out_dir="runs/kgen")
            p = os.path.join(a.out, f"k2_s{s}.manifest.json")
            with open(p, "w") as f:
                json.dump(man, f, indent=1)
            queue.append(dict(manifest=p, core=cores[n % len(cores)]))
            n += 1
    else:
        missing = []
        for s in SEEDS:
            rid = f"k2_s{s}"
            rj = os.path.join(a.runs, f"{rid}.json")
            r = json.load(open(rj)) if os.path.exists(rj) else None
            cks = glob.glob(os.path.join(a.runs, "ckpt", rid, "step*.pt"))
            if not (r and (r.get("done") or r.get("failed")) and cks):
                missing.append(rid)
                continue
            T = max(int(os.path.basename(c)[4:-3]) for c in cks)
            q_at = {e["step"]: e.get("query_ctx") for e in r.get("evals", [])}
            crit = r["chance_query_ctx"] + 0.5 * (1 - r["chance_query_ctx"])
            e1k = next((e for e in r.get("evals", []) if e["step"] == TAU_FORK), None)
            if q_at.get(T, 0) < 0.75 or not os.path.exists(
                    os.path.join(a.runs, "ckpt", rid, f"step{TAU_FORK}.pt")):
                missing.append(rid + "(unusable)")
                continue
            if e1k and e1k.get("query_ctx", 0) >= crit:
                missing.append(rid + "(emerged-before-1k)")   # tau fork would not be pre-emergence
                continue
            man = json.load(open(os.path.join(a.out, "..", "k2expbasemx",
                                              f"{rid}.manifest.json"))) if os.path.exists(
                os.path.join(a.out, "..", "k2expbasemx", f"{rid}.manifest.json")) else dict(
                BASE, run_id=rid, init_seed=s, task=dict(K=2, D=32), out_dir="runs/kgen")
            # formed-collapsed arm
            c1 = dict(man)
            c1.update(run_id=f"k2postd10000_{rid}", parent_run_id=rid, fork_step=T,
                      resume_ckpt=os.path.abspath(os.path.join(a.runs, "ckpt", rid,
                                                               f"step{T}.pt")),
                      p_schedule=f"0:1.0,{T}:0.0,{T + DEP}:1.0",
                      steps=T + DEP + RESCUE, stop_at=2.0, ckpt_every=0,
                      ckpt_at=sorted({T + 500, T + 1000, T + 2000, T + DEP,
                                      T + DEP + 1000, T + DEP + 3000}),
                      out_dir="runs/k2exp",
                      data_streams=[dict(from_step=0, stream_id=rid)],
                      health_gate=dict(step=T + 2000, min_recap=0.5))
            # never-formed arm
            c2 = dict(man)
            c2.update(run_id=f"k2tau10000_{rid}", parent_run_id=rid, fork_step=TAU_FORK,
                      resume_ckpt=os.path.abspath(os.path.join(a.runs, "ckpt", rid,
                                                               f"step{TAU_FORK}.pt")),
                      p_schedule=f"0:1.0,{TAU_FORK}:0.0,{TAU_FORK + TAU}:1.0",
                      steps=TAU_BUDGET, stop_at=0.90, ckpt_every=0, ckpt_at=[],
                      out_dir="runs/k2exp",
                      data_streams=[dict(from_step=0, stream_id=rid)],
                      health_gate=dict(step=TAU_FORK + 2000, min_recap=0.5))
            for c in (c1, c2):
                p = os.path.join(a.out, f"{c['run_id']}.manifest.json")
                with open(p, "w") as f:
                    json.dump(c, f, indent=1)
                queue.append(dict(manifest=p, core=cores[n % len(cores)]))
                n += 1
        if missing:
            print(f"[k2exp:arms] NOT READY — missing/unusable parents: {missing}")
            sys.exit(1)          # BUILD_FAILED -> program retries next cycle

    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[k2exp:{a.stage}] {n} runs -> {a.out}")


if __name__ == "__main__":
    main()
