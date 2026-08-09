"""Phase X8 — the delta=8000 column of the foreclosure clock.

PRE-REGISTERED before any run.  The measured chi(t, delta=4000) matrix shows a ~30x decay
over the first ~8k of deprivation, but two weaknesses remain: (1) the registered per-parent
paired sign test sits at p=0.070 because one slow-emerging parent (q4_s3) shows chi(0) ~ 0 —
a 4k pulse is below ITS formation timescale; (2) delta=1000 is below the instrument floor
entirely, so the matrix effectively has one usable column.  delta=8000 doubles the probe:
long enough that even slow parents' age-0 response should register, cheap enough to run at
three ages.

Ages {4000, 12000, 20000} (deprivation ages 0 / 8k / 16k) x delta=8000 x 8 parents = 24 forks
into runs/tomo_pulse with the tomo_a{age}_d8000_ naming, so analysis/chi_matrix.py and the
paired-decline analysis pick them up with no changes.  Controls: the existing trajectories
(age 12000+8000=20000 exact; age 20000+8000=28000 uses the trajectory's final logit at 24000
— the analysis already handles that case).  Prediction: the age-0 cell rises for ALL parents
including s3, and the >=8k cells stay ~0, pushing the paired decline to 8/8.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess

AGES = [4000, 12000, 20000]
DELTA = 8000


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
    ap.add_argument("--factorial", default=os.path.expanduser("~/devaxis-work/factorial"))
    ap.add_argument("--runs", default="runs/factorial")
    ap.add_argument("--traj-runs", default="runs/tomo_traj")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cores", default="0-31")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lo, hi = (int(x) for x in a.cores.split("-"))
    cores = [c for c in range(lo, hi + 1) if c not in busy_cores()] or list(range(lo, hi + 1))
    queue, n = [], 0
    for s in range(8):
        rid = f"q4_s{s}"
        mp = os.path.join(a.factorial, f"{rid}.manifest.json")
        if not os.path.exists(mp):
            continue
        pman = json.load(open(mp))
        for age in AGES:
            ck = (os.path.abspath(os.path.join(a.runs, "ckpt", rid, f"step{age}.pt"))
                  if age == 4000 else
                  os.path.abspath(os.path.join(a.traj_runs, "ckpt", f"tomotraj_{rid}",
                                               f"step{age}.pt")))
            if not os.path.exists(ck):
                print(f"[skip] {rid} age {age}")
                continue
            child = dict(pman)
            child.pop("condition", None)
            child.pop("health_gate", None)
            child.update(run_id=f"tomo_a{age}_d{DELTA}_{rid}", parent_run_id=rid,
                         fork_step=age, resume_ckpt=ck, p_schedule="0:1.0",
                         steps=age + DELTA, stop_at=2.0, ckpt_every=0, ckpt_at=[],
                         out_dir="runs/tomo_pulse",
                         data_streams=[dict(from_step=0, stream_id=rid)])
            p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
            with open(p, "w") as f:
                json.dump(child, f, indent=1)
            queue.append(dict(manifest=p, core=cores[n % len(cores)]))
            n += 1
    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[chi8k] {n} runs -> {a.out}")


if __name__ == "__main__":
    main()
