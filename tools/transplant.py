"""Checkpoint chimera tool: swap layer groups between a plastic and a foreclosed checkpoint.

Layer groups over the GPT's parameter names (training/model.py):
    emb  = tok., pos.        b0..b5 = blocks.N.        out = lnf., head.

The chimera's optimizer state is EMPTY (fresh AdamW, lazy-init on first step) in EVERY arm,
including the no-swap control.  This dodges the per-layer moment-mapping problem, and the
control absorbs the known effect of a fresh optimizer: the mech experiment measured optimizer
reset alone at 0/7 rescues, so fresh moments are a certified near-null co-intervention.
step / lr / nparam / manifest_hash / rng are copied from the recipient, so checkpoint.load's
sha256, nparam, and lr assertions all pass on the merged file.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import torch

GROUPS = {
    "emb": ("tok.", "pos."),
    "b0": ("blocks.0.",), "b1": ("blocks.1.",), "b2": ("blocks.2.",),
    "b3": ("blocks.3.",), "b4": ("blocks.4.",), "b5": ("blocks.5.",),
    "out": ("lnf.", "head."),
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def make_chimera(recipient_path: str, donor_path: str, swap_groups: list[str],
                 out_path: str) -> dict:
    rec = torch.load(recipient_path, map_location="cpu", weights_only=False)
    prefixes = tuple(p for g in swap_groups for p in GROUPS[g])
    n_swapped = 0
    if prefixes:
        don = torch.load(donor_path, map_location="cpu", weights_only=False)
        assert don["nparam"] == rec["nparam"], "architecture mismatch"
        for k in rec["model"]:
            if k.startswith(prefixes):
                rec["model"][k] = don["model"][k]
                n_swapped += 1
        assert n_swapped > 0, f"no params matched {swap_groups}"
    # fresh optimizer in every arm (control absorbs this; optreset alone is a measured ~null)
    rec["opt"] = {"state": {}, "param_groups": rec["opt"]["param_groups"]}
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    torch.save(rec, out_path)
    side = dict(path=os.path.basename(out_path), step=rec["step"],
                sha256=sha256_file(out_path), nparam=rec["nparam"], lr=rec["lr"],
                manifest_hash=rec["manifest_hash"], swapped_groups=swap_groups,
                n_tensors_swapped=n_swapped, donor=os.path.basename(donor_path),
                recipient=os.path.basename(recipient_path))
    with open(out_path + ".manifest.json", "w") as f:
        json.dump(side, f, indent=1)
    return side


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recipient", required=True)
    ap.add_argument("--donor", required=True)
    ap.add_argument("--swap", default="", help="comma list of groups, empty = noop control")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    groups = [g for g in a.swap.split(",") if g]
    side = make_chimera(a.recipient, a.donor, groups, a.out)
    print(json.dumps(side, indent=1))


if __name__ == "__main__":
    main()
