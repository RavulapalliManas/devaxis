"""Canary-gated wave launch.  The one procedure that must never be skipped again.

    python tools/launch_wave.py --out ~/devaxis-work/factorial [--nproc 32]

1. Build manifests (pre-registered factorial).
2. Run the CANARY alone: same model/task/precision/mask as the science runs, 2000 steps.
   Two jobs at once: it proves the platform still trains this exact config, AND it populates
   the NEFF compile cache so the 32-way launch is a cache hit instead of a compile storm
   (32 simultaneous neuronx-cc processes SIGHUP'd each other on 2026-08-08).
3. Verify canary health from its run record: finite loss AND recap >= 0.5.  Abort otherwise —
   a failed canary is a platform finding, and 48 cores must not commit to a broken config.
4. Only then start the wave (staggered), and report what is running.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys

MIN_RECAP = 0.5


def sh(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=False, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--nproc", type=int, default=32)
    ap.add_argument("--skip-canary", action="store_true")
    a = ap.parse_args()
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    sh([sys.executable, os.path.join(here, "tools", "make_factorial.py"),
        "--out", a.out, "--nproc", str(a.nproc)])

    canary_man = os.path.join(a.out, "canary.manifest.json")
    canary_rec = os.path.join("runs", "factorial", "canary.json")
    if not a.skip_canary:
        env = dict(os.environ, NEURON_RT_VISIBLE_CORES="0")
        r = sh([sys.executable, "-m", "training.train", "--manifest", canary_man,
                "--backend", "neuron"], env=env)
        if r.returncode != 0 or not os.path.exists(canary_rec):
            print("[launch] CANARY FAILED TO RUN — wave NOT started", flush=True)
            sys.exit(2)
        rec = json.load(open(canary_rec))
        ev = rec["evals"]
        losses = [e.get("train_loss_mean") for e in ev if e.get("train_loss_mean") is not None]
        finite = [x for x in losses if x == x]
        recap = max(e["recap"] for e in ev)
        print(f"[launch] canary: finite_losses={len(finite)}/{len(losses)} max_recap={recap:.3f}")
        if len(finite) != len(losses) or recap < MIN_RECAP:
            print(f"[launch] CANARY UNHEALTHY (recap {recap:.3f} < {MIN_RECAP} or NaN loss) "
                  f"— wave NOT started", flush=True)
            sys.exit(3)
        print("[launch] canary HEALTHY — compile cache warm, starting wave", flush=True)

    os.makedirs("logs", exist_ok=True)
    log = open("logs/topology_wave.log", "a")
    p = subprocess.Popen([sys.executable, os.path.join(here, "platforms", "neuron", "topology.py"),
                          "--queue", os.path.join(a.out, "queue.jsonl")],
                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    print(f"[launch] wave dispatcher pid {p.pid} -> logs/topology_wave.log", flush=True)


if __name__ == "__main__":
    main()
