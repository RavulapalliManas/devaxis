"""Preflight gate — the box is unusable for science until every check passes with an asserted
VALUE, not just a zero exit code (the H100 playbook's all-reduce-value discipline).

    python preflight.py                 # single-process checks (devices, matmul, disk, S3, hours)
    torchrun --nproc_per_node=32 preflight.py --allreduce   # collective value check

Writes gates/q0_preflight.json.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys

S3 = "s3://pythia-fork-experiments-434457397267/devaxis"
END_UTC = os.environ.get("END_UTC", "2026-08-23T11:30:00Z")
EXPECT_DEVICES = 16
EXPECT_CORES = 32


def check_devices(res):
    out = subprocess.run(["neuron-ls", "--json-output"], capture_output=True, text=True)
    devs = json.loads(out.stdout)
    n = len(devs)
    cores = sum(d.get("nc_count", d.get("neuroncore_count", 0)) for d in devs)
    res["devices"] = dict(found=n, cores=cores, ok=(n == EXPECT_DEVICES and cores == EXPECT_CORES))
    assert res["devices"]["ok"], f"expected {EXPECT_DEVICES} devices/{EXPECT_CORES} cores, got {n}/{cores}"


def check_matmul(res):
    """One small bf16 matmul on ONE core with a value assertion (identity @ ones == ones)."""
    import torch
    import torch_xla.core.xla_model as xm
    dev = xm.xla_device()
    a = torch.eye(64, dtype=torch.bfloat16, device=dev)
    b = torch.ones(64, 64, dtype=torch.bfloat16, device=dev)
    c = (a @ b).cpu()
    ok = bool(torch.all(c == 1.0))
    res["matmul"] = dict(ok=ok)
    assert ok, "identity matmul returned wrong VALUES"


def check_disk(res):
    free = shutil.disk_usage(os.path.expanduser("~")).free / 1e9
    res["disk"] = dict(free_gb=round(free, 1), ok=free > 50)
    assert free > 50, f"only {free:.0f} GB free"


def check_s3(res):
    """Write-then-read-back canary — S3 access is asserted by round-trip, not by ls."""
    canary = f"preflight {dt.datetime.utcnow().isoformat()}"
    p = subprocess.run(["aws", "s3", "cp", "-", f"{S3}/.preflight_probe"],
                       input=canary, capture_output=True, text=True)
    assert p.returncode == 0, f"S3 write failed: {p.stderr}"
    q = subprocess.run(["aws", "s3", "cp", f"{S3}/.preflight_probe", "-"],
                       capture_output=True, text=True)
    assert q.stdout == canary, "S3 read-back mismatch"
    res["s3"] = dict(ok=True)


def check_hours(res):
    end = dt.datetime.fromisoformat(END_UTC.replace("Z", "+00:00"))
    left = (end - dt.datetime.now(dt.timezone.utc)).total_seconds() / 3600
    res["hours_left"] = round(left, 1)
    assert left > 1, "block expired or about to"


def allreduce_main():
    import torch
    import torch.distributed as dist
    import torch_xla.core.xla_model as xm
    import torch_xla.distributed.xla_backend  # noqa: F401
    dist.init_process_group("xla")
    rank = dist.get_rank()
    world = dist.get_world_size()
    t = torch.tensor([float(rank)], device=xm.xla_device())
    dist.all_reduce(t)
    xm.mark_step()
    got = float(t.cpu())
    expect = world * (world - 1) / 2                 # sum(0..31) == 496 at world=32
    assert got == expect, f"rank {rank}: all_reduce sum {got} != {expect}"
    if rank == 0:
        print(f"ALLREDUCE OK world={world} sum={got}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allreduce", action="store_true")
    a = ap.parse_args()
    if a.allreduce:
        allreduce_main()
        return
    res = {"end_utc": END_UTC}
    for fn in (check_devices, check_matmul, check_disk, check_s3, check_hours):
        fn(res)
        print(f"[preflight] {fn.__name__} OK {res}", flush=True)
    os.makedirs("gates", exist_ok=True)
    res["pass"] = True
    with open("gates/q0_preflight.json", "w") as f:
        json.dump(res, f, indent=1)
    print("[preflight] PASS -> gates/q0_preflight.json")


if __name__ == "__main__":
    sys.exit(main())
