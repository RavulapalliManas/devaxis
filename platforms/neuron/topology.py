"""Wave dispatcher: independent single-core training processes, one NeuronCore per LANE.

queue.jsonl lines: {"manifest": "path.json", "core": 7, "overrides": ["run_id=x", ...]}
Jobs sharing a core form a lane and run SEQUENTIALLY (never concurrently on one core).
Each job runs `python -m training.train --backend neuron` under NEURON_RT_VISIBLE_CORES=<core>.
A crashed job is retried in place up to --max-retries (it resumes from its own run state).
Job state is read from the filesystem (run JSON done/failed flags), never from queue position.
A STOP_NEW file (deadline guard) stops new launches; running jobs finish or get the guard's
SIGTERM."""
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", required=True)
    ap.add_argument("--max-retries", type=int, default=2)
    ap.add_argument("--poll", type=int, default=30)
    a = ap.parse_args()

    jobs = [json.loads(l) for l in open(a.queue) if l.strip()]
    lanes: dict[int, list[int]] = {}
    for i, j in enumerate(jobs):
        lanes.setdefault(j["core"], []).append(i)

    os.makedirs("logs", exist_ok=True)
    retries = {i: 0 for i in range(len(jobs))}
    active: dict[int, tuple[int, subprocess.Popen]] = {}

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
        print(f"[topology] core {core}: launched job {i} (pid {p.pid})", flush=True)

    for core in sorted(lanes):
        if os.path.exists("STOP_NEW"):
            print("[topology] STOP_NEW present — launching nothing", flush=True)
            return
        i = next_pending(core)
        if i is not None:
            launch(core, i)

    while active:
        time.sleep(a.poll)
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
                launch(core, i)
                continue
            else:
                print(f"[topology] core {core}: job {i} FAILED permanently", flush=True)
                lanes[core].pop(0)
            if not os.path.exists("STOP_NEW"):
                nxt = next_pending(core)
                if nxt is not None:
                    launch(core, nxt)
    print("[topology] all lanes drained", flush=True)


if __name__ == "__main__":
    main()
