"""P1 — relational addressing (K-binding).  Vectorized numpy port of lag_law.build_batch.

Sequence layout (T = 1 + 2K + D + 1 + 2K + 4):

    BOS | e1 o1 ... eK oK | D distractors | RECAP | e1 o1 ... eK oK | ? e_j ANS o_j

READ supply: the 2K recap tokens, supervised on EVERY sequence (constant in p).
USE  supply: the single answer token, supervised with probability p (the only thing p moves).
The input distribution is identical across p — only the loss mask moves.

Latent/surface split (this is what the recurrence factorial keys on):
  * sample_latents(rng)  — the latent program: which (entity, obligation) pairs, which query slot.
  * render_batch(latents, rng) — the surface: distractor draw + loss-mask draw.
  exact duplicate    = same latents + same surface rng  -> byte-identical sequence
  paraphrase         = same latents + fresh surface rng -> same program, new distractors
  structural         = fresh latents                    -> new program, same schema

DRAW ORDER IS THE CONTRACT: ents, obls, j (latents); distractors, mask (surface).  Any change to
the order or shape of draws is a generator version bump.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import numpy as np

GENERATOR_VERSION = "binding-1.0.0"

PAD, BOS, SEP, DOT, RECAP, QMARK, ANS = 0, 1, 2, 3, 4, 5, 6
E0 = 8


@dataclass(frozen=True)
class Vocab:
    ne: int = 64
    no: int = 64
    nd: int = 256

    @property
    def o0(self) -> int:
        return E0 + self.ne

    @property
    def d0(self) -> int:
        return self.o0 + self.no

    @property
    def size(self) -> int:
        return self.d0 + self.nd


def seq_len(K: int, D: int) -> int:
    return 1 + 2 * K + D + 1 + 2 * K + 4


def sample_latents(rng: np.random.Generator, bs: int, K: int, v: Vocab) -> dict:
    """The latent program: K distinct entities bound to K distinct obligations, one queried slot."""
    ents = np.argsort(rng.random((bs, v.ne)), axis=1)[:, :K].astype(np.int64) + E0
    obls = np.argsort(rng.random((bs, v.no)), axis=1)[:, :K].astype(np.int64) + v.o0
    j = rng.integers(0, K, size=bs)
    return dict(ents=ents, obls=obls, j=j)


def render_batch(lat: dict, D: int, p: float, rng: np.random.Generator, v: Vocab,
                 force_loss: bool = False) -> dict:
    """Surface realization of a latent batch.  Targets are next-token aligned (tgt[i] = ids[i+1])."""
    ents, obls, j = lat["ents"], lat["obls"], lat["j"]
    bs, K = ents.shape
    T = seq_len(K, D)
    r = np.arange(bs)

    ids = np.full((bs, T), PAD, dtype=np.int64)
    tgt = np.full((bs, T), -100, dtype=np.int64)

    ids[:, 0] = BOS
    ids[:, 1:1 + 2 * K:2] = ents                      # declaration: unpredictable, no loss
    ids[:, 2:2 + 2 * K:2] = obls
    ids[:, 2 * K + 1:2 * K + 1 + D] = rng.integers(0, v.nd, size=(bs, D)) + v.d0

    rp = 2 * K + D + 1                                # probe site: state here must hold all K pairs
    ids[:, rp] = RECAP
    ids[:, rp + 1:rp + 1 + 2 * K:2] = ents            # recap: same order -> positional maintenance
    ids[:, rp + 2:rp + 2 + 2 * K:2] = obls
    tgt[:, rp:rp + 2 * K:2] = ents                    # predicted from the token before each
    tgt[:, rp + 1:rp + 1 + 2 * K:2] = obls

    q0 = rp + 1 + 2 * K
    gold = obls[r, j]
    ids[:, q0] = QMARK
    ids[:, q0 + 1] = ents[r, j]
    ids[:, q0 + 2] = ANS
    ids[:, q0 + 3] = gold
    mask = np.ones(bs, bool) if force_loss else (rng.random(bs) < p)
    tgt[mask, q0 + 2] = gold[mask]

    return dict(ids=ids, tgt=tgt,
                ans_pos=np.full(bs, q0 + 2, dtype=np.int64),
                slot_lab=obls - v.o0,
                recap_pos=np.full(bs, rp, dtype=np.int64))


def build_batch(bs: int, K: int, D: int, p: float, rng: np.random.Generator, v: Vocab,
                force_loss: bool = False) -> dict:
    return render_batch(sample_latents(rng, bs, K, v), D, p, rng, v, force_loss=force_loss)


def batch_hash(batch: dict) -> str:
    """sha256 over the model-visible bytes — the golden-test and exact-duplicate primitive."""
    h = hashlib.sha256()
    h.update(batch["ids"].tobytes())
    h.update(batch["tgt"].tobytes())
    return h.hexdigest()
