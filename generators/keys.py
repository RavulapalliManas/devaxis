"""The purity primitive.

Every batch in devaxis is a pure function of (stream_id, stream, step).  There is no data-loader
cursor, no shuffle state, no replay buffer: the "cursor" IS the step number.  A branch that replays
its parent's stream_id reproduces the parent's bytes exactly; an intervention that switches
stream_id at fork_step changes the data and nothing else.

numpy Philox is counter-based and platform-stable (same bytes on macOS/Linux/x86/ARM), which is what
makes golden hashes meaningful across machines.
"""
from __future__ import annotations
import hashlib
import numpy as np

# All runs share this eval stream so eval data is identical across every run (the lag_law
# fixed-eval-generator discipline, seeds 999983/4242, carried over).
EVAL_STREAM_ID = "__eval__"


def key(stream_id: str, stream: str, step: int) -> np.random.Generator:
    """Derive an independent, reproducible RNG for one (stream_id, stream, step) cell."""
    h = hashlib.sha256(f"{stream_id}\x1f{stream}\x1f{step}".encode()).digest()
    return np.random.Generator(np.random.Philox(key=int.from_bytes(h[:16], "little")))


def eval_key(step_or_index: int) -> np.random.Generator:
    return key(EVAL_STREAM_ID, "eval", step_or_index)
