"""Phase PR — the RESTORE-RATE dose-response: does restoring MORE supervision recover LESS?

PRE-REGISTERED before any run.  This is the cross-lab reconciliation experiment, and if the
non-monotone branch is what happens it is the most surprising result in the program.

THE PUZZLE.  Two labs, same task family, opposite conclusions:
  * devaxis (this repo): fork a formed K=2 circuit, cut supply for 10,000 steps, then restore
    at **p_after = 1.0** (FULL supervision) for 30-60k steps -> only 18/40 recover, median
    savings -0.44 (re-forming is SLOWER than learning from scratch).
  * h100-clocks X9: same construction, restore at **p_after = 0.01 / 0.02** -> 3/3 and 3/3
    recover, in 250-1,750 steps (67-96% savings).  Their p_after = 0.00 arm is 0/3, which is
    the degenerate case (no answer supervision at all — our own deprived trajectories already
    establish query stays at chance forever there, so it is a floor, not a rescue arm).

Their weakest supervision recovers BEST; our strongest recovers WORST.  Both cannot be
"how long you watch" — our window is 60k rescued steps (~19x the K=2 de-novo median), theirs
2x.  The remaining candidate explanations are (a) their deprivation was milder, or (b) THE
RESTORE RATE ITSELF MATTERS, non-monotonically.

Our own data already hints at (b) and it was misread at the time: continuous p = 0.03 recovered
two K=4 circuits FROM CHANCE (thresh phase, thr003_q4_s5/s6), while p = 1.0 restored after an
identical gap recovered 0 of ~21.  That was logged as continuity-vs-quantity; the rate reading
was never tested.

THE TEST.  Hold the parent, the deprivation, the byte stream and the budget FIXED, and vary
only the restore rate.  Parents k2_s24-s31 (tranche-2 seeds, chosen because their existing
p_after = 1.0 arms already ran at the SAME 60k horizon, so that arm needs no new compute):

    fork at the parent's terminal checkpoint | p = 0 for 10,000 | p = p_after for 60,000

    p_after in {0.01, 0.02, 0.05, 0.20}      (32 new runs)
    p_after = 1.00                            (existing k2postd10000_k2_s24..s31)
    p_after = 0.00                            (existing deprived trajectories: 0 by construction)

PREDICTIONS, stated before the data:
  MONOTONE (the boring, expected one): recovery rises with p_after; the h100/devaxis gap is
    then explained by deprivation severity, not rate, and their milder insult is the answer.
  NON-MONOTONE (the surprising one): recovery peaks at LOW p_after (~0.01-0.05) and FALLS at
    p_after = 1.0 — restoring a capability at full strength recovers it less often than
    dripping it back.  This reconciles both labs exactly, retro-explains our own thr003
    recoveries, and carries a blunt practical rule for continual pretraining: to revive a
    collapsed capability, do NOT blast it back.
  FLAT above zero: every p_after > 0 recovers alike; the two labs differ by deprivation
    severity and the restore rate is irrelevant.

PRIMARY ENDPOINT: recovery within budget per arm, paired by parent (each parent contributes
one run per arm); Cochran-Armitage trend across the five rate levels, and an exact paired
McNemar on the decisive p_after = 0.02 vs p_after = 1.00 contrast.  SECONDARY: rescued steps
to criterion (KM, rate as the group variable).

CONFOUND, NAMED: total supervision differs across arms by construction (rate x window).  That
is intended — the question is whether MORE total supervision, delivered faster, recovers less.
A dose-matched follow-up (equal integrated supervision, different rate x duration) is the
declared next experiment if the non-monotone branch fires.
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import subprocess

SEEDS = range(24, 32)
DEP, RESCUE = 10000, 60000
RATES = [0.01, 0.02, 0.05, 0.20]


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
    ap.add_argument("--kgen", default=os.path.expanduser("~/devaxis-work/k2exp2basemx"))
    ap.add_argument("--runs", default="runs/kgen")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cores", default="0-31")
    ap.add_argument("--dep", type=int, default=DEP,
                    help="deprivation length before restore; dep=2500 against the default "
                         "10000 at matched rates is the SEVERITY x RATE interaction that "
                         "settles the cross-lab discrepancy from our own data")
    ap.add_argument("--rates", default=",".join(str(x) for x in RATES))
    ap.add_argument("--during", default="0.0",
                    help="supply held DURING the gap (h100-clocks' p_after axis). "
                         "--during 0.01 --rates 1.0 is a direct replication of their "
                         "X9 cell in this codebase.")
    ap.add_argument("--tag", default="pr")
    a = ap.parse_args()
    rates = [float(x) for x in a.rates.split(",")]
    durings = [float(x) for x in a.during.split(",")]
    os.makedirs(a.out, exist_ok=True)
    lo, hi = (int(x) for x in a.cores.split("-"))
    cores = [c for c in range(lo, hi + 1) if c not in busy_cores()] or list(range(lo, hi + 1))

    queue, n, skipped = [], 0, []
    for s in SEEDS:
        rid = f"k2_s{s}"
        rj = os.path.join(a.runs, f"{rid}.json")
        cks = glob.glob(os.path.join(a.runs, "ckpt", rid, "step*.pt"))
        mp = os.path.join(a.kgen, f"{rid}.manifest.json")
        if not (os.path.exists(rj) and cks and os.path.exists(mp)):
            skipped.append(rid)
            continue
        r = json.load(open(rj))
        T = max(int(os.path.basename(c)[4:-3]) for c in cks)
        q_at = {e["step"]: e.get("query_ctx") for e in r.get("evals", [])}
        if q_at.get(T, 0) < 0.75:
            skipped.append(rid + "(not formed at ckpt)")
            continue
        pman = json.load(open(mp))
        for dv in durings:
         for pv in rates:
            child = dict(pman)
            child.pop("condition", None)
            child.update(run_id=f"{a.tag}{str(dv).replace('.', 'p')}r{str(pv).replace('.', 'p')}_{rid}" if dv else f"{a.tag}{str(pv).replace('.', 'p')}_{rid}", parent_run_id=rid,
                         fork_step=T,
                         resume_ckpt=os.path.abspath(os.path.join(a.runs, "ckpt", rid,
                                                                  f"step{T}.pt")),
                         p_schedule=f"0:1.0,{T}:{dv},{T + a.dep}:{pv}",
                         steps=T + a.dep + RESCUE, stop_at=2.0, ckpt_every=0,
                         ckpt_at=[T + a.dep, T + a.dep + 2000],
                         out_dir="runs/prestore",
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
    if skipped:
        print(f"[prestore] skipped: {skipped}")
    print(f"[prestore] {n} runs (dep={a.dep}, rates={rates}) -> {a.out}")


if __name__ == "__main__":
    main()
