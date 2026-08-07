"""Fork a checkpoint into a child run, and certify no-op branches.

A fork is a child manifest: parent's manifest + resume_ckpt + fork_step + an intervention diff.
An EMPTY intervention is the no-op branch — the child inherits the parent's data_streams and
therefore replays the parent's exact bytes (keys are stream-addressed, not run-addressed).

The difference certificate records the tier the no-op branch achieved:
  T0  bitwise      — params byte-identical, eval streams identical (required on CPU)
  T1  deterministic— max rel param divergence <= 1e-6, eval metric drift <= 1e-5 (target on trn1)
  T2  statistical  — trajectory inside the seed band (floor for science validity)
  FAIL otherwise

CLI:
    python -m training.branch fork   --parent-manifest p.json --parent-ckpt c.pt \
        --child-run-id X --out-dir runs/ [--p-schedule S] [--switch-stream]
    python -m training.branch certify --parent-rec a.json --child-rec b.json \
        --parent-ckpt p.pt --child-ckpt c.pt --out cert.json
"""
from __future__ import annotations
import argparse
import copy
import json
import os
import torch


def fork(parent_man: dict, parent_ckpt: str, child_run_id: str, out_dir: str,
         p_schedule: str | None = None, switch_stream: bool = False) -> dict:
    side = json.load(open(parent_ckpt + ".manifest.json"))
    fork_step = side["step"]
    child = copy.deepcopy(parent_man)
    child.pop("overrides", None)
    child["run_id"] = child_run_id
    child["parent_run_id"] = parent_man["run_id"]
    child["fork_step"] = fork_step
    child["resume_ckpt"] = os.path.abspath(parent_ckpt)
    child["out_dir"] = out_dir
    streams = sorted(parent_man.get("data_streams",
                                    [dict(from_step=0, stream_id=parent_man["run_id"])]),
                     key=lambda s: s["from_step"])
    if switch_stream:
        streams = streams + [dict(from_step=fork_step, stream_id=child_run_id)]
    child["data_streams"] = streams
    if p_schedule is not None:
        child["p_schedule"] = p_schedule
    return child


def _param_compare(a_path: str, b_path: str) -> dict:
    a = torch.load(a_path, map_location="cpu", weights_only=False)["model"]
    b = torch.load(b_path, map_location="cpu", weights_only=False)["model"]
    assert a.keys() == b.keys(), "state dict key mismatch"
    bitwise = True
    max_rel = 0.0
    for k in a:
        ta, tb = a[k], b[k]
        if ta.numpy().tobytes() != tb.numpy().tobytes():
            bitwise = False
            denom = ta.norm().item() or 1.0
            max_rel = max(max_rel, (ta - tb).norm().item() / denom)
    return dict(bitwise=bitwise, max_rel_param_div=max_rel)


def certify(parent_rec: dict, child_rec: dict, parent_ckpt: str, child_ckpt: str) -> dict:
    fork_step = child_rec["fork_step"]
    pe = {e["step"]: e for e in parent_rec["evals"] if e["step"] >= fork_step}
    ce = {e["step"]: e for e in child_rec["evals"]}
    common = sorted(set(pe) & set(ce))
    assert common, "no overlapping eval steps"
    drift = 0.0
    exact = True
    for s in common:
        for k in ("recap", "query", "query_ctx", "train_loss_mean"):
            if k in pe[s] and k in ce[s]:
                d = abs(pe[s][k] - ce[s][k])
                drift = max(drift, d)
                exact = exact and (d == 0.0)
    pc = _param_compare(parent_ckpt, child_ckpt)
    if pc["bitwise"] and exact:
        tier = "T0"
    elif pc["max_rel_param_div"] <= 1e-6 and drift <= 1e-5:
        tier = "T1"
    else:
        tier = "FAIL"          # T2 needs the seed band — assessed in analysis, not here
    return dict(parent_run_id=parent_rec["run_id"], child_run_id=child_rec["run_id"],
                fork_step=fork_step, eval_steps_compared=common, metric_drift_max=drift,
                metrics_exact=exact, **pc, tier=tier)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fork")
    f.add_argument("--parent-manifest", required=True)
    f.add_argument("--parent-ckpt", required=True)
    f.add_argument("--child-run-id", required=True)
    f.add_argument("--out-dir", required=True)
    f.add_argument("--p-schedule", default=None)
    f.add_argument("--switch-stream", action="store_true")
    c = sub.add_parser("certify")
    c.add_argument("--parent-rec", required=True)
    c.add_argument("--child-rec", required=True)
    c.add_argument("--parent-ckpt", required=True)
    c.add_argument("--child-ckpt", required=True)
    c.add_argument("--out", required=True)
    a = ap.parse_args()

    if a.cmd == "fork":
        child = fork(json.load(open(a.parent_manifest)), a.parent_ckpt, a.child_run_id,
                     a.out_dir, a.p_schedule, a.switch_stream)
        path = os.path.join(a.out_dir, f"{a.child_run_id}.manifest.json")
        os.makedirs(a.out_dir, exist_ok=True)
        with open(path, "w") as fh:
            json.dump(child, fh, indent=1)
        print(path)
    else:
        cert = certify(json.load(open(a.parent_rec)), json.load(open(a.child_rec)),
                       a.parent_ckpt, a.child_ckpt)
        with open(a.out, "w") as fh:
            json.dump(cert, fh, indent=1)
        print(json.dumps(cert, indent=1))


if __name__ == "__main__":
    main()
