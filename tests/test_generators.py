"""Generator purity + structure + golden hashes.

Goldens (tests/goldens.json) are generated ON cpu-angad and committed; numpy Philox is
platform-stable, so a mismatch anywhere means the generator changed, not the machine.
Regenerate deliberately with:  python -m tests.regen_goldens  (and bump GENERATOR_VERSION).
"""
import json
import os

import numpy as np
import pytest

from generators import binding, keys
from generators.binding import Vocab, seq_len, PAD, BOS, RECAP, QMARK, ANS

GOLDENS = os.path.join(os.path.dirname(__file__), "goldens.json")
V = Vocab()


def test_same_key_same_bytes():
    a = binding.build_batch(16, 4, 32, 0.7, keys.key("r1", "train", 5), V)
    b = binding.build_batch(16, 4, 32, 0.7, keys.key("r1", "train", 5), V)
    assert binding.batch_hash(a) == binding.batch_hash(b)


def test_different_step_different_bytes():
    a = binding.build_batch(16, 4, 32, 0.7, keys.key("r1", "train", 5), V)
    b = binding.build_batch(16, 4, 32, 0.7, keys.key("r1", "train", 6), V)
    assert binding.batch_hash(a) != binding.batch_hash(b)


def test_different_stream_different_bytes():
    a = binding.build_batch(16, 4, 32, 0.7, keys.key("r1", "train", 5), V)
    b = binding.build_batch(16, 4, 32, 0.7, keys.key("r2", "train", 5), V)
    assert binding.batch_hash(a) != binding.batch_hash(b)


def test_structure():
    K, D, bs = 4, 32, 8
    b = binding.build_batch(bs, K, D, 1.0, keys.key("s", "train", 0), V, force_loss=True)
    ids, tgt = b["ids"], b["tgt"]
    T = seq_len(K, D)
    assert ids.shape == (bs, T) and tgt.shape == (bs, T)
    assert (ids[:, 0] == BOS).all()
    rp = 2 * K + D + 1
    assert (ids[:, rp] == RECAP).all()
    assert (b["recap_pos"] == rp).all()
    q0 = rp + 1 + 2 * K
    assert (ids[:, q0] == QMARK).all() and (ids[:, q0 + 2] == ANS).all()
    assert (b["ans_pos"] == q0 + 2).all()
    # declaration and recap blocks agree token-for-token
    assert (ids[:, 1:1 + 2 * K] == ids[:, rp + 1:rp + 1 + 2 * K]).all()
    # recap targets are next-token aligned with the recap block
    assert (tgt[:, rp:rp + 2 * K] == ids[:, rp + 1:rp + 1 + 2 * K]).all()
    # the answer token is the queried entity's obligation, and it is in the declared set
    r = np.arange(bs)
    gold = tgt[r, b["ans_pos"][0]]
    assert (gold >= 0).all()
    obls = ids[:, 2:2 * K + 1:2]
    assert ((obls == gold[:, None]).any(axis=1)).all()
    assert (ids[r, b["ans_pos"][0] + 1] == gold).all()
    # no PAD anywhere in a rendered sequence
    assert (ids != PAD).all()


def test_loss_mask_probability():
    rng = keys.key("mask", "train", 0)
    b = binding.build_batch(4096, 2, 4, 0.5, rng, V)
    r = np.arange(4096)
    frac = float((b["tgt"][r, b["ans_pos"][0]] >= 0).mean())
    assert 0.45 < frac < 0.55
    b0 = binding.build_batch(256, 2, 4, 0.0, keys.key("mask", "train", 1), V)
    assert (b0["tgt"][np.arange(256), b0["ans_pos"][0]] == -100).all()


def test_latent_surface_split():
    """exact = same latents+surface key; paraphrase = same latents, new surface;
    structural = new latents."""
    lat = binding.sample_latents(keys.key("lat", "latents", 0), 8, 4, V)
    a = binding.render_batch(lat, 32, 1.0, keys.key("surf", "s", 0), V)
    a2 = binding.render_batch(lat, 32, 1.0, keys.key("surf", "s", 0), V)
    para = binding.render_batch(lat, 32, 1.0, keys.key("surf", "s", 1), V)
    assert binding.batch_hash(a) == binding.batch_hash(a2)          # exact duplicate
    assert binding.batch_hash(a) != binding.batch_hash(para)        # paraphrase differs
    K = 4
    assert (a["ids"][:, 1:1 + 2 * K] == para["ids"][:, 1:1 + 2 * K]).all()  # same program


def test_goldens():
    cases = {
        "K4_D32_p1.0": binding.batch_hash(
            binding.build_batch(64, 4, 32, 1.0, keys.key("golden", "train", 0), V)),
        "K2_D8_p0.5": binding.batch_hash(
            binding.build_batch(64, 2, 8, 0.5, keys.key("golden", "train", 1), V)),
        "eval_batch0": binding.batch_hash(
            binding.build_batch(128, 4, 32, 1.0, keys.eval_key(0), V, force_loss=True)),
    }
    if not os.path.exists(GOLDENS):
        pytest.skip("goldens.json not yet generated (run python -m tests.regen_goldens)")
    gold = json.load(open(GOLDENS))["generators"]
    assert cases == gold, "generator bytes changed — version bump + deliberate regen required"
