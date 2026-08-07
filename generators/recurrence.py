"""DD condition layer: recurrence x spacing x order over the P1 binding generator.

A condition is a dict:
    recurrence: "none" | "exact" | "paraphrase"
    rate:       fraction of each RECURRENCE-STEP batch drawn from the pool (0 < rate <= 1)
    pool_size:  number of latent programs in the recurrence pool
    interval:   steps between pool visits (spacing: short=small, long=large)
    order:      "fixed" (cyclic through the pool) | "scrambled" (keyed random pick)

Semantics (all pure functions of (stream_id, step) — branches replay bytes exactly):
  * Pool item i has latents  = sample_latents(key(stream_id, "pool", i)).
  * At step t with t % interval == 0, the first round(bs*rate) rows of the batch are pool
    rows (visit index vi = t // interval); all other rows, and all rows of non-recurrence
    steps, are ordinary fresh rows from the "train" stream.
  * exact:      pool row surface key = key(stream_id, "poolsurf", i)            — byte-identical
                rendering on every visit (same distractors, same query slot).
  * paraphrase: pool row surface key = key(stream_id, "poolsurf", i*1000003+vi) — same latent
                program (same entity-obligation pairs), fresh distractors/query each visit.
  * order fixed:     slot r of visit vi takes pool item (vi*m + r) % pool_size — cyclic sweep.
    order scrambled: items drawn without replacement by key(stream_id, "order", t).

The intended_difference between any two conditions is exactly one field of the dict; the data
manifest records it (difference-certificate discipline).
"""
from __future__ import annotations
import numpy as np

from generators import binding, keys
from generators.binding import Vocab

CONDITION_VERSION = "recurrence-1.0.0"


def _pool_latents(stream_id: str, idx: np.ndarray, K: int, v: Vocab) -> dict:
    """Latents for the given pool item indices (one keyed draw per item, stacked)."""
    parts = [binding.sample_latents(keys.key(stream_id, "pool", int(i)), 1, K, v) for i in idx]
    return dict(ents=np.concatenate([p["ents"] for p in parts]),
                obls=np.concatenate([p["obls"] for p in parts]),
                j=np.concatenate([p["j"] for p in parts]))


def build_condition_batch(cond: dict, bs: int, K: int, D: int, p: float,
                          stream_id: str, step: int, v: Vocab) -> dict:
    fresh = binding.build_batch(bs, K, D, p, keys.key(stream_id, "train", step), v)
    rec = cond.get("recurrence", "none")
    interval = cond.get("interval", 1)
    if rec == "none" or step % interval != 0:
        return fresh

    m = int(round(bs * cond["rate"]))
    if m == 0:
        return fresh
    P = cond["pool_size"]
    vi = step // interval

    if cond.get("order", "fixed") == "fixed":
        idx = (vi * m + np.arange(m)) % P
    else:
        rng = keys.key(stream_id, "order", step)
        idx = rng.permutation(P)[:m] if m <= P else rng.integers(0, P, m)

    lat = _pool_latents(stream_id, idx, K, v)
    rows = []
    for r in range(m):
        i = int(idx[r])
        skey = i if rec == "exact" else i * 1000003 + vi
        one = binding.render_batch(
            dict(ents=lat["ents"][r:r + 1], obls=lat["obls"][r:r + 1], j=lat["j"][r:r + 1]),
            D, p, keys.key(stream_id, "poolsurf", skey), v)
        rows.append(one)

    for field in ("ids", "tgt", "ans_pos", "slot_lab", "recap_pos"):
        fresh[field][:m] = np.concatenate([one[field] for one in rows])
    return fresh
