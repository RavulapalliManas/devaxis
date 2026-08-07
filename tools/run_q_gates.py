"""Q2 (exact-branch replay) and Q3 (numerical equivalence) on free NeuronCores.

Q3 — platform error.  Same tiny model, same keyed stream (q3data), 200 steps, run on Neuron in
fp32 and under the bf16 policy.  Compared against the CPU legs already in S3
(devaxis/reference/q3_cpu): the CPU fp32-vs-fp64 gap is the yardstick, and Neuron must land
within 10x of it — loss <= 1.8e-05, final-param relative L2 <= 2.5e-03.

Q2 — branch replay.  Fork a finished run at a checkpoint with an EMPTY intervention and rerun
the same span; the child must reproduce the parent (tier T0 bitwise / T1 tolerance).  This is
what makes every later branch-matrix intervention interpretable: without it, a difference
between parent and child could just be the platform.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys

import torch

REF = "s3://pythia-fork-experiments-434457397267/devaxis/reference/q3_cpu"
LOSS_BAR, PARAM_BAR = 1.8e-05, 2.5e-03


def run(manifest_path, core, backend="neuron"):
    env = dict(os.environ, NEURON_RT_VISIBLE_CORES=str(core))
    return subprocess.run([sys.executable, "-m", "training.train", "--manifest", manifest_path,
                           "--backend", backend], env=env, capture_output=True, text=True)


def param_rel_l2(a_path, b_path):
    a = torch.load(a_path, map_location="cpu", weights_only=False)["model"]
    b = torch.load(b_path, map_location="cpu", weights_only=False)["model"]
    num = sum(float((a[k].double() - b[k].double()).norm()) ** 2 for k in a) ** 0.5
    den = sum(float(a[k].double().norm()) ** 2 for k in a) ** 0.5
    return num / den


def loss_traj(rec):
    return [e["train_loss_mean"] for e in rec["evals"] if "train_loss_mean" in e]


def q3(out_dir, core0):
    os.makedirs("ref_cpu", exist_ok=True)
    subprocess.run(["aws", "s3", "sync", REF, "ref_cpu", "--only-show-errors"], check=False)
    base = json.load(open(os.path.expanduser("~/devaxis/configs/q3_tiny.json")))
    base["out_dir"] = out_dir
    base["mask_value"] = "finite"
    legs = {}
    for i, (name, prec) in enumerate((("q3_neuron_fp32", "fp32"),
                                      ("q3_neuron_bf16", "bf16_autocast"))):
        man = dict(base, run_id=name, precision=prec)
        p = f"/tmp/{name}.json"
        json.dump(man, open(p, "w"))
        r = run(p, core0 + i)
        legs[name] = (r.returncode, p)
        print(f"[Q3] {name} rc={r.returncode}", flush=True)
        if r.returncode:
            print(r.stdout[-1500:], r.stderr[-800:])
    res = {}
    cpu64 = json.load(open("ref_cpu/q3_cpu64.json"))
    yard = json.load(open("ref_cpu/q3_cpu_reference_error.json"))
    for name in legs:
        f = os.path.join(out_dir, f"{name}.json")
        if not os.path.exists(f):
            res[name] = dict(verdict="NO_OUTPUT")
            continue
        rec = json.load(open(f))
        a, b = loss_traj(cpu64), loss_traj(rec)
        n = min(len(a), len(b))
        dloss = max(abs(x - y) for x, y in zip(a[:n], b[:n])) if n else None
        ck_n = os.path.join(out_dir, "ckpt", name, "step200.pt")
        ck_c = "ref_cpu/ckpt/q3_cpu64/step200.pt"
        dparam = param_rel_l2(ck_c, ck_n) if os.path.exists(ck_n) else None
        ok = (dloss is not None and dloss <= LOSS_BAR and
              dparam is not None and dparam <= PARAM_BAR)
        res[name] = dict(max_loss_diff_vs_cpu64=dloss, param_rel_l2_vs_cpu64=dparam,
                         loss_bar=LOSS_BAR, param_bar=PARAM_BAR,
                         cpu_yardstick=yard, verdict="PASS" if ok else "FAIL")
        print(f"[Q3] {name}: loss_diff={dloss} param_relL2={dparam} -> {res[name]['verdict']}",
              flush=True)
    return res


def q2(parent_run, out_dir, core, fork_step, target_step):
    from training import branch
    fdir = os.path.expanduser("~/devaxis-work/factorial")
    parent_man = json.load(open(os.path.join(fdir, f"{parent_run}.manifest.json")))
    pck = os.path.join("runs/factorial/ckpt", parent_run, f"step{fork_step}.pt")
    if not os.path.exists(pck):
        return dict(verdict="NO_PARENT_CKPT", looked_for=pck)
    child = branch.fork(parent_man, pck, f"q2_noop_{parent_run}", out_dir)
    child["ckpt_at"] = [target_step]
    child["steps"] = target_step
    child["stop_at"] = 0.0
    cp = "/tmp/q2_child.json"
    json.dump(child, open(cp, "w"))
    r = run(cp, core)
    print(f"[Q2] child rc={r.returncode}", flush=True)
    crec_p = os.path.join(out_dir, f"{child['run_id']}.json")
    if not os.path.exists(crec_p):
        return dict(verdict="NO_CHILD_OUTPUT", stderr=r.stderr[-800:])
    prec = json.load(open(os.path.join("runs/factorial", f"{parent_run}.json")))
    crec = json.load(open(crec_p))
    cert = branch.certify(prec, crec,
                          os.path.join("runs/factorial/ckpt", parent_run, f"step{target_step}.pt"),
                          os.path.join(out_dir, "ckpt", child["run_id"], f"step{target_step}.pt"))
    print(f"[Q2] tier={cert['tier']} drift={cert['metric_drift_max']} "
          f"relparam={cert['max_rel_param_div']}", flush=True)
    return cert


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="runs/qgates")
    ap.add_argument("--core0", type=int, default=28)
    ap.add_argument("--parent", default="q4_s5")
    ap.add_argument("--fork-step", type=int, default=4000)
    ap.add_argument("--target-step", type=int, default=8000)
    a = ap.parse_args()
    os.makedirs("gates", exist_ok=True)
    out = {}
    out["Q3"] = q3(a.out, a.core0)
    out["Q2"] = q2(a.parent, a.out, a.core0 + 2, a.fork_step, a.target_step)
    with open("gates/q2_q3.json", "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
