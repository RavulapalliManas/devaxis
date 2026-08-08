"""Phase P — the test the window sweep MISSED: deprive an ALREADY-FORMED circuit.

Why this is needed.  The window sweep (fixed tau = 10,000 at ages 1k/2k/4k/8k/12k) found
foreclosure at EVERY age: 1/22 runs emerged.  That looks like "deprivation damages at any age",
not a narrow window.  But the cell that would have decided it was never actually populated:
the parents present at ages 8,000 and 12,000 had NOT yet emerged at those steps (baseline
emergence median 9,750; the 12,000 cell contains q4_s0, which never emerged, and q4_s1, which
emerged at 15,500).  So every window run deprived a PRE-emergence model.  The asymmetry that
would make this developmental — a circuit that cannot FORM under deprivation but survives it
once FORMED — is untested.

This phase tests it directly.  For each parent that emerged, fork at the first checkpoint
strictly AFTER its own emergence step, so every fork starts from a model that demonstrably has
the use circuit, and apply the same two insults:

    postdep     p = 0 permanently      does a formed circuit DECAY without its supply?
    postresc    p = 0 for 10,000, then p = 1    if it decays, does it come back?

Declared predictions:
  ASYMMETRY (the developmental claim): the formed circuit persists, or decays and recovers
    quickly.  Combined with 0/22 formation under the same insult, that is a genuine
    formation-vs-maintenance dissociation.
  SYMMETRIC DAMAGE: the formed circuit decays and does not recover — deprivation is simply
    corrosive, and the "critical period" framing should be dropped in favour of a
    supply-dependence account.

Either outcome is worth having; the second would retire a framing I currently favour, which is
exactly why it is worth running.
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import subprocess

TAU = 10000
BUDGET_AFTER = 40000
ONSET = 0.625


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

    queue, n, notes = [], 0, []
    for s in range(8):
        rid = f"q4_s{s}"
        rec_p = os.path.join(a.runs, f"{rid}.json")
        man_p = os.path.join(a.factorial, f"{rid}.manifest.json")
        if not (os.path.exists(rec_p) and os.path.exists(man_p)):
            continue
        rec = json.load(open(rec_p))
        em = next((e["step"] for e in rec["evals"] if e.get("query_ctx", 0) >= ONSET), None)
        if em is None:
            notes.append(f"{rid}: never emerged, skipped")
            continue
        cks = sorted(int(os.path.basename(f)[4:-3])
                     for f in glob.glob(os.path.join(a.runs, "ckpt", rid, "step*.pt")))
        post = [c for c in cks if c > em]
        if not post:
            notes.append(f"{rid}: emerged {em} but no ckpt after it (have {cks})")
            continue
        fork = post[0]
        pman = json.load(open(man_p))
        for arm, sched in (("postdep", f"0:1.0,{fork}:0.0"),
                           ("postresc", f"0:1.0,{fork}:0.0,{fork + TAU}:1.0")):
            child = dict(pman)
            child.pop("condition", None)
            child.update(run_id=f"{arm}_{rid}", parent_run_id=rid, fork_step=fork,
                         resume_ckpt=os.path.abspath(
                             os.path.join(a.runs, "ckpt", rid, f"step{fork}.pt")),
                         p_schedule=sched, steps=fork + BUDGET_AFTER,
                         stop_at=0.0,                     # never early-stop: we want the DECAY
                         ckpt_every=0, ckpt_at=[], out_dir="runs/postem",
                         data_streams=[dict(from_step=0, stream_id=rid)],
                         health_gate=dict(step=fork + 2000, min_recap=0.5))
            p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
            with open(p, "w") as f:
                json.dump(child, f, indent=1)
            queue.append(dict(manifest=p, core=cores[n % len(cores)]))
            n += 1
        notes.append(f"{rid}: emerged {em}, forking at {fork} (post-emergence)")
    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[postem] {n} runs -> {a.out}")
    for x in notes:
        print(f"   {x}")


if __name__ == "__main__":
    main()
