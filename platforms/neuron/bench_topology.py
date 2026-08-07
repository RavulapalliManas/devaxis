"""Q1: how many independent single-core processes does one trn1.32xlarge host sustain?

Grid nproc in {8,16,24,32}; each proc trains the REAL Phase-F config (K=4, D=32, bs=128) for
--steps steps on its own core.  Decision rule: largest nproc with >=80% scaling efficiency vs
the single-proc rate.  Writes gates/q1_topology.json.  Batch size is a scientific parameter —
it is NOT tuned here."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time


def run_wave(nproc: int, steps: int, manifest: str) -> dict:
    os.makedirs("logs", exist_ok=True)
    procs = []
    t0 = time.time()
    for c in range(nproc):
        env = dict(os.environ, NEURON_RT_VISIBLE_CORES=str(c))
        cmd = [sys.executable, "-m", "training.train", "--manifest", manifest,
               "--backend", "neuron",
               "--set", f"run_id=bench_n{nproc}_c{c}",
               "--set", f"steps={steps}",
               "--set", "out_dir=runs/bench",
               "--set", "ckpt_every=0", "--set", "stop_at=0"]
        log = open(f"logs/bench_n{nproc}_c{c}.log", "w")
        procs.append(subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT))
    rc = [p.wait() for p in procs]
    wall = time.time() - t0
    rates = []
    for c in range(nproc):
        rec = json.load(open(f"runs/bench/bench_n{nproc}_c{c}.json"))
        ev = rec["evals"]
        # steady-state rate from the last two eval points (skips compile + warmup)
        (s0, w0), (s1, w1) = [(e["step"], e["wall"]) for e in ev[-2:]]
        rates.append((s1 - s0) / (w1 - w0))
    return dict(nproc=nproc, rc=rc, wall_s=round(wall, 1),
                per_proc_steps_per_s=[round(r, 2) for r in rates],
                aggregate_steps_per_s=round(sum(rates), 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="configs/q4_baseline.json")
    ap.add_argument("--steps", type=int, default=1500)
    ap.add_argument("--grid", default="1,8,16,24,32")
    a = ap.parse_args()
    out = dict(steps=a.steps, waves=[])
    for n in [int(x) for x in a.grid.split(",")]:
        w = run_wave(n, a.steps, a.manifest)
        out["waves"].append(w)
        print(json.dumps(w), flush=True)
    base = out["waves"][0]["aggregate_steps_per_s"] / out["waves"][0]["nproc"]
    for w in out["waves"]:
        w["scaling_efficiency"] = round(w["aggregate_steps_per_s"] / (w["nproc"] * base), 3)
    chosen = max((w for w in out["waves"] if w["scaling_efficiency"] >= 0.8),
                 key=lambda w: w["nproc"], default=out["waves"][0])
    out["chosen_nproc"] = chosen["nproc"]
    os.makedirs("gates", exist_ok=True)
    with open("gates/q1_topology.json", "w") as f:
        json.dump(out, f, indent=1)
    print(f"[bench] chosen nproc = {out['chosen_nproc']} -> gates/q1_topology.json")


if __name__ == "__main__":
    main()
