"""Deadline guard.  Capacity blocks TERMINATE at EndDate and destroy local storage — only S3
survives.  The H100 program lost nothing only because its guard was patched IN TIME; this one
syncs every cycle from first boot (the lesson, encoded).

T-2h: create STOP_NEW (topology launches nothing new).
T-30m: SIGTERM all training (engine's incremental JSON means a kill costs one eval).
Every cycle: full sync.  T-10m: sync + object-count audit to the log.
Rehearse on day 3 with a fake END_UTC 30 min out.
"""
from __future__ import annotations
import datetime as dt
import os
import subprocess
import time

END_UTC = os.environ.get("END_UTC", "2026-08-23T11:30:00Z")
WORK = os.path.expanduser("~/devaxis-work")
SYNC = os.path.expanduser("~/devaxis/platforms/neuron/sync_s3.sh")


def hours_left() -> float:
    end = dt.datetime.fromisoformat(END_UTC.replace("Z", "+00:00"))
    return (end - dt.datetime.now(dt.timezone.utc)).total_seconds() / 3600


def log(msg: str):
    line = f"{dt.datetime.utcnow().isoformat()} {msg}"
    print(line, flush=True)
    with open(os.path.join(WORK, "logs", "guard.log"), "a") as f:
        f.write(line + "\n")


def main():
    os.makedirs(os.path.join(WORK, "logs"), exist_ok=True)
    log(f"guard up, END_UTC={END_UTC}, {hours_left():.1f}h left")
    while True:
        h = hours_left()
        subprocess.run(["bash", SYNC], capture_output=True)
        if h <= 2 and not os.path.exists(os.path.join(WORK, "STOP_NEW")):
            open(os.path.join(WORK, "STOP_NEW"), "w").close()
            log("T-2h: STOP_NEW created")
        if h <= 0.5:
            log("T-30m: SIGTERM training")
            subprocess.run(["pkill", "-f", "training.train"], capture_output=True)
            subprocess.run(["bash", SYNC])
            out = subprocess.run(
                ["aws", "s3", "ls", "--recursive", "--summarize",
                 "s3://pythia-fork-experiments-434457397267/devaxis/"],
                capture_output=True, text=True)
            log("final audit:\n" + out.stdout[-2000:])
            time.sleep(600)
        time.sleep(120)


if __name__ == "__main__":
    main()
