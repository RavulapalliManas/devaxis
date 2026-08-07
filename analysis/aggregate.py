"""runs/*.json -> one flat CSV.  No statistics here (three-script discipline: aggregate does
tables, analyse does stats, verify does invariants).  Emergence is scored at the sweep's onset
criterion query_ctx >= 0.625; a run that never crosses is RIGHT-CENSORED at its last eval step —
never substitute the max step as the transition time (master-plan §26.3)."""
from __future__ import annotations
import argparse
import csv
import glob
import json
import os

ONSET = 0.625


def row(rec: dict) -> dict:
    man = rec.get("manifest", {})
    evals = rec.get("evals", [])
    em = next((e["step"] for e in evals if e.get("query_ctx", 0) >= ONSET), None)
    last = evals[-1] if evals else {}
    return dict(
        run_id=rec.get("run_id"),
        parent_run_id=rec.get("parent_run_id"),
        fork_step=rec.get("fork_step"),
        backend=rec.get("backend"),
        precision=rec.get("precision"),
        mutate=rec.get("mutate"),
        K=man.get("task", {}).get("K"),
        D=man.get("task", {}).get("D"),
        bs=man.get("bs"), lr=man.get("lr"), wd=man.get("wd"), warmup=man.get("warmup"),
        p_schedule=man.get("p_schedule"), init_seed=man.get("init_seed"),
        nparam=rec.get("nparam"),
        emergence_step=em,
        censored=em is None,
        last_step=last.get("step"),
        final_recap=last.get("recap"),
        final_query_ctx=last.get("query_ctx"),
        done=rec.get("done", False),
        failed=rec.get("failed"),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True, help="glob, e.g. 'runs/*.json'")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    files = sorted(glob.glob(a.runs))
    rows = [row(json.load(open(f))) for f in files if not f.endswith(".manifest.json")]
    print(f"[aggregate] n = {len(rows)} run files (counted from filesystem)")
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"[aggregate] -> {a.out}")


if __name__ == "__main__":
    main()
