"""P2 — dynamic state update (boxes world).  NOT IMPLEMENTED IN THIS SLICE.

Spec (port when a DD/AX experiment schedules P2):
  * Reuse the deterministic state machine of flagship-04 `boxes_binding.py::simulate()`
    (move/remove/put ops over n boxes -> exact final box->object map), but re-emit as
    fixed-length sequences over a closed synthetic vocab (box tokens, object tokens, op tokens),
    NOT English text.  Fixed T per (n_boxes, n_ops) config — one XLA shape bucket.
  * Same latent/surface split as binding.py: latents = (initial assignment, op sequence, queried
    box); surface = distractor interleaving + loss mask.
  * Privileged record must carry the full state trajectory (state_sequence) per the master-plan
    dataset contract, so verification tasks can later plant first-error labels.
"""
from __future__ import annotations


def sample_latents(*a, **k):
    raise NotImplementedError("P2 (state) is stubbed in the Trainium slice; see module docstring")


def render_batch(*a, **k):
    raise NotImplementedError("P2 (state) is stubbed in the Trainium slice; see module docstring")
