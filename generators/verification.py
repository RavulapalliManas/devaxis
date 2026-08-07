"""P3 — verification / error localization.  NOT IMPLEMENTED IN THIS SLICE (no prior generator
exists anywhere in the tree — this one is greenfield when scheduled).

Spec:
  * A trajectory over the P2 state machine containing valid and (optionally) invalid transitions.
  * Required outputs: validity bit; first invalid step index; violated rule id.
  * Difficulty controls: error position, local-vs-compositional error, plausible-invalid
    distractors, hidden applicability conditions.
  * Loss-mask-only discipline (input distribution identical across supervision conditions),
    modeled on binding.py.
  * Validate with planted mechanisms (master-plan AX7) BEFORE any real-model use: a generator
    whose planted first-error labels a sensor cannot recover is not a sensor failure you can
    interpret later.
"""
from __future__ import annotations


def sample_latents(*a, **k):
    raise NotImplementedError("P3 (verification) is stubbed in the Trainium slice; see docstring")
