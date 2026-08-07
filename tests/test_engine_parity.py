"""The engine must reproduce the committed fp64 golden loss trajectory (generated on cpu-angad by
tests/regen_goldens.py).  rtol 1e-7: fp64 at 30 steps leaves no room for a real engine change to
hide, while tolerating BLAS reduction-order differences across machines."""
import json
import os

import pytest
import torch

from training import engine

GOLDENS = os.path.join(os.path.dirname(__file__), "goldens.json")


def test_fp64_golden_trajectory(tmp_path):
    if not os.path.exists(GOLDENS):
        pytest.skip("goldens.json not yet generated (run python -m tests.regen_goldens)")
    gold = json.load(open(GOLDENS))["fp64_loss_trajectory"]
    torch.set_num_threads(1)
    man = dict(run_id="golden_fp64", init_seed=0, task=dict(K=2, D=8),
               model=dict(d=64, nl=2, nh=4), bs=32, lr=3e-3, wd=0.1, warmup=100,
               p_schedule="1.0", steps=30, eval_every=10, eval_n=64, eval_bs=32,
               precision="fp64", out_dir=str(tmp_path))
    rec = engine.run(man, "cpu")
    traj = [e["train_loss_mean"] for e in rec["evals"] if "train_loss_mean" in e]
    assert len(traj) == len(gold)
    for a, b in zip(traj, gold):
        assert abs(a - b) <= 1e-7 * max(abs(b), 1.0), (traj, gold)


def test_sync_every_windowing_identical_on_cpu(tmp_path):
    """sync_every changes only WHERE sync() lands (a no-op on cpu): records must be bitwise
    identical.  Guards the windowing/boundary logic, not numerics."""
    import torch as _t
    _t.set_num_threads(1)
    base = dict(run_id="w1", init_seed=5, task=dict(K=2, D=8), model=dict(d=64, nl=2, nh=4),
                bs=16, lr=3e-3, wd=0.1, warmup=100, p_schedule="1.0", steps=30,
                eval_every=10, eval_n=32, eval_bs=16, out_dir=str(tmp_path))
    r1 = engine.run(dict(base, run_id="w1"), "cpu")
    r5 = engine.run(dict(base, run_id="w5", sync_every=5,
                         data_streams=[dict(from_step=0, stream_id="w1")]), "cpu")
    for a, b in zip(r1["evals"], r5["evals"]):
        for k in ("recap", "query", "query_ctx", "train_loss_mean"):
            if k in a or k in b:
                assert a.get(k) == b.get(k), (k, a, b)
