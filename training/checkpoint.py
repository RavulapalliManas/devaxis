"""Checkpoints = the branch points of the science.  A checkpoint is a blob + a sidecar manifest
with the blob's sha256; a checkpoint without its sidecar does not exist for confirmation purposes.

Contract (earned, not assumed — the model has no dropout and data is a pure function of step, so
the ENTIRE mutable state of a run is params + optimizer moments + step; see generators/keys.py):
  * saved:   model.state_dict(), opt.state_dict(), step, lr(step), nparam, manifest_hash,
             RNG states (defensive only — nothing reads them; documented inert).
  * restore: load params+moments, set lr(step) via the pure schedule, ASSERT it matches the
             recorded value (the critical_period bug class dies here), return step.
Saves must happen only immediately after backend.sync() (engine's responsibility) so no live XLA
lazy handle is ever serialized.
"""
from __future__ import annotations
import hashlib
import json
import os
import numpy as np
import torch

from training.optim import lr_at, set_lr
from training.model import nparam as count_params


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def save(path: str, model, opt, step: int, base_lr: float, warmup: int,
         manifest_hash: str, backend) -> dict:
    payload = dict(
        model=model.state_dict(), opt=opt.state_dict(), step=step,
        lr=lr_at(step, base_lr, warmup), nparam=count_params(model),
        manifest_hash=manifest_hash,
        rng_inert=dict(torch=torch.get_rng_state(), numpy=np.random.get_state()),
    )
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    backend.save(payload, path)
    side = dict(path=os.path.basename(path), step=step, sha256=sha256_file(path),
                nparam=payload["nparam"], lr=payload["lr"], manifest_hash=manifest_hash)
    with open(path + ".manifest.json", "w") as f:
        json.dump(side, f, indent=1)
    return side


def load(path: str, model, opt, base_lr: float, warmup: int) -> int:
    side_path = path + ".manifest.json"
    if os.path.exists(side_path):
        side = json.load(open(side_path))
        actual = sha256_file(path)
        assert actual == side["sha256"], f"checkpoint corrupted: {path}"
    ck = torch.load(path, map_location="cpu", weights_only=False)
    assert ck["nparam"] == count_params(model), "checkpoint/model mismatch"
    model.load_state_dict(ck["model"])
    if opt is not None:
        opt.load_state_dict(ck["opt"])
        step = ck["step"]
        set_lr(opt, lr_at(step, base_lr, warmup))
        assert abs(opt.param_groups[0]["lr"] - ck["lr"]) < 1e-12, \
            f"resume LR {opt.param_groups[0]['lr']} != recorded {ck['lr']}"
    return ck["step"]
