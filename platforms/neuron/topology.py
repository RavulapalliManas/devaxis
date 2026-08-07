"""Wave dispatcher: N independent single-core training processes, one NeuronCore each.

queue.jsonl lines: {"manifest": "path.json", "core": 7, "overrides": ["run_id=x", ...]}
Each job runs `python -m training.train --manifest ... --backend neuron` with
NEURON_RT_VISIBLE_CORES=<core>.  A core is never reassigned mid-run; a crashed job is restarted
in place up to --max-retries; state is read from the filesystem (run JSON done/failed flags),
never from queue position (H100-playbook rule: count n from files)."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time


def job_state(man_path: str, overrides: list[str]) -> str:
    man = json.load(open(man_path))
    run_id = man["run_id"]
    out_dir = man["out_dir"]
    for kv in overrides:
        k, v = kv.split("=", 1)
        if k == "run_id":
            run_id = v
        if k == "out_dir":
            out_dir = v
    p = os.path.join(out_dir, f"{run_id}.json")
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
    cores = [j["core"] for j in jobs]
    assert len(cores) == len(set(cores)), "one core per job — duplicate core in queue"

    procs: dict[int, subprocess.Popen] = {}
    retries = {i: 0 for i in range(len(jobs))}
    live = set(range(len(jobs)))

    for i in sorted(live):
        j = jobs[i]
        if job_state(j["manifest"], j.get("overrides", [])) == "done":
            print(f"[topology] job {i} already done, skipping", flush=True)
            live.discard(i)

    def launch(i):
        j = jobs[i]
        env = dict(os.environ, NEURON_RT_VISIBLE_CORES=str(j["core"]))
        cmd = [sys.executable, "-m", "training.train", "--manifest", j["manifest"],
               "--backend", "neuron"]
        for kv in j.get("overrides", []):
            cmd += ["--set", kv]
        log = open(f"logs/job{i}_core{j['core']}.log", "a")
        procs[i] = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
        print(f"[topology] launched job {i} on core {j['core']} pid {procs[i].pid}", flush=True)

    os.makedirs("logs", exist_ok=True)
    for i in sorted(live):
        if os.path.exists("STOP_NEW"):
            print("[topology] STOP_NEW present — not launching", flush=True)
            return
        launch(i)

    while any(i in procs for i in live):
        time.sleep(a.poll)
        if os.path.exists("STOP_NEW"):
            print("[topology] STOP_NEW — waiting for running jobs, launching nothing", flush=True)
        for i in list(live):
            p = procs.get(i)
            if p is None or p.poll() is None:
                continue
            if p.returncode == 0:
                print(f"[topology] job {i} DONE", flush=True)
                live.discard(i)
                procs.pop(i)
            elif retries[i] < a.max_retries and not os.path.exists("STOP_NEW"):
                retries[i] += 1
                print(f"[topology] job {i} crashed (rc={p.returncode}), retry {retries[i]}",
                      flush=True)
                launch(i)                        # same core, resume from its own run state
            else:
                print(f"[topology] job {i} FAILED permanently", flush=True)
                live.discard(i)
                procs.pop(i)
    print("[topology] wave complete", flush=True)


if __name__ == "__main__":
    main()
