"""Open-ended experiment runner: reads PROGRAM.json and executes phases forever.

Why this exists: the overnight orchestrator's phase list is baked into the running process, so
adding an experiment meant restarting it (killing live dispatchers).  This reads its queue from
a FILE on every iteration, so new phases can be appended at any time — including by me, while
it runs — and the box never goes idle for want of a plan.

PROGRAM.json is a list of phases:
    {"name": "mech", "builder": ["tools/make_mechanism.py", "--out", "<WORK>/mechmx"],
     "queue": "<WORK>/mechmx/queue.jsonl", "run_dir": "runs/mech"}

Rules, all learned from failures today:
  * waits for any other devaxis wave to finish before starting (one writer per core);
  * builders skip busy cores themselves, so overlap is safe even if that check races;
  * a phase that fails is recorded and the next one runs;
  * completion is judged by diffing the QUEUE against the RESULTS — a job that never starts
    leaves no JSON and would otherwise be invisible;
  * state is kept in PROGRAM_STATE.json so a restart resumes instead of re-running;
  * the morning report is regenerated after every phase, so there is always a current answer.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import time

WORK = os.path.expanduser("~/devaxis-work")
DEVAXIS = os.path.expanduser("~/devaxis")
S3 = "s3://pythia-fork-experiments-434457397267/devaxis"
PROGRAM = os.path.join(WORK, "PROGRAM.json")
STATE = os.path.join(WORK, "PROGRAM_STATE.json")
POLL = 120
STALL_MIN = 60


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(os.path.join(WORK, "logs", "program.log"), "a") as f:
        f.write(line + "\n")


def state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {}


def save_state(st):
    with open(STATE, "w") as f:
        json.dump(st, f, indent=1)


def other_orchestrator_active():
    """True while the older overnight orchestrator still owns the box.  Waiting on trainer
    count alone is not enough: between its phases the count momentarily hits zero, and both
    runners would grab cores in that gap."""
    r = subprocess.run(["systemctl", "is-active", "devaxis-overnight"],
                       capture_output=True, text=True)
    return r.stdout.strip() == "active"


def trainers():
    out = subprocess.run(["pgrep", "-fc", "training[.]train"], capture_output=True, text=True)
    try:
        return int(out.stdout.strip() or 0)
    except ValueError:
        return 0


def pending(queue, run_dir):
    """Jobs in the queue with no terminal run record — the honest 'what is left'."""
    left = []
    try:
        jobs = [json.loads(l) for l in open(queue) if l.strip()]
    except Exception:
        return None
    for j in jobs:
        try:
            rid = json.load(open(j["manifest"]))["run_id"]
        except Exception:
            continue
        p = os.path.join(WORK, run_dir, f"{rid}.json")
        if not os.path.exists(p):
            left.append(rid)
            continue
        try:
            r = json.load(open(p))
        except Exception:
            left.append(rid)
            continue
        if not (r.get("done") or r.get("failed")):
            left.append(rid)
    return left


def report():
    subprocess.run([sys.executable, os.path.join(DEVAXIS, "tools/morning_report.py"),
                    "--out", os.path.join(WORK, "MORNING_REPORT.md")],
                   cwd=WORK, capture_output=True)
    subprocess.run(["aws", "s3", "cp", os.path.join(WORK, "MORNING_REPORT.md"),
                    f"{S3}/MORNING_REPORT.md", "--only-show-errors"], capture_output=True)
    subprocess.run(["bash", os.path.join(DEVAXIS, "platforms/neuron/sync_s3.sh")],
                   capture_output=True)


def run_phase(ph):
    name, queue, run_dir = ph["name"], ph["queue"].replace("<WORK>", WORK), ph["run_dir"]
    builder = [x.replace("<WORK>", WORK) for x in ph["builder"]]
    builder[0] = os.path.join(DEVAXIS, builder[0])
    log(f"[{name}] building")
    r = subprocess.run([sys.executable, *builder], cwd=WORK, capture_output=True, text=True)
    log(f"[{name}] build: {r.stdout.strip()[:400]} {r.stderr.strip()[-300:]}")
    if r.returncode != 0:
        return dict(name=name, status="BUILD_FAILED")
    left = pending(queue, run_dir)
    if left is None:
        return dict(name=name, status="NO_QUEUE")
    if not left:
        return dict(name=name, status="ALREADY_COMPLETE")
    log(f"[{name}] {len(left)} jobs to run")
    logf = open(os.path.join(WORK, "logs", f"topology_{name}.log"), "a")
    proc = subprocess.Popen([sys.executable,
                             os.path.join(DEVAXIS, "platforms/neuron/topology.py"),
                             "--queue", queue], cwd=WORK, stdout=logf,
                            stderr=subprocess.STDOUT)
    last, changed, revived = None, time.time(), 0
    while True:
        if os.path.exists(os.path.join(WORK, "STOP_NEW")):
            log(f"[{name}] STOP_NEW — stopping")
            proc.terminate()
            return dict(name=name, status="STOPPED_BY_GUARD")
        left = pending(queue, run_dir)
        if not left:
            log(f"[{name}] COMPLETE")
            if proc.poll() is None:
                proc.terminate()
            return dict(name=name, status="OK")
        if len(left) != last:
            last, changed = len(left), time.time()
            log(f"[{name}] {len(left)} left, {trainers()} trainers")
        if proc.poll() is not None and revived < 5:
            revived += 1
            log(f"[{name}] dispatcher exited with {len(left)} left — reviving ({revived}/5)")
            proc = subprocess.Popen([sys.executable,
                                     os.path.join(DEVAXIS, "platforms/neuron/topology.py"),
                                     "--queue", queue], cwd=WORK, stdout=logf,
                                    stderr=subprocess.STDOUT)
            changed = time.time()
        elif time.time() - changed > STALL_MIN * 60:
            log(f"[{name}] STALLED {STALL_MIN} min — abandoning, {len(left)} unfinished")
            if proc.poll() is None:
                proc.terminate()
            return dict(name=name, status="STALLED", unfinished=left)
        time.sleep(POLL)


def main():
    os.makedirs(os.path.join(WORK, "logs"), exist_ok=True)
    log("=== PROGRAM RUNNER START ===")
    while True:
        try:
            phases = json.load(open(PROGRAM))
        except Exception as e:
            log(f"no PROGRAM.json ({e}); sleeping")
            time.sleep(300)
            continue
        st = state()
        nxt = next((p for p in phases if st.get(p["name"], {}).get("status") not in
                    ("OK", "ALREADY_COMPLETE")), None)
        if nxt is None:
            log("all phases complete; regenerating report and idling")
            report()
            time.sleep(600)
            continue
        while trainers() > 0 or other_orchestrator_active():
            log(f"waiting: {trainers()} trainers, overnight active="
                f"{other_orchestrator_active()}")
            time.sleep(POLL)
            if os.path.exists(os.path.join(WORK, "STOP_NEW")):
                log("STOP_NEW while waiting — exiting")
                return
        res = run_phase(nxt)
        log(f"[{nxt['name']}] -> {res['status']}")
        st[nxt["name"]] = res
        save_state(st)
        report()


if __name__ == "__main__":
    main()
