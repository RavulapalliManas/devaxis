"""Condition-layer contract: exact recurrence is byte-identical across visits; paraphrase
preserves the latent program and changes the surface; off-schedule steps and the none
condition reduce to the plain generator."""
import numpy as np

from generators import binding, keys, recurrence
from generators.binding import Vocab

V = Vocab()
K, D, BS = 4, 32, 64


def rows_hash(b, m):
    import hashlib
    return hashlib.sha256(b["ids"][:m].tobytes() + b["tgt"][:m].tobytes()).hexdigest()


def test_none_equals_plain():
    cond = dict(recurrence="none")
    a = recurrence.build_condition_batch(cond, BS, K, D, 1.0, "s", 7, V)
    b = binding.build_batch(BS, K, D, 1.0, keys.key("s", "train", 7), V)
    assert binding.batch_hash(a) == binding.batch_hash(b)


def test_off_schedule_step_is_fresh():
    cond = dict(recurrence="exact", rate=0.5, pool_size=16, interval=50, order="fixed")
    a = recurrence.build_condition_batch(cond, BS, K, D, 1.0, "s", 51, V)
    b = binding.build_batch(BS, K, D, 1.0, keys.key("s", "train", 51), V)
    assert binding.batch_hash(a) == binding.batch_hash(b)


def test_exact_bytes_identical_across_visits():
    m = 32
    cond = dict(recurrence="exact", rate=m / BS, pool_size=m, interval=50, order="fixed")
    v1 = recurrence.build_condition_batch(cond, BS, K, D, 1.0, "s", 50, V)
    v2 = recurrence.build_condition_batch(cond, BS, K, D, 1.0, "s", 100, V)
    assert rows_hash(v1, m) == rows_hash(v2, m)          # pool rows: byte-identical
    assert binding.batch_hash(v1) != binding.batch_hash(v2)   # fresh rows differ


def test_paraphrase_same_program_new_surface():
    m = 32
    cond = dict(recurrence="paraphrase", rate=m / BS, pool_size=m, interval=50, order="fixed")
    v1 = recurrence.build_condition_batch(cond, BS, K, D, 1.0, "s", 50, V)
    v2 = recurrence.build_condition_batch(cond, BS, K, D, 1.0, "s", 100, V)
    assert rows_hash(v1, m) != rows_hash(v2, m)          # surface differs
    # latent program identical: declaration entities and obligations agree row-for-row
    assert (v1["ids"][:m, 1:1 + 2 * K] == v2["ids"][:m, 1:1 + 2 * K]).all()
    # distractors differ somewhere
    d = slice(2 * K + 1, 2 * K + 1 + D)
    assert (v1["ids"][:m, d] != v2["ids"][:m, d]).any()


def test_scrambled_differs_from_fixed():
    cond_f = dict(recurrence="exact", rate=0.25, pool_size=64, interval=50, order="fixed")
    cond_s = dict(recurrence="exact", rate=0.25, pool_size=64, interval=50, order="scrambled")
    a = recurrence.build_condition_batch(cond_f, BS, K, D, 1.0, "s", 50, V)
    b = recurrence.build_condition_batch(cond_s, BS, K, D, 1.0, "s", 50, V)
    assert binding.batch_hash(a) != binding.batch_hash(b)


def test_purity():
    cond = dict(recurrence="paraphrase", rate=0.25, pool_size=16, interval=50, order="scrambled")
    a = recurrence.build_condition_batch(cond, BS, K, D, 0.7, "s", 150, V)
    b = recurrence.build_condition_batch(cond, BS, K, D, 0.7, "s", 150, V)
    assert binding.batch_hash(a) == binding.batch_hash(b)
