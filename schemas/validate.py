"""Writer-side schema validation.  Every writer of a manifest/certificate calls the matching
function before writing; a run whose manifest does not validate is invalid for confirmation
(master-plan T0 rule)."""
from __future__ import annotations
import json
import os
import jsonschema

_DIR = os.path.dirname(os.path.abspath(__file__))
_CACHE: dict = {}


def _schema(name: str) -> dict:
    if name not in _CACHE:
        _CACHE[name] = json.load(open(os.path.join(_DIR, f"{name}.schema.json")))
    return _CACHE[name]


def validate_manifest(man: dict) -> None:
    jsonschema.validate(man, _schema("run_manifest"))


def validate_checkpoint_sidecar(side: dict) -> None:
    jsonschema.validate(side, _schema("checkpoint_manifest"))


def validate_data_manifest(dm: dict) -> None:
    jsonschema.validate(dm, _schema("data_manifest"))


def validate_certificate(cert: dict) -> None:
    jsonschema.validate(cert, _schema("difference_certificate"))
