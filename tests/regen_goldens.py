"""Deliberately regenerate tests/goldens.json (generator byte hashes + fp64 loss trajectory).
Run ON cpu-angad; commit the result.  A regen without a GENERATOR_VERSION bump (for the generator
block) or an engine-change rationale (for the trajectory block) is a red flag in review."""
import json
import os
import tempfile

import torch

from generators import binding, keys
from generators.binding import Vocab
from training import engine

V = Vocab()
OUT = os.path.join(os.path.dirname(__file__), "goldens.json")


def main():
    torch.set_num_threads(1)
    gens = {
        "K4_D32_p1.0": binding.batch_hash(
            binding.build_batch(64, 4, 32, 1.0, keys.key("golden", "train", 0), V)),
        "K2_D8_p0.5": binding.batch_hash(
            binding.build_batch(64, 2, 8, 0.5, keys.key("golden", "train", 1), V)),
        "eval_batch0": binding.batch_hash(
            binding.build_batch(128, 4, 32, 1.0, keys.eval_key(0), V, force_loss=True)),
    }
    with tempfile.TemporaryDirectory() as td:
        man = dict(run_id="golden_fp64", init_seed=0, task=dict(K=2, D=8),
                   model=dict(d=64, nl=2, nh=4), bs=32, lr=3e-3, wd=0.1, warmup=100,
                   p_schedule="1.0", steps=30, eval_every=10, eval_n=64, eval_bs=32,
                   precision="fp64", out_dir=td)
        rec = engine.run(man, "cpu")
    traj = [e["train_loss_mean"] for e in rec["evals"] if "train_loss_mean" in e]
    with open(OUT, "w") as f:
        json.dump(dict(generators=gens, fp64_loss_trajectory=traj,
                       generator_version=binding.GENERATOR_VERSION), f, indent=1)
    print(f"wrote {OUT}")
    print(json.dumps(gens, indent=1))
    print("fp64 traj:", traj)


if __name__ == "__main__":
    main()
