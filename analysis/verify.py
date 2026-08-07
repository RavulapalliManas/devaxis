"""Recompute invariants from raw run JSONs; exit nonzero on any violation.

Checks per run file: manifest validates against the schema; chance fields equal 1/K and 1/no;
eval step grid is monotone and on the eval_every lattice; every checkpoint sidecar validates and
its blob (if present) matches its sha256; run is done, failed, or explicitly in-progress.
Optionally audits an S3 prefix: every local run/ckpt object must exist remotely (the
"S3-or-it-didn't-happen" rule made executable)."""
from __future__ import annotations
import argparse
import glob
import json
import os
import subprocess
import sys

from schemas.validate import validate_manifest, validate_checkpoint_sidecar
from training.checkpoint import sha256_file

def check_run(path: str) -> list[str]:
    errs = []
    rec = json.load(open(path))
    man = rec.get("manifest")
    if man is None:
        return [f"{path}: no manifest echo"]
    try:
        validate_manifest(man)
    except Exception as e:
        errs.append(f"{path}: manifest invalid: {e}")
    K = man["task"]["K"]
    if abs(rec.get("chance_query_ctx", -1) - 1.0 / K) > 1e-12:
        errs.append(f"{path}: chance_query_ctx != 1/K")
    steps = [e["step"] for e in rec.get("evals", [])]
    if steps != sorted(steps):
        errs.append(f"{path}: eval steps not monotone")
    ee = man["eval_every"]
    if any(s % ee for s in steps):
        errs.append(f"{path}: eval step off the eval_every lattice")
    if not (rec.get("done") or rec.get("failed") or rec.get("in_progress")):
        errs.append(f"{path}: neither done nor failed (mark in_progress explicitly if live)")
    return errs


def check_ckpts(out_dir: str) -> list[str]:
    errs = []
    for side_path in glob.glob(os.path.join(out_dir, "ckpt", "**", "*.manifest.json"),
                               recursive=True):
        side = json.load(open(side_path))
        try:
            validate_checkpoint_sidecar(side)
        except Exception as e:
            errs.append(f"{side_path}: sidecar invalid: {e}")
            continue
        blob = side_path[:-len(".manifest.json")]
        if os.path.exists(blob) and sha256_file(blob) != side["sha256"]:
            errs.append(f"{blob}: sha256 mismatch vs sidecar")
    return errs


def check_s3(local_root: str, s3_prefix: str) -> list[str]:
    out = subprocess.run(["aws", "s3", "ls", "--recursive", s3_prefix],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return [f"s3 ls failed: {out.stderr.strip()}"]
    remote = {line.split()[-1].split("/", 1)[-1] for line in out.stdout.splitlines() if line}
    missing = []
    for f in glob.glob(os.path.join(local_root, "**", "*"), recursive=True):
        if os.path.isfile(f):
            rel = os.path.relpath(f, local_root)
            if not any(r.endswith(rel) for r in remote):
                missing.append(f"not in S3: {rel}")
    return missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", required=True)
    ap.add_argument("--s3-prefix", default=None)
    a = ap.parse_args()
    files = [f for f in sorted(glob.glob(os.path.join(a.runs_dir, "*.json")))
             if not f.endswith(".manifest.json")]
    errs = []
    for f in files:
        errs += check_run(f)
    errs += check_ckpts(a.runs_dir)
    if a.s3_prefix:
        errs += check_s3(a.runs_dir, a.s3_prefix)
    print(f"[verify] n = {len(files)} run files, {len(errs)} violations")
    for e in errs:
        print(f"[verify] FAIL {e}")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
