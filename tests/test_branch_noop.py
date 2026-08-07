"""The no-op branch must reproduce its parent BITWISE on CPU (tier T0).  Single-threaded so
BLAS reduction order cannot differ between the two runs."""
import os

import torch

from training import engine, branch

MAN = dict(init_seed=3, task=dict(K=2, D=8), model=dict(d=64, nl=2, nh=4), bs=16,
           lr=3e-3, wd=0.1, warmup=100, p_schedule="1.0", eval_every=10,
           eval_n=32, eval_bs=16)


def test_noop_branch_T0(tmp_path):
    torch.set_num_threads(1)
    out = str(tmp_path)
    parent = dict(MAN, run_id="parent", steps=60, ckpt_at=[30, 60], out_dir=out)
    prec = engine.run(parent, "cpu")

    child = branch.fork(parent, os.path.join(out, "ckpt", "parent", "step30.pt"),
                        "child", out)
    crec = engine.run(dict(child, ckpt_at=[60]), "cpu")

    cert = branch.certify(prec, crec,
                          os.path.join(out, "ckpt", "parent", "step60.pt"),
                          os.path.join(out, "ckpt", "child", "step60.pt"))
    assert cert["tier"] == "T0", cert


def test_intervention_branch_diverges(tmp_path):
    """A stream-switch fork MUST diverge — a branch engine that cannot detect its own
    intervention is not measuring anything."""
    torch.set_num_threads(1)
    out = str(tmp_path)
    parent = dict(MAN, run_id="parent", steps=60, ckpt_at=[30, 60], out_dir=out)
    prec = engine.run(parent, "cpu")
    child = branch.fork(parent, os.path.join(out, "ckpt", "parent", "step30.pt"),
                        "childsw", out, switch_stream=True)
    crec = engine.run(dict(child, ckpt_at=[60]), "cpu")
    cert = branch.certify(prec, crec,
                          os.path.join(out, "ckpt", "parent", "step60.pt"),
                          os.path.join(out, "ckpt", "childsw", "step60.pt"))
    assert cert["tier"] != "T0" and not cert["bitwise"], cert
