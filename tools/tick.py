"""Supervision tick: what is not terminal, and what the branch arms are doing.  Read-only."""
from __future__ import annotations
import glob
import json
import os
import statistics
import sys

WORK = os.path.expanduser("~/devaxis-work")
ONSET = 0.625


def recs(d):
    out = []
    for f in sorted(glob.glob(os.path.join(WORK, "runs", d, "*.json"))):
        if f.endswith(".manifest.json"):
            continue
        try:
            out.append(json.load(open(f)))
        except Exception:
            pass
    return out


def em(r):
    return next((e["step"] for e in r.get("evals", []) if e.get("query_ctx", 0) >= ONSET), None)


for d in ("factorial", "branch", "tau", "dd10"):
    rs = recs(d)
    if not rs:
        print(f"== {d}: no runs yet")
        continue
    open_runs = [r for r in rs if not (r.get("done") or r.get("failed"))]
    print(f"== {d}: {len(rs)} runs, {len(rs)-len(open_runs)} terminal, {len(open_runs)} open")
    for r in open_runs:
        ev = r.get("evals") or [{}]
        print(f"   OPEN {r['run_id']:32s} step {ev[-1].get('step')}/{r['manifest']['steps']}"
              f" qctx {ev[-1].get('query_ctx')}")
    fails = [r for r in rs if r.get("failed")]
    for r in fails:
        print(f"   FAILED {r['run_id']}: {r['failed'][:70]}")

    if d == "branch":
        arms = {}
        for r in rs:
            arms.setdefault(r["run_id"].split("_")[1], []).append(r)
        print("   --- arm summary (fork at 4000; rescue restores supply at 14000) ---")
        for arm in sorted(arms):
            a = arms[arm]
            e = [em(r) for r in a if em(r)]
            steps = [(r.get("evals") or [{}])[-1].get("step", 0) for r in a]
            off = 14000 if arm == "rescue10k" else 4000
            delays = [x - off for x in e]
            print(f"   {arm:10s} n={len(a)} terminal={sum(1 for r in a if r.get('done') or r.get('failed'))}"
                  f" emerged={len(e)} max_step={max(steps) if steps else 0}"
                  + (f" median use-supplied delay={statistics.median(delays):.0f} {sorted(delays)}"
                     if delays else " (none emerged)"))
