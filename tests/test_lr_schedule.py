"""Regression for the critical_period.py LR bug (opt.step() before the LR assignment -> one
500x-oversized first step on every process start).  In devaxis the schedule is a pure function
applied BEFORE opt.step(); these tests pin that, including across a resume."""
import json
import os

import torch

from generators.binding import seq_len
from training import engine, checkpoint
from training.model import GPT
from training.optim import lr_at, make_optimizer

MAN = dict(init_seed=0, task=dict(K=2, D=8), model=dict(d=64, nl=2, nh=4), bs=16,
           lr=3e-3, wd=0.1, warmup=100, p_schedule="1.0", eval_every=2,
           eval_n=32, eval_bs=16)


def test_lr_at_matches_lag_law_const_schedule():
    # LambdaLR(lambda s: min(1,(s+1)/warmup)) applies lambda(s) to optimizer step s
    assert lr_at(0, 3e-3, 500) == 3e-3 * (1 / 500)
    assert lr_at(499, 3e-3, 500) == 3e-3
    assert lr_at(10_000, 3e-3, 500) == 3e-3


def test_first_step_lr_is_warmup_not_base(tmp_path):
    man = dict(MAN, run_id="lr0", steps=2, out_dir=str(tmp_path))
    rec = engine.run(man, "cpu")
    assert rec["evals"][0]["lr"] == lr_at(0, 3e-3, 100)   # NOT 3e-3


def test_resume_lr_asserted(tmp_path):
    man = dict(MAN, run_id="lrres", steps=6, ckpt_at=[4], out_dir=str(tmp_path))
    engine.run(man, "cpu")
    ck = os.path.join(str(tmp_path), "ckpt", "lrres", "step4.pt")
    side = json.load(open(ck + ".manifest.json"))
    assert side["lr"] == lr_at(4, 3e-3, 100)
    torch.manual_seed(0)
    model = GPT(392, d=64, nl=2, nh=4, ctx=seq_len(2, 8))
    opt = make_optimizer(model, 3e-3, 0.1)
    step = checkpoint.load(ck, model, opt, 3e-3, 100)
    assert step == 4
    assert opt.param_groups[0]["lr"] == lr_at(4, 3e-3, 100)


def test_reset_optimizer_and_lr_rewarm(tmp_path):
    """Mechanism-probe knobs: reset_optimizer must drop Adam moments (so the first post-resume
    update differs), and lr_rewarm must restart the warmup ramp at the fork step."""
    from training.optim import lr_at as _lr
    base = dict(MAN, steps=6, ckpt_at=[4], out_dir=str(tmp_path))
    engine.run(dict(base, run_id="mp"), "cpu")
    ck = os.path.join(str(tmp_path), "ckpt", "mp", "step4.pt")
    plain = engine.run(dict(base, run_id="mp_plain", resume_ckpt=ck, steps=6), "cpu")
    rewarm = engine.run(dict(base, run_id="mp_rewarm", resume_ckpt=ck, steps=6,
                             lr_rewarm=True), "cpu")
    # lr_rewarm restarts the ramp: at step 4 it must equal lr(0), not lr(4)
    assert plain["evals"][0]["lr"] == _lr(4, 3e-3, 100)
    assert rewarm["evals"][0]["lr"] == _lr(0, 3e-3, 100)
    # reset_optimizer must load without an optimizer state and still run
    reset = engine.run(dict(base, run_id="mp_reset", resume_ckpt=ck, steps=6,
                            reset_optimizer=True), "cpu")
    assert reset["evals"][-1]["step"] == 6
