"""Build the DD factorial: run manifests + per-cell data manifests + queue.jsonl.

Design (pre-registered here, before any condition run starts):
  cells = {exact, paraphrase} x interval {50 (short), 500 (long)} x order {fixed, scrambled}
        = 8 cells, 3 seeds each = 24 condition runs
  + 8 baseline seeds (q4_s0..7, condition=none) = 32 runs = one full wave.
  Constants across all cells: rate=0.25, pool_size=64, K=4, D=32, bs=128, lr=3e-3, wd=0.1,
  warmup=500, steps=120000, stop_at=0.90, eval grid 250, ckpt_every=4000 + early forks
  {1000,2000,3000}.  The intended_difference between any two cells is exactly the named
  factor(s); everything else is byte-matched machinery.
  Primary endpoint (one, per master-plan 26.4): emergence step of query_ctx >= 0.625
  (right-censored at stop).  Secondary: recap trajectory, logit stats, branch responses.

Usage:  python tools/make_factorial.py --out ~/devaxis-work/factorial [--nproc 32]
"""
from __future__ import annotations
import argparse
import itertools
import json
import os

from generators import binding, keys, recurrence
from generators.binding import Vocab
from schemas.validate import validate_manifest, validate_data_manifest

BASE = dict(task=dict(K=4, D=32), model=dict(d=256, nl=6, nh=8), bs=128,
            lr=3e-3, wd=0.1, warmup=500, p_schedule="1.0", steps=120000,
            eval_every=250, logit_every=1000, stop_at=0.90,
            ckpt_every=4000, ckpt_at=[1000, 2000, 3000])
RATE, POOL = 0.25, 64
SEEDS = [0, 1, 2]
BASELINE_SEEDS = list(range(8))


def cell_name(rec, interval, order):
    sp = "short" if interval == 50 else "long"
    return f"dd_{rec}_{sp}_{order}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--nproc", type=int, default=32)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    v = Vocab()
    runs = []

    for s in BASELINE_SEEDS:
        man = dict(BASE, run_id=f"q4_s{s}", init_seed=s, out_dir="runs/factorial")
        validate_manifest(man)
        runs.append(man)

    for rec, interval, order in itertools.product(["exact", "paraphrase"], [50, 500],
                                                  ["fixed", "scrambled"]):
        cell = cell_name(rec, interval, order)
        cond = dict(recurrence=rec, rate=RATE, pool_size=POOL, interval=interval, order=order)
        golden = binding.batch_hash(recurrence.build_condition_batch(
            cond, BASE["bs"], 4, 32, 1.0, f"{cell}_s0", interval, v))
        dm = dict(condition_id=cell, generator_version=recurrence.CONDITION_VERSION,
                  vocab=dict(ne=v.ne, no=v.no, nd=v.nd), task=BASE["task"],
                  recurrence=rec, recurrence_rate=RATE,
                  spacing="short" if interval == 50 else "long", order=order,
                  golden_hashes=[dict(step=interval, sha256=golden)],
                  intended_difference=f"recurrence={rec}, interval={interval}, order={order} "
                                      f"vs baseline none; all else byte-matched machinery")
        validate_data_manifest(dm)
        with open(os.path.join(a.out, f"{cell}.data_manifest.json"), "w") as f:
            json.dump(dm, f, indent=1)
        for s in SEEDS:
            man = dict(BASE, run_id=f"{cell}_s{s}", init_seed=s, condition=cond,
                       out_dir="runs/factorial")
            validate_manifest(man)
            runs.append(man)

    assert len(runs) == 32, len(runs)
    queue = []
    for i, man in enumerate(runs):
        path = os.path.join(a.out, f"{man['run_id']}.manifest.json")
        with open(path, "w") as f:
            json.dump(man, f, indent=1)
        queue.append(dict(manifest=path, core=i % a.nproc))
    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[factorial] {len(runs)} runs -> {a.out} (queue over {a.nproc} cores)")


if __name__ == "__main__":
    main()
