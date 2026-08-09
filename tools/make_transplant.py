"""Phase TX — the transplant battery: WHERE does foreclosure live in the weights?

PRE-REGISTERED before any run (program doc Experiment 5.1, minimal registered version).

For each original K=4 parent (s0-s7) there exist a PLASTIC checkpoint (factorial step4000 —
the tomography's age-0 positive control, chi(delta=8k) = +0.51) and a FORECLOSED checkpoint
(tomotraj step24000 — chi ~ 0).  Chimeras swap layer groups between them; every chimera gets
a fresh optimizer (the no-swap control absorbs that co-intervention — optreset alone measured
~0/7).  Each chimera runs a pulse arm (p=1, 4,000 steps) and a control arm (p=0), identical
bytes; chi_chimera = Δgold_mass(pulse − control) at the last logit eval.

Arms per parent:
    noop   F-base, swap nothing          — fresh-optimizer control (expected ~0)
    lower  F-base <- P {emb,b0,b1,b2}    — is plasticity in the lower half?
    upper  F-base <- P {b3,b4,b5,out}    — or the upper half?
    full   F-base <- P everything        — positive control (expected ~ plastic chi)
    revup  P-base <- F {b3,b4,b5,out}    — does foreclosure TRANSFER into a plastic state?

CONFOUND GUARD (doc falsification #7): a swap that restores CURRENT behavior transferred
performance, not plasticity.  The first eval at the fork is recorded in every run; F-base
chimeras whose pre-pulse query exceeds the emergence criterion are excluded from the
plasticity claim and reported separately.

Predictions, stated before the data: if a partial swap (lower XOR upper) restores chi toward
the full-swap level while pre-pulse behavior stays at chance, foreclosure is modular and
localized; if only the full swap restores chi, the state is distributed; if revup drags
plastic chi toward 0, foreclosure transfers — evidence it is carried by those weights rather
than by a global property.  noop ~ 0 is the gate for all of it.

STAGE canary: ONE noop chimera (s0) + a 500-step pulse — proves the merged-checkpoint path
loads under the engine (sha256 sidecar, nparam, lr asserts) before 80 runs queue behind it.
STAGE battery: gated on the canary run being terminal with recap >= 0.99 at its last eval.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.expanduser("~/devaxis"))
from tools.transplant import make_chimera          # noqa: E402

PARENTS = [f"q4_s{s}" for s in range(8)]
F_STEP, P_STEP, DELTA = 24000, 4000, 4000
ARMS = dict(noop=("F", []), lower=("F", ["emb", "b0", "b1", "b2"]),
            upper=("F", ["b3", "b4", "b5", "out"]),
            full=("F", ["emb", "b0", "b1", "b2", "b3", "b4", "b5", "out"]),
            revup=("P", ["b3", "b4", "b5", "out"]))


def busy_cores():
    out = set()
    for p in subprocess.run(["pgrep", "-f", "training[.]train"],
                            capture_output=True, text=True).stdout.split():
        try:
            for x in open(f"/proc/{p}/environ", "rb").read().decode(errors="ignore").split("\0"):
                if x.startswith("NEURON_RT_VISIBLE_CORES="):
                    out.add(int(x.split("=", 1)[1]))
        except Exception:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["canary", "battery"], required=True)
    ap.add_argument("--factorial", default=os.path.expanduser("~/devaxis-work/factorial"))
    ap.add_argument("--runs", default="runs/factorial")
    ap.add_argument("--traj-runs", default="runs/tomo_traj")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cores", default="0-31")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ckdir = os.path.join(a.out, "chimeras")
    lo, hi = (int(x) for x in a.cores.split("-"))
    cores = [c for c in range(lo, hi + 1) if c not in busy_cores()] or list(range(lo, hi + 1))

    if a.stage == "battery":
        cj = "runs/transplant/txcanary_pulse.json"
        r = json.load(open(cj)) if os.path.exists(cj) else None
        ok = bool(r and (r.get("done") or r.get("failed")) and not r.get("failed")
                  and r.get("evals") and r["evals"][-1].get("recap", 0) >= 0.99)
        if not ok:
            print(f"[tx:battery] NOT READY — canary state: "
                  f"{'missing' if not r else ('failed:' + str(r.get('failed'))) if r and r.get('failed') else 'unhealthy/running'}")
            sys.exit(1)

    queue, n = [], 0
    parents = PARENTS[:1] if a.stage == "canary" else PARENTS
    arms = {"noop": ARMS["noop"]} if a.stage == "canary" else ARMS
    for rid in parents:
        p_ck = os.path.join(a.runs, "ckpt", rid, f"step{P_STEP}.pt")
        f_ck = os.path.join(a.traj_runs, "ckpt", f"tomotraj_{rid}", f"step{F_STEP}.pt")
        mp = os.path.join(a.factorial, f"{rid}.manifest.json")
        if not (os.path.exists(p_ck) and os.path.exists(f_ck) and os.path.exists(mp)):
            print(f"[skip] {rid}")
            continue
        pman = json.load(open(mp))
        for arm, (base, groups) in arms.items():
            recipient, donor = (f_ck, p_ck) if base == "F" else (p_ck, f_ck)
            base_step = F_STEP if base == "F" else P_STEP
            ch = os.path.join(ckdir, f"{arm}_{rid}.pt")
            side = make_chimera(recipient, donor, groups, ch)
            print(f"[chimera] {arm}_{rid}: swapped {side['n_tensors_swapped']} tensors")
            pulse_steps = 500 if a.stage == "canary" else DELTA
            for pa, pv in (("pulse", "1.0"), ("ctrl", "0.0")):
                if a.stage == "canary" and pa == "ctrl":
                    continue
                child = dict(pman)
                child.pop("condition", None)
                child.pop("health_gate", None)
                child.update(run_id=(f"txcanary_{pa}" if a.stage == "canary"
                                     else f"tx_{arm}_{pa}_{rid}"),
                             parent_run_id=rid, fork_step=base_step,
                             resume_ckpt=os.path.abspath(ch), p_schedule=f"0:{pv}",
                             steps=base_step + pulse_steps, stop_at=2.0,
                             ckpt_every=0, ckpt_at=[], out_dir="runs/transplant",
                             data_streams=[dict(from_step=0, stream_id=rid)])
                mpth = os.path.join(a.out, f"{child['run_id']}.manifest.json")
                with open(mpth, "w") as f:
                    json.dump(child, f, indent=1)
                queue.append(dict(manifest=mpth, core=cores[n % len(cores)]))
                n += 1
    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[tx:{a.stage}] {n} runs -> {a.out}")


if __name__ == "__main__":
    main()
