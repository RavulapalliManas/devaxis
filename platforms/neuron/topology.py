"""Wave dispatcher: a FIFO of jobs packed dynamically onto free NeuronCores.

queue.jsonl lines: {"manifest": "path.json", "core": 7, "overrides": [...]}.  The "core" field
is a legacy hint and is IGNORED: jobs are launched in queue order onto whichever core in
--cores is free, unheld, and unlocked.  This replaced static lanes on 2026-08-09 — static
build-time core assignment left cores idle whenever a lane's core was held by another wave,
and raced when two builders computed the same free list seconds apart (8 jobs died at init).

Collision safety, two layers:
  * flock on locks/core<N>.lock, held for the child's lifetime — arbitrates between LIVE
    dispatchers racing for a core in the same second;
  * a foreign-holder scan of /proc (trainers outside this dispatcher) — covers processes whose
    dispatcher died and released its locks.

A crashed job is retried (any core) up to --max-retries, resuming from its own run state.
Job state is read from the filesystem (run JSON done flag), never from queue position.
A STOP_NEW file (deadline guard) stops new launches; running jobs finish or get the guard's
SIGTERM."""
from __future__ import annotations
import argparse
import fcntl
import json
import os
import subprocess
import sys
import time


def run_paths(man_path: str, overrides: list[str]) -> str:
    man = json.load(open(man_path))
    run_id, out_dir = man["run_id"], man["out_dir"]
    for kv in overrides:
        k, val = kv.split("=", 1)
        if k == "run_id":
            run_id = val
        if k == "out_dir":
            out_dir = val
    return os.path.join(out_dir, f"{run_id}.json")


def job_state(man_path: str, overrides: list[str]) -> str:
    p = run_paths(man_path, overrides)
    if not os.path.exists(p):
        return "pending"
    try:
        rec = json.load(open(p))
    except Exception:
        return "partial"          # mid-write; treat as in progress
    if rec.get("done"):
        return "done"
    if rec.get("failed"):
        return "failed"
    return "partial"


def foreign_scan(own_pids: set[int]) -> tuple[set[int], set[str]]:
    """(cores held, manifest paths being trained) by trainers OUTSIDE this dispatcher.
    The manifest set prevents the two-writer hazard: after a dispatcher dies and is revived,
    its orphaned trainers keep running — the revived dispatcher must never relaunch a job
    whose manifest a live foreign trainer is already working on."""
    held, manifests = set(), set()
    out = subprocess.run(["pgrep", "-f", "training[.]train"],
                         capture_output=True, text=True).stdout.split()
    for pid in out:
        try:
            if int(pid) in own_pids:
                continue
            env = open(f"/proc/{pid}/environ", "rb").read().decode(errors="ignore").split("\0")
            for x in env:
                if x.startswith("NEURON_RT_VISIBLE_CORES="):
                    held.add(int(x.split("=", 1)[1]))
            cmd = open(f"/proc/{pid}/cmdline", "rb").read().decode(errors="ignore").split("\0")
            for k, tok in enumerate(cmd):
                if tok == "--manifest" and k + 1 < len(cmd):
                    manifests.add(os.path.abspath(cmd[k + 1]))
        except Exception:
            continue
    return held, manifests


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", required=True)
    ap.add_argument("--cores", default="0-31")
    ap.add_argument("--max-retries", type=int, default=2)
    ap.add_argument("--poll", type=int, default=30)
    ap.add_argument("--stagger", type=float, default=8.0,
                    help="seconds between launches; prevents the compile storm that SIGHUP'd "
                         "neuronx-cc when 32 processes compiled simultaneously")
    a = ap.parse_args()

    lo, hi = (int(x) for x in a.cores.split("-"))
    pool = list(range(lo, hi + 1))
    jobs = [json.loads(l) for l in open(a.queue) if l.strip()]

    os.makedirs("logs", exist_ok=True)
    os.makedirs("locks", exist_ok=True)
    retries = {i: 0 for i in range(len(jobs))}
    perm_failed: set[int] = set()
    # core -> (job_idx, proc, lock_fd)
    active: dict[int, tuple[int, subprocess.Popen, int]] = {}

    def pend(foreign_manifests: set[str]) -> list[int]:
        busy = {i for i, _, _ in active.values()}
        out = []
        for i, j in enumerate(jobs):
            if i in busy or i in perm_failed:
                continue
            if os.path.abspath(j["manifest"]) in foreign_manifests:
                continue          # a live foreign trainer already owns this job
            if job_state(j["manifest"], j.get("overrides", [])) == "done":
                continue
            out.append(i)
        return out

    def try_lock(core: int) -> int | None:
        fd = os.open(os.path.join("locks", f"core{core}.lock"), os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except OSError:
            os.close(fd)
            return None

    def launch(core: int, i: int, fd: int):
        j = jobs[i]
        env = dict(os.environ, NEURON_RT_VISIBLE_CORES=str(core))
        cmd = [sys.executable, "-m", "training.train", "--manifest", j["manifest"],
               "--backend", "neuron"]
        for kv in j.get("overrides", []):
            cmd += ["--set", kv]
        log = open(f"logs/job{i}_core{core}.log", "a")
        p = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
        active[core] = (i, p, fd)
        print(f"[topology] core {core}: launched job {i} (pid {p.pid})", flush=True)

    while True:
        own = {p.pid for _, p, _ in active.values()}
        held, foreign_man = foreign_scan(own)
        if not os.path.exists("STOP_NEW"):
            waiting = pend(foreign_man)
            for core in pool:
                if not waiting:
                    break
                if core in active or core in held:
                    continue
                fd = try_lock(core)
                if fd is None:
                    continue
                launch(core, waiting.pop(0), fd)
                time.sleep(a.stagger)

        if not active:
            if os.path.exists("STOP_NEW"):
                print("[topology] STOP_NEW and nothing active — exiting", flush=True)
                return
            if not pend(foreign_man):
                break
        time.sleep(a.poll)

        for core in list(active):
            i, p, fd = active[core]
            if p.poll() is None:
                continue
            del active[core]
            os.close(fd)          # releases the flock
            if p.returncode == 0:
                print(f"[topology] core {core}: job {i} DONE", flush=True)
            elif retries[i] < a.max_retries and not os.path.exists("STOP_NEW"):
                retries[i] += 1
                print(f"[topology] core {core}: job {i} crashed rc={p.returncode}, "
                      f"retry {retries[i]} (any core)", flush=True)
            else:
                print(f"[topology] core {core}: job {i} FAILED permanently", flush=True)
                perm_failed.add(i)
    print("[topology] all jobs drained", flush=True)


if __name__ == "__main__":
    main()
