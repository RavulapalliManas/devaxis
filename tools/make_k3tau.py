"""Phase K3-tau — the K=3 deprivation dose-response: the second interior point of tau_c(K).

PRE-REGISTERED before any run.  The fate map so far: K=2 never forecloses (8/8 at tau up to
10k; deprivation only delays), K=4 forecloses monotonically (2k->4/8, 5k->2/8, 10k->0/20).
K=3 baselines emerged 8/8 at 6,500-13,000, so a fork at 3,000 is pre-emergence for every
parent (the design property, not the raw number).  tau in {2000, 5000, 10000}, mirroring both
sweeps; budget 70,000; parent's own byte stream.

Predictions, stated before the data: if the foreclosure boundary interpolates in K, K=3 lands
between K=2's 8/8-everywhere and K=4's 4/8 / 2/8 / 0/x — e.g. tau=10k strictly between 0 and 8.
A K=2-like result (8/8 everywhere) puts the boundary sharply between K=3 and K=4; a K=4-like
result puts it between 2 and 3.
"""
from __future__ import annotations
import argparse, json, os, subprocess

FORK, TAUS, BUDGET = 3000, [2000, 5000, 10000], 70000


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
    ap.add_argument("--k36", default=os.path.expanduser("~/devaxis-work/k36mx"))
    ap.add_argument("--runs", default="runs/kgen")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cores", default="0-31")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lo, hi = (int(x) for x in a.cores.split("-"))
    cores = [c for c in range(lo, hi + 1) if c not in busy_cores()] or list(range(lo, hi + 1))
    queue, n = [], 0
    for s in range(8):
        rid = f"k3_s{s}"
        mp = os.path.join(a.k36, f"{rid}.manifest.json")
        ck = os.path.join(a.runs, "ckpt", rid, f"step{FORK}.pt")
        rj = os.path.join(a.runs, f"{rid}.json")
        if not (os.path.exists(mp) and os.path.exists(ck) and os.path.exists(rj)):
            print(f"[skip] {rid}: manifest={os.path.exists(mp)} ckpt={os.path.exists(ck)}")
            continue
        r = json.load(open(rj))
        crit = r["chance_query_ctx"] + 0.5 * (1 - r["chance_query_ctx"])
        e3k = next((e for e in r.get("evals", []) if e["step"] == FORK), None)
        if e3k and e3k.get("query_ctx", 0) >= crit:
            print(f"[skip] {rid}: emerged before {FORK} — fork not pre-emergence")
            continue
        pman = json.load(open(mp))
        for tau in TAUS:
            child = dict(pman)
            child.pop("condition", None)
            child.update(run_id=f"k3tau{tau}_{rid}", parent_run_id=rid, fork_step=FORK,
                         resume_ckpt=os.path.abspath(ck),
                         p_schedule=f"0:1.0,{FORK}:0.0,{FORK + tau}:1.0",
                         steps=BUDGET, stop_at=0.90, ckpt_every=0, ckpt_at=[],
                         out_dir="runs/k3tau",
                         data_streams=[dict(from_step=0, stream_id=rid)],
                         health_gate=dict(step=FORK + 2000, min_recap=0.5))
            p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
            with open(p, "w") as f:
                json.dump(child, f, indent=1)
            queue.append(dict(manifest=p, core=cores[n % len(cores)]))
            n += 1
    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[k3tau] {n} runs -> {a.out}")


if __name__ == "__main__":
    main()
