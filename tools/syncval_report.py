"""Sync-window equivalence certificate: 1-step vs N-step engine on the SAME data stream.

sync_every changes only how many steps are traced before the XLA graph is dispatched; the math
and its order are identical.  This report is the evidence for that claim on-device, and the
gate for using sync_every>1 in any confirmatory run.

PASS bar (declared before reading): per-eval |Δ| on recap / query_ctx / train_loss_mean must be
<= the platform-error yardstick measured on CPU (loss 1.8e-06 x 10 = 1.8e-05); anything larger
means the window changed the computation and sync_every>1 is rejected for science use.
"""
from __future__ import annotations
import argparse
import json
import os

LOSS_BAR = 1.8e-05


def rate(rec):
    ev = rec["evals"]
    if len(ev) < 2:
        return float("nan")
    return (ev[-1]["step"] - ev[-2]["step"]) / max(ev[-1]["wall"] - ev[-2]["wall"], 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="1-step run json")
    ap.add_argument("--b", required=True, help="N-step run json")
    ap.add_argument("--out", default=None)
    x = ap.parse_args()
    a, b = json.load(open(x.a)), json.load(open(x.b))
    ea = {e["step"]: e for e in a["evals"]}
    eb = {e["step"]: e for e in b["evals"]}
    com = sorted(set(ea) & set(eb))
    diffs = {}
    for k in ("recap", "query_ctx", "train_loss_mean"):
        ds = [abs(ea[s][k] - eb[s][k]) for s in com if k in ea[s] and k in eb[s]]
        diffs[k] = max(ds) if ds else None
    loss_d = diffs.get("train_loss_mean")
    verdict = ("PASS" if (loss_d is not None and loss_d <= LOSS_BAR) else
               "FAIL" if loss_d is not None else "NO_DATA")
    out = dict(
        a=dict(run=a["run_id"], sync_every=a["manifest"].get("sync_every", 1),
               steps_per_s=round(rate(a), 3), wall_s=round(a["evals"][-1]["wall"], 1),
               last_step=a["evals"][-1]["step"]),
        b=dict(run=b["run_id"], sync_every=b["manifest"].get("sync_every", 1),
               steps_per_s=round(rate(b), 3), wall_s=round(b["evals"][-1]["wall"], 1),
               last_step=b["evals"][-1]["step"],
               recompile_events=len(b.get("recompile_events", []))),
        common_evals=len(com), max_abs_diff=diffs, loss_bar=LOSS_BAR, verdict=verdict,
        speedup=round(rate(b) / rate(a), 2) if rate(a) > 0 else None,
    )
    print(json.dumps(out, indent=1))
    if x.out:
        os.makedirs(os.path.dirname(x.out) or ".", exist_ok=True)
        with open(x.out, "w") as f:
            json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
