"""Wave dispatcher: independent single-core training processes, one NeuronCore per LANE.

queue.jsonl lines: {"manifest": "path.json", "core": 7, "overrides": ["run_id=x", ...]}
Jobs sharing a core form a lane and run SEQUENTIALLY (never concurrently on one core).
Each job runs `python -m training.train --backend neuron` under NEURON_RT_VISIBLE_CORES=<core>.
A crashed job is retried in place up to --max-retries (it resumes from its own run state).
Job state is read from the filesystem (run JSON done/failed flags), never from queue position.
A STOP_NEW file (deadline guard) stops new launches; running jobs finish or get the guard's
SIGTERM.

LAUNCH-TIME CORE GUARD (2026-08-09): a core held by a FOREIGN trainer (another wave's process)
is not launched onto — the lane waits and retries each poll.  Build-time free-core checks are
not enough: two builders run seconds apart see the same free list and assign overlapping lanes,
and the collision losers die at device init leaving no run record (8 jobs lost this way when
devaxis-tomo and devaxis-k2post10k launched together)."""
from __future__ import annotations
import argparse
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
    rec = json.load(open(p))
    if rec.get("done"):
        return "done"
    if rec.get("failed"):
        return "failed"
    return "partial"


def foreign_holder(core: int, own_pids: set[int]) -> bool:
    """True if a trainer OUTSIDE this dispatcher currently holds the core."""
    out = subprocess.run(["pgrep", "-f", "training[.]train"],
                         capture_output=True, text=True).stdout.split()
    for pid in out:
        try:
            if int(pid) in own_pids:
                continue
            env = open(f"/proc/{pid}/environ", "rb").read().decode(errors="ignore").split("\0")
            for x in env:
                if x.startswith("NEURON_RT_VISIBLE_CORES=") and int(x.split("=", 1)[1]) == core:
                    return True
        except Exception:
            continue
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", required=True)
    ap.add_argument("--max-retries", type=int, default=2)
    ap.add_argument("--poll", type=int, default=30)
    ap.add_argument("--stagger", type=float, default=8.0,
                    help="seconds between lane starts; prevents the compile storm that "
                         "SIGHUP'd neuronx-cc when 32 processes compiled simultaneously")
    a = ap.parse_args()

    jobs = [json.loads(l) for l in open(a.queue) if l.strip()]
    lanes: dict[int, list[int]] = {}
    for i, j in enumerate(jobs):
        lanes.setdefault(j["core"], []).append(i)

    os.makedirs("logs", exist_ok=True)
    retries = {i: 0 for i in range(len(jobs))}
    active: dict[int, tuple[int, subprocess.Popen]] = {}
    waiting_note: set[int] = set()

    def next_pending(core) -> int | None:
        while lanes[core]:
            i = lanes[core][0]
            if job_state(jobs[i]["manifest"], jobs[i].get("overrides", [])) == "done":
                print(f"[topology] job {i} already done, skipping", flush=True)
                lanes[core].pop(0)
                continue
            return i
        return None

    def launch(core, i):
        j = jobs[i]
        env = dict(os.environ, NEURON_RT_VISIBLE_CORES=str(core))
        cmd = [sys.executable, "-m", "training.train", "--manifest", j["manifest"],
               "--backend", "neuron"]
        for kv in j.get("overrides", []):
            cmd += ["--set", kv]
        log = open(f"logs/job{i}_core{core}.log", "a")
        p = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
        active[core] = (i, p)
        waiting_note.discard(core)
        print(f"[topology] core {core}: launched job {i} (pid {p.pid})", flush=True)

    while True:
        # launch pass: any lane with work, no active process, and an unheld core
        if not os.path.exists("STOP_NEW"):
            own = {p.pid for _, p in active.values()}
            for core in sorted(lanes):
                if core in active:
                    continue
                i = next_pending(core)
                if i is None:
                    continue
                if foreign_holder(core, own):
                    if core not in waiting_note:
                        print(f"[topology] core {core}: held by a foreign trainer — waiting",
                              flush=True)
                        waiting_note.add(core)
                    continue
                launch(core, i)
                time.sleep(a.stagger)

        if not active:
            if os.path.exists("STOP_NEW"):
                print("[topology] STOP_NEW and nothing active — exiting", flush=True)
                return
            if all(next_pending(c) is None for c in lanes):
                break
        time.sleep(a.poll)

        # reap pass
        for core in list(active):
            i, p = active[core]
            if p.poll() is None:
                continue
            del active[core]
            if p.returncode == 0:
                print(f"[topology] core {core}: job {i} DONE", flush=True)
                lanes[core].pop(0)
            elif retries[i] < a.max_retries and not os.path.exists("STOP_NEW"):
                retries[i] += 1
                print(f"[topology] core {core}: job {i} crashed rc={p.returncode}, "
                      f"retry {retries[i]}", flush=True)
            else:
                print(f"[topology] core {core}: job {i} FAILED permanently", flush=True)
                lanes[core].pop(0)
    print("[topology] all lanes drained", flush=True)


if __name__ == "__main__":
    main()
