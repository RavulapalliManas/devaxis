"""CLI entry.  The manifest is the only input; argv beyond these flags is forbidden.

    python -m training.train --manifest configs/x.json --backend cpu [--mutate NAME] \
        [--set key=value ...]

--set applies dotted-path overrides (e.g. --set run_id=q4_s3 --set init_seed=3) so a sweep is one
manifest plus per-run overrides recorded verbatim in the output — no hand-edited copies.
"""
from __future__ import annotations
import argparse
import json

from schemas.validate import validate_manifest
from training import engine


def apply_set(man: dict, kv: str) -> None:
    k, val = kv.split("=", 1)
    try:
        val = json.loads(val)
    except json.JSONDecodeError:
        pass
    node = man
    parts = k.split(".")
    for p in parts[:-1]:
        node = node[p]
    node[parts[-1]] = val


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--backend", required=True, choices=["cpu", "cuda", "neuron"])
    ap.add_argument("--mutate", default=None,
                    choices=[None, "random_labels", "constant_loss", "detached_head",
                             "wrong_eval_position"])
    ap.add_argument("--set", action="append", default=[], dest="overrides")
    a = ap.parse_args()

    man = json.load(open(a.manifest))
    for kv in a.overrides:
        apply_set(man, kv)
    man["overrides"] = a.overrides
    validate_manifest(man)
    engine.run(man, a.backend, mutate=a.mutate)


if __name__ == "__main__":
    main()
