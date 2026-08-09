"""Phase K6-tau — the K=6 deprivation dose-response (gated on K=6 baselines emerging).

PRE-REGISTERED before any run.  Third interior point of tau_c(K).  GATE: builds only when at
least 6 K=6 parents are terminal AND emerged AND pre-emergence at the fork age — otherwise
exits nonzero, which the program runner retries next cycle (no silent partial design).  If
K=6 turns out to emerge as rarely as K=8 (2/8 by 120k), this phase never builds and that
non-build is itself the K=6 data point.

Fork at 4000 (must verify pre-emergence per parent from the run's own evals), tau in
{2000, 5000, 10000}, budget 120,000 (K=6 formation may be slow; stop_at 0.90 ends early).
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys

FORK, TAUS, BUDGET = 4000, [2000, 5000, 10000], 120000


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
    ap.add_argument("--k36", default=os.path.expanduser("~/devaxis-work/k36mx"))
    ap.add_argument("--runs", default="runs/kgen")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cores", default="0-31")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lo, hi = (int(x) for x in a.cores.split("-"))
    cores = [c for c in range(lo, hi + 1) if c not in busy_cores()] or list(range(lo, hi + 1))

    usable = []
    for s in range(8):
        rid = f"k6_s{s}"
        rj = os.path.join(a.runs, f"{rid}.json")
        ck = os.path.join(a.runs, "ckpt", rid, f"step{FORK}.pt")
        r = json.load(open(rj)) if os.path.exists(rj) else None
        if not (r and (r.get("done") or r.get("failed")) and os.path.exists(ck)):
            continue
        crit = r["chance_query_ctx"] + 0.5 * (1 - r["chance_query_ctx"])
        emerged = any(e.get("query_ctx", 0) >= crit for e in r.get("evals", []))
        efork = next((e for e in r.get("evals", []) if e["step"] == FORK), None)
        pre = not (efork and efork.get("query_ctx", 0) >= crit)
        if emerged and pre:
            usable.append(rid)
    if len(usable) < 6:
        print(f"[k6tau] NOT READY — usable emerged parents: {usable} ({len(usable)}/6 needed)")
        sys.exit(1)

    queue, n = [], 0
    for rid in usable:
        pman = json.load(open(os.path.join(a.k36, f"{rid}.manifest.json")))
        for tau in TAUS:
            child = dict(pman)
            child.pop("condition", None)
            child.update(run_id=f"k6tau{tau}_{rid}", parent_run_id=rid, fork_step=FORK,
                         resume_ckpt=os.path.abspath(os.path.join(a.runs, "ckpt", rid,
                                                                  f"step{FORK}.pt")),
                         p_schedule=f"0:1.0,{FORK}:0.0,{FORK + tau}:1.0",
                         steps=BUDGET, stop_at=0.90, ckpt_every=0, ckpt_at=[],
                         out_dir="runs/k6tau",
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
    print(f"[k6tau] {n} runs ({len(usable)} parents) -> {a.out}")


if __name__ == "__main__":
    main()
