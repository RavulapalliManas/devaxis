"""One-shot wave status: per-run step rates from run JSONs, NeuronCore utilization from one
neuron-monitor sample, host load.  Read-only; safe while the wave runs.  Run on the box:
    python ~/devaxis/tools/wave_status.py [--runs ~/devaxis-work/runs/factorial]
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import subprocess


def run_rates(runs_dir: str):
    rows = []
    for f in sorted(glob.glob(os.path.join(runs_dir, "*.json"))):
        if f.endswith(".manifest.json"):
            continue
        try:
            r = json.load(open(f))
        except Exception:
            continue
        ev = r.get("evals", [])
        if len(ev) >= 2:
            (s0, w0), (s1, w1) = [(e["step"], e["wall"]) for e in ev[-2:]]
            rate = (s1 - s0) / max(w1 - w0, 1e-9)
            em = next((e["step"] for e in ev if e.get("query_ctx", 0) >= 0.625), None)
            rows.append(dict(run=r["run_id"], step=s1, rate=rate,
                             qctx=ev[-1].get("query_ctx"), emerged=em,
                             done=r.get("done", False), failed=r.get("failed")))
    return rows


def neuron_util():
    try:
        p = subprocess.run(["timeout", "8", "neuron-monitor"], capture_output=True, text=True)
        line = p.stdout.splitlines()[0]
        d = json.loads(line)
        u = []
        for g in d.get("neuron_runtime_data", []):
            nc = g.get("report", {}).get("neuroncore_counters", {})
            for v in nc.get("neuroncores_in_use", {}).values():
                u.append(v.get("neuroncore_utilization", 0.0))
        return u
    except Exception as e:
        return f"neuron-monitor unavailable: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default=os.path.expanduser("~/devaxis-work/runs/factorial"))
    a = ap.parse_args()
    rows = run_rates(a.runs)
    rows.sort(key=lambda r: r["rate"])
    print(f"runs reporting: {len(rows)}")
    if rows:
        rates = [r["rate"] for r in rows]
        print(f"steps/s per run: min {rates[0]:.3f} median {rates[len(rates)//2]:.3f} "
              f"max {rates[-1]:.3f} | aggregate {sum(rates):.2f}")
        print(f"steps: min {min(r['step'] for r in rows)} max {max(r['step'] for r in rows)}")
        em = [r for r in rows if r["emerged"]]
        print(f"emerged (qctx>=0.625): {len(em)} -> {[(r['run'], r['emerged']) for r in em]}")
        bad = [r for r in rows if r["failed"]]
        if bad:
            print("FAILED runs:", [(r["run"], r["failed"]) for r in bad])
        done = [r["run"] for r in rows if r["done"]]
        if done:
            print("done:", done)
    u = neuron_util()
    if isinstance(u, list) and u:
        print(f"neuroncore util % (n={len(u)}): mean {sum(u)/len(u):.1f} "
              f"min {min(u):.1f} max {max(u):.1f}")
    else:
        print(u)
    print("host:", open("/proc/loadavg").read().strip())


if __name__ == "__main__":
    main()
