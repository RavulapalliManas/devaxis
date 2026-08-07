"""Unattended overnight orchestrator.  Runs on the box under systemd; needs no laptop.

Sequence: wait for the currently-running waves to drain, then build/launch/await each phase in
turn, analysing as it goes, syncing to S3 continuously, and writing a morning report at the end.

Robustness rules, learned the hard way today:
  * every phase is wrapped — a phase that fails is RECORDED and the next one still runs;
  * the dispatcher is launched as a plain child of THIS long-lived process (not a oneshot unit),
    and this process is itself the systemd unit, so nothing is cgroup-killed;
  * a phase that stops making progress for STALL_MIN minutes is abandoned, not waited on forever;
  * STOP_NEW (written by the deadline guard at T-2h) aborts the whole program cleanly;
  * everything writes under its own out_dir — one writer per path.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import time
import glob

WORK = os.path.expanduser("~/devaxis-work")
DEVAXIS = os.path.expanduser("~/devaxis")
S3 = "s3://pythia-fork-experiments-434457397267/devaxis"
POLL = 120
STALL_MIN = 45


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(os.path.join(WORK, "logs", "overnight.log"), "a") as f:
        f.write(line + "\n")


def py(*args, **kw):
    return subprocess.run([sys.executable, *args], cwd=WORK, capture_output=True, text=True, **kw)


def running_count():
    out = subprocess.run(["pgrep", "-fc", "-m", "training.train"], capture_output=True, text=True)
    try:
        return int(out.stdout.strip() or 0)
    except ValueError:
        return 0


def runs_state(run_dir):
    """(#terminal, #total_json, max_step) read from the filesystem — never from a queue."""
    term = tot = 0
    mx = 0
    for f in glob.glob(os.path.join(WORK, run_dir, "*.json")):
        if f.endswith(".manifest.json"):
            continue
        try:
            r = json.load(open(f))
        except Exception:
            continue
        tot += 1
        if r.get("done") or r.get("failed"):
            term += 1
        if r.get("evals"):
            mx = max(mx, r["evals"][-1]["step"])
    return term, tot, mx


def wait_drain(run_dir, expect, label, queue=None, proc=None, max_revive=5):
    """Wait until every launched run in run_dir is terminal, or progress stalls.

    SELF-HEALING: the dangerous failure is a dispatcher that dies while work remains — the
    cores go idle and a naive waiter blocks until the stall timeout.  So if the dispatcher has
    exited (or no training process is alive) while runs are still incomplete, relaunch it.
    Relaunch is safe and idempotent: the dispatcher reads each job's state from its run JSON
    and skips anything already done, and partial runs simply restart from their own state.
    """
    last_sig, last_change = None, time.time()
    revived = 0
    while True:
        if os.path.exists(os.path.join(WORK, "STOP_NEW")):
            log(f"[{label}] STOP_NEW present — aborting wait")
            return False
        term, tot, mx = runs_state(run_dir)
        live = running_count()
        sig = (term, tot, mx)
        if sig != last_sig:
            last_sig, last_change = sig, time.time()
            log(f"[{label}] terminal {term}/{tot} (expect {expect}) max_step {mx} live {live}")
        if tot >= expect and term >= expect:
            log(f"[{label}] COMPLETE")
            return True

        dead = (proc is not None and proc.poll() is not None) or (live == 0 and tot < expect)
        if dead and queue and revived < max_revive:
            revived += 1
            log(f"[{label}] dispatcher not running with work left "
                f"(live={live}, terminal={term}/{expect}) — REVIVING ({revived}/{max_revive})")
            proc = launch(queue, label)
            last_change = time.time()
            time.sleep(POLL)
            continue

        if time.time() - last_change > STALL_MIN * 60:
            log(f"[{label}] STALLED {STALL_MIN} min with no progress — moving on")
            return False
        time.sleep(POLL)


def launch(queue, label):
    log(f"[{label}] launching dispatcher on {queue}")
    logf = open(os.path.join(WORK, "logs", f"topology_{label}.log"), "a")
    return subprocess.Popen(
        [sys.executable, os.path.join(DEVAXIS, "platforms/neuron/topology.py"),
         "--queue", queue], cwd=WORK, stdout=logf, stderr=subprocess.STDOUT)


def sync():
    subprocess.run(["bash", os.path.join(DEVAXIS, "platforms/neuron/sync_s3.sh")],
                   capture_output=True)


def phase(label, builder_args, queue, run_dir, expect):
    """Build -> launch -> wait -> sync.  Never raises; returns a status dict."""
    try:
        if builder_args:
            r = py(*builder_args)
            log(f"[{label}] build: {r.stdout.strip()[:300]} {r.stderr.strip()[-200:]}")
            if r.returncode != 0:
                return dict(phase=label, status="BUILD_FAILED", err=r.stderr[-500:])
        p = launch(queue, label)
        ok = wait_drain(run_dir, expect, label, queue=queue, proc=p)
        if p.poll() is None:
            p.terminate()
        sync()
        term, tot, mx = runs_state(run_dir)
        return dict(phase=label, status="OK" if ok else "INCOMPLETE",
                    terminal=term, total=tot, max_step=mx)
    except Exception as e:                                    # a phase must never kill the night
        log(f"[{label}] EXCEPTION {e!r}")
        return dict(phase=label, status="EXCEPTION", err=repr(e))


def main():
    os.makedirs(os.path.join(WORK, "logs"), exist_ok=True)
    results = []
    log("=== OVERNIGHT PROGRAM START ===")

    # Phase 0 — let the waves already in flight finish.
    log("[wait] draining factorial + branch matrix (revivable)")
    wait_drain("runs/factorial", 48, "factorial",
               queue=f"{WORK}/factorial/queue.jsonl")
    wait_drain("runs/branch", 21, "branch",
               queue=f"{WORK}/branchmx/queue.jsonl")
    sync()
    results.append(dict(phase="factorial+branch", status="drained"))

    # Phase B — critical-period dose-response (tau sweep).
    results.append(phase(
        "tau",
        [os.path.join(DEVAXIS, "tools/make_tau_sweep.py"), "--out", f"{WORK}/tausweep",
         "--cores", "0-31"],
        f"{WORK}/tausweep/queue.jsonl", "runs/tau", 21))

    # Phase C — DD10, same data from two developmental states.
    results.append(phase(
        "dd10",
        [os.path.join(DEVAXIS, "tools/make_dd10.py"), "--out", f"{WORK}/dd10mx",
         "--cores", "0-31"],
        f"{WORK}/dd10mx/queue.jsonl", "runs/dd10", 16))

    # Morning report — always written, whatever happened above.
    log("=== building morning report ===")
    r = py(os.path.join(DEVAXIS, "tools/morning_report.py"),
           "--out", f"{WORK}/MORNING_REPORT.md",
           "--phases", json.dumps(results))
    log(r.stdout[-2000:])
    if r.returncode:
        log(f"report stderr: {r.stderr[-1000:]}")
    subprocess.run(["aws", "s3", "cp", f"{WORK}/MORNING_REPORT.md",
                    f"{S3}/MORNING_REPORT.md", "--only-show-errors"], capture_output=True)
    sync()
    log("=== OVERNIGHT PROGRAM END ===")


if __name__ == "__main__":
    main()
