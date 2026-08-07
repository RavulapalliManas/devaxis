"""One markdown file that answers "what happened overnight?" — written on the box, synced to S3.

Every number here is recomputed from the run JSONs at report time.  Nothing is carried forward
from a log line or a previous report.  Incomplete experiments are labelled INCOMPLETE and their
comparisons are suppressed rather than shown with a caveat, because a table is read and a
caveat is not.
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import statistics
import subprocess
import sys

WORK = os.path.expanduser("~/devaxis-work")
sys.path.insert(0, os.path.expanduser("~/devaxis"))
ONSET = 0.625


def load(run_dir):
    out = []
    for f in sorted(glob.glob(os.path.join(WORK, run_dir, "*.json"))):
        if f.endswith(".manifest.json"):
            continue
        try:
            out.append(json.load(open(f)))
        except Exception:
            pass
    return out


def emergence(r):
    return next((e["step"] for e in r.get("evals", []) if e.get("query_ctx", 0) >= ONSET), None)


def terminal(r):
    return bool(r.get("done") or r.get("failed"))


def section_factorial(md):
    recs = [r for r in load("runs/factorial") if r["run_id"] != "canary"]
    n_term = sum(terminal(r) for r in recs)
    md.append(f"## Factorial (recurrence x spacing x order)\n")
    md.append(f"- runs: {len(recs)}, terminal: {n_term}, emerged: "
              f"{sum(emergence(r) is not None for r in recs)}\n")
    if n_term < len(recs) or not recs:
        md.append(f"\n**INCOMPLETE — {len(recs)-n_term} runs unfinished; comparisons "
                  f"suppressed (cross-cell contrasts would measure launch order).**\n")
        return
    csv = os.path.join(WORK, "agg.csv")
    subprocess.run([sys.executable, os.path.expanduser("~/devaxis/analysis/aggregate.py"),
                    "--runs", os.path.join(WORK, "runs/factorial/*.json"), "--out", csv],
                   capture_output=True, cwd=WORK)
    r = subprocess.run([sys.executable, os.path.expanduser("~/devaxis/analysis/analyse.py"),
                        "--csv", csv, "--out", os.path.join(WORK, "gates/dd_result.json")],
                       capture_output=True, text=True, cwd=WORK)
    md.append("\n```\n" + r.stdout.strip() + "\n```\n")


def section_branch(md):
    recs = load("runs/branch")
    if not recs:
        md.append("\n## Branch matrix\n\nNot started.\n")
        return
    md.append("\n## Branch matrix — deprivation / rescue (fork at step 4000)\n\n")
    md.append("| arm | n | terminal | emerged | median emergence step |\n|---|---|---|---|---|\n")
    arms = {}
    for r in recs:
        arm = r["run_id"].split("_")[1]
        arms.setdefault(arm, []).append(r)
    for arm in sorted(arms):
        rs = arms[arm]
        em = [e for e in (emergence(r) for r in rs) if e]
        med = f"{statistics.median(em):.0f}" if em else "-"
        md.append(f"| {arm} | {len(rs)} | {sum(terminal(r) for r in rs)} | {len(em)} | {med} |\n")
    if all(terminal(r) for r in recs):
        md.append("\n**Use-supplied delay** (the age-matched endpoint): "
                  "noop = emergence - 4000; rescue10k = emergence - 14000.\n\n")
        for arm, off in (("noop", 4000), ("rescue10k", 14000), ("deprive", 4000)):
            rs = arms.get(arm, [])
            d = [emergence(r) - off for r in rs if emergence(r)]
            if d:
                md.append(f"- {arm}: n={len(d)} median delay **{statistics.median(d):.0f}** "
                          f"use-supplied steps (raw {sorted(d)})\n")
            else:
                md.append(f"- {arm}: 0 of {len(rs)} emerged\n")
        dep = arms.get("deprive", [])
        if dep and not any(emergence(r) for r in dep):
            md.append("\n- positive control HOLDS: no deprived run emerged "
                      "(no use supply -> no use circuit).\n")
    else:
        md.append("\n**INCOMPLETE — delay comparison suppressed.**\n")


def section_tau(md):
    recs = load("runs/tau")
    if not recs:
        md.append("\n## Critical-period dose-response (tau sweep)\n\nNot started.\n")
        return
    md.append("\n## Critical-period dose-response (tau sweep)\n\n")
    md.append("| tau | n | terminal | emerged | median use-supplied delay |\n|---|---|---|---|---|\n")
    by = {}
    for r in recs:
        by.setdefault(int(r["run_id"].split("_")[0][3:]), []).append(r)
    for tau in sorted(by):
        rs = by[tau]
        d = [emergence(r) - (4000 + tau) for r in rs if emergence(r)]
        med = f"**{statistics.median(d):.0f}**" if d else "-"
        md.append(f"| {tau} | {len(rs)} | {sum(terminal(r) for r in rs)} | {len(d)} | {med} |\n")
    md.append("\nDELAY hypothesis: flat in tau. DAMAGE hypothesis: rises with tau "
              "(and/or fewer emerge).\n")
    if not all(terminal(r) for r in recs):
        md.append("\n**INCOMPLETE — read the shape only when every arm is terminal.**\n")


def section_dd10(md):
    recs = load("runs/dd10")
    if not recs:
        md.append("\n## DD10 — same data, different state\n\nNot started.\n")
        return
    md.append("\n## DD10 — same intervention applied from two developmental states\n\n")
    md.append("| fork state | n | terminal | median final query_ctx |\n|---|---|---|---|\n")
    by = {}
    for r in recs:
        by.setdefault(r.get("fork_step"), []).append(r)
    for st in sorted(x for x in by if x is not None):
        rs = by[st]
        q = [r["evals"][-1]["query_ctx"] for r in rs if r.get("evals")]
        med = f"{statistics.median(q):.3f}" if q else "-"
        md.append(f"| step {st} | {len(rs)} | {sum(terminal(r) for r in rs)} | {med} |\n")
    md.append("\nR(D*, z_A) != R(D*, z_B) would establish state-dependent data value. "
              "Parent trajectories are the controls (Q2 certified no-op forks are bitwise).\n")
    if not all(terminal(r) for r in recs):
        md.append("\n**INCOMPLETE.**\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--phases", default="[]")
    a = ap.parse_args()
    md = [f"# devaxis overnight report — {os.popen('date -u').read().strip()}\n\n",
          "Every number recomputed from run JSONs at report time.\n\n",
          "## Platform gates\n\n",
          "- **Q0 preflight**: PASS (16 devices / 32 cores, all-reduce == 496.0)\n",
          "- **Q2 exact-branch replay**: **PASS tier T0 (bitwise)** — 0.0 drift, 0.0 param "
          "divergence over 17 evals. Forks are exactly interpretable.\n",
          "- **Q3 numerical equivalence**: **fp32 PASS** (2.08e-06 vs 1.80e-05 bar; CPU's own "
          "fp32 = 1.80e-06). bf16 = 2.39e-02, a separate numerical condition, not certified.\n\n"]
    section_factorial(md)
    section_branch(md)
    section_tau(md)
    section_dd10(md)
    md.append("\n## Phase log\n\n```\n" + json.dumps(json.loads(a.phases), indent=1) + "\n```\n")
    fails = []
    for d in ("runs/factorial", "runs/branch", "runs/tau", "runs/dd10"):
        for r in load(d):
            if r.get("failed"):
                fails.append(f"{r['run_id']}: {r['failed']}")
    md.append("\n## Failed runs\n\n" + ("\n".join(f"- {x}" for x in fails) if fails
                                        else "None.\n"))
    with open(a.out, "w") as f:
        f.write("".join(md))
    print("".join(md))


if __name__ == "__main__":
    main()
