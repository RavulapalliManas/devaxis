"""Bisect the Neuron NaN: which factor turns a training run into NaN loss / flat recap?

The reference (CPU) trains this task to recap 1.0 within ~500 steps.  On Neuron the full
factorial config produced NaN loss and recap 0.000 for 36k steps, while the tiny smoke config
(d64/nl2/bs32/K2/D8) trained normally.  Each arm below changes ONE factor from the failing
config.  400 steps each is far past the point where a healthy run has recap > 0.5.

Arms are launched one per NeuronCore and evaluated on: max |loss| finite? recap risen?
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys

FAIL = dict(task=dict(K=4, D=32), model=dict(d=256, nl=6, nh=8), bs=128,
            lr=3e-3, wd=0.1, warmup=500, p_schedule="1.0", steps=400,
            eval_every=100, eval_n=128, eval_bs=64, out_dir="runs/nanbisect")

ARMS = {
    "A_repro":     {},                                     # control: the failing config
    "B_smoke":     dict(task=dict(K=2, D=8), model=dict(d=64, nl=2, nh=4), bs=32),
    "C_finite":    dict(mask_value="finite"),              # XLA-safe attention mask
    "D_explicit":  dict(attn="explicit"),
    "E_bf16":      dict(precision="bf16_autocast"),
    "F_bs32":      dict(bs=32),
    "G_nl2":       dict(model=dict(d=256, nl=2, nh=8)),
    "H_ctx22":     dict(task=dict(K=2, D=8)),
    "I_fin_expl":  dict(mask_value="finite", attn="explicit"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=400)
    a = ap.parse_args()
    os.makedirs("logs", exist_ok=True)
    procs = {}
    for core, (name, over) in enumerate(ARMS.items()):
        man = dict(FAIL, **over, run_id=name, init_seed=0, steps=a.steps)
        path = f"/tmp/nan_{name}.json"
        with open(path, "w") as f:
            json.dump(man, f)
        env = dict(os.environ, NEURON_RT_VISIBLE_CORES=str(core))
        log = open(f"logs/nan_{name}.log", "w")
        procs[name] = subprocess.Popen(
            [sys.executable, "-m", "training.train", "--manifest", path, "--backend", "neuron"],
            env=env, stdout=log, stderr=subprocess.STDOUT)
        print(f"[bisect] {name} -> core {core}", flush=True)
    for name, p in procs.items():
        p.wait()
    print("\n=== VERDICTS ===")
    for name in ARMS:
        f = f"runs/nanbisect/{name}.json"
        if not os.path.exists(f):
            print(f"{name:12s} NO OUTPUT (crashed — see logs/nan_{name}.log)")
            continue
        r = json.load(open(f))
        ev = r["evals"]
        losses = [e.get("train_loss_mean") for e in ev if e.get("train_loss_mean") is not None]
        finite = [x for x in losses if x == x]                      # NaN != NaN
        recap = max(e["recap"] for e in ev)
        print(f"{name:12s} loss_finite={len(finite)}/{len(losses)} "
              f"last_loss={losses[-1] if losses else None} max_recap={recap:.3f} "
              f"{'HEALTHY' if finite and recap > 0.3 else 'BROKEN'}")


if __name__ == "__main__":
    main()
