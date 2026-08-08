"""Phase X — perturbational plasticity: a standardized supervision pulse at every saved age.

PRE-REGISTERED before any run of this phase.

Everything measured so far reads the model's CURRENT behavior.  The lifecycle framing needs a
third coordinate: what the model could still LEARN — plasticity — measured actively rather than
inferred from what later training happened to do.  The instrument is the cheapest possible one:
fork a saved checkpoint, apply a fixed 1,000-step supervision pulse (p = 1), and compare against
a paired control fork (p = 0) on the SAME bytes.  Susceptibility is

    chi(a) = [ q_pulse(a+1000) - q_pulse(a) ] - [ q_control(a+1000) - q_control(a) ]

per parent per age a.  The control arm subtracts drift; the byte streams are identical because
data is a pure function of (stream, step), so the pulse/control contrast isolates the loss mask.

Round 1 runs on the checkpoints that exist: the K=4 baseline parents at ages
{1000, 2000, 3000, 4000, 8000, 12000, 16000, 20000} (whatever subset each parent saved before
its early stop).  This charts chi along NORMAL development: the prediction from the account is
chi low at very young ages, rising toward emergence, ~0 after mastery (ceiling).  What it
cannot yet do is probe DEPRIVED or COLLAPSED states — those forks saved no checkpoints
(ckpt_every=0), which is exactly why the continuity and zero phases now save dense ones.
Round 2 (same builder, --runs pointed at those phases) is the decisive use: two at-chance
checkpoints, one pre-formation and one post-collapse, distinguished — or not — by chi.

Endpoints: chi(a) per parent-age, paired pulse-vs-control; no stop_at (a post-emergence pulse
must run its full window, so stop_at = 2.0 disables early stop).
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess

AGES = [1000, 2000, 3000, 4000, 8000, 12000, 16000, 20000]
PULSE = 1000


def busy_cores():
    out = set()
    for p in subprocess.run(["pgrep", "-f", "training[.]train"],
                            capture_output=True, text=True).stdout.split():
        try:
            env = open(f"/proc/{p}/environ", "rb").read().decode(errors="ignore").split("\0")
            for x in env:
                if x.startswith("NEURON_RT_VISIBLE_CORES="):
                    out.add(int(x.split("=", 1)[1]))
        except Exception:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--factorial", default=os.path.expanduser("~/devaxis-work/factorial"))
    ap.add_argument("--runs", default="runs/factorial")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cores", default="0-31")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lo, hi = (int(x) for x in a.cores.split("-"))
    held = busy_cores()
    cores = [c for c in range(lo, hi + 1) if c not in held]
    if held:
        print(f"[cores] avoiding busy cores {sorted(held)}; using {len(cores)}")
    assert cores, "no free cores"

    queue, n = [], 0
    for s in range(8):
        rid = f"q4_s{s}"
        mp = os.path.join(a.factorial, f"{rid}.manifest.json")
        if not os.path.exists(mp):
            continue
        pman = json.load(open(mp))
        for age in AGES:
            ck = os.path.join(a.runs, "ckpt", rid, f"step{age}.pt")
            if not os.path.exists(ck):
                continue
            for arm, pv in (("p", "1.0"), ("c", "0.0")):
                child = dict(pman)
                child.pop("condition", None)
                child.pop("health_gate", None)
                child.update(run_id=f"chi{age}{arm}_{rid}", parent_run_id=rid, fork_step=age,
                             resume_ckpt=os.path.abspath(ck),
                             p_schedule=f"0:{pv}", steps=age + PULSE, stop_at=2.0,
                             ckpt_every=0, ckpt_at=[], out_dir="runs/pulse",
                             data_streams=[dict(from_step=0, stream_id=rid)])
                p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
                with open(p, "w") as f:
                    json.dump(child, f, indent=1)
                queue.append(dict(manifest=p, core=cores[n % len(cores)]))
                n += 1
    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[pulse] {n} runs (pulse+control forks across saved ages) -> {a.out}")


if __name__ == "__main__":
    main()
