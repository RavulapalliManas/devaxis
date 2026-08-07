"""Mutation tests: each sabotage must trip its detector; a clean run must trip none.

Fast tier (always): constant_loss / detached_head via gradient telemetry, 20 steps.
Slow tier (-m slow, run on cpu-angad before any Trainium hour): random_labels and
wrong_eval_position need a COMPETENT model to be detectable.  If the clean tiny run does not
emerge within budget the test SKIPS loudly — an unvalidated detector is reported as unvalidated,
never as passing (global CLAUDE.md §5.3)."""
import os

import pytest
import torch

from audit.mutations import detect
from diagnostics import battery
from generators.binding import Vocab, seq_len
from training import engine, checkpoint
from training.model import GPT

TINY = dict(init_seed=0, task=dict(K=2, D=8), model=dict(d=64, nl=2, nh=4), bs=32,
            lr=3e-3, wd=0.1, warmup=100, p_schedule="1.0", eval_every=10,
            eval_n=64, eval_bs=32)

# Dense-vocab regime for the slow detector tests: with ne=no=8 each entity recurs across
# sequences ~8x more often, and emergence is fast — MEASURED on cpu-angad 2026-08-07
# (probe_small_s0: qctx crossed 0.9 at step 1500; all default-vocab arms still at chance at
# 2000+).  Detector validity does not depend on the science regime, only on having a
# competent model.
DENSE = dict(init_seed=0, task=dict(K=2, D=8), model=dict(d=64, nl=2, nh=4),
             vocab=dict(ne=8, no=8, nd=32), bs=32, lr=3e-3, wd=0.1, warmup=100,
             p_schedule="1.0", eval_every=100, eval_n=64, eval_bs=32)


def test_clean_run_trips_nothing(tmp_path):
    man = dict(TINY, run_id="clean", steps=20, audit_mode=True, out_dir=str(tmp_path))
    rec = engine.run(man, "cpu")
    d = detect(rec)
    assert not d["constant_loss"] and not d["detached_head"]
    assert max(rec["audit"]["grad_total"]) > 0


def test_constant_loss_detected(tmp_path):
    man = dict(TINY, run_id="mconst", steps=20, out_dir=str(tmp_path))
    rec = engine.run(man, "cpu", mutate="constant_loss")
    assert detect(rec)["constant_loss"]


def test_detached_head_detected(tmp_path):
    man = dict(TINY, run_id="mdet", steps=20, out_dir=str(tmp_path))
    rec = engine.run(man, "cpu", mutate="detached_head")
    assert detect(rec)["detached_head"]


@pytest.mark.slow
def test_random_labels_and_eval_position(tmp_path):
    # Emergence is stochastic ACROSS DATA STREAMS at fixed init seed (measured: stream
    # probe_small_s0 emerged at step 1500; stream "sclean", same seed/config, was still at
    # chance at 6000).  So the clean arm PINS the validated stream — data_streams decouples
    # the bytes from run_id precisely so this is possible.  Threads=2 matches the validation
    # run (BLAS reduction order).
    torch.set_num_threads(2)
    out = str(tmp_path)
    clean = dict(DENSE, run_id="sclean", steps=6000, stop_at=0.9,
                 ckpt_every=1000, out_dir=out,
                 data_streams=[dict(from_step=0, stream_id="probe_small_s0")])
    crec = engine.run(clean, "cpu")
    final = crec["evals"][-1]["query_ctx"]
    if final < 0.8:
        pytest.skip(f"clean dense-vocab run did not emerge (qctx={final:.2f}) — "
                    "random_labels/wrong_eval_position detectors NOT validated")

    # random_labels: SAME stream, corrupted answer supervision -> must stay at chance
    mrec = engine.run(dict(DENSE, run_id="srand", steps=6000, out_dir=out,
                           data_streams=[dict(from_step=0, stream_id="probe_small_s0")]),
                      "cpu", mutate="random_labels")
    assert detect(mrec)["at_chance"], mrec["evals"][-1]

    # wrong_eval_position: the competent model read one position off -> collapses to chance
    cks = sorted((f for f in os.listdir(os.path.join(out, "ckpt", "sclean"))
                  if f.endswith(".pt")),
                 key=lambda f: int(f[4:-3]))          # numeric, not lexicographic
    v = Vocab(**DENSE["vocab"])
    torch.manual_seed(0)
    model = GPT(v.size, d=64, nl=2, nh=4, ctx=seq_len(2, 8))
    checkpoint.load(os.path.join(out, "ckpt", "sclean", cks[-1]), model, None, 3e-3, 100)
    # Offset -2 = the QMARK position, BEFORE the queried entity is revealed: chance there is
    # information-theoretic, for any model.  Offset -1 (the entity token) is NOT a valid
    # detector — the answer is already partially decodable one position early (measured 0.695
    # on this checkpoint vs chance 0.5; the represent-before-use signature).
    good = battery.behavioral(model, 2, 8, v, "cpu", n=128, bs=64)["query_ctx"]
    off = battery.behavioral(model, 2, 8, v, "cpu", n=128, bs=64, ans_offset=-2)["query_ctx"]
    assert good >= 0.8 and off <= 0.5 + 0.12, (good, off)
