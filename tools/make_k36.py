"""Phase K36 — baselines at K = 3 and K = 6: the interior of the phase diagram.

PRE-REGISTERED before any run.  The (K, tau) fate map now has measured corners:
K = 2 recovers on both sides (foreclosure weak: tau=2k 8/8, 5k 8/8, 10k 6/8+; formed circuits
recover after collapse), K = 4 is absorbing on both sides (tau>=10k 0/20; postresc 0/7), K = 8
not yet emerged.  A phase BOUNDARY tau_c(K) — the transformative version of the claim — needs
interior points.  This trains 8 fresh baselines each at K = 3 (chance 1/3) and K = 6
(chance 1/6) with dense early checkpoints, exactly as make_kgen did for K = 2/8, so the
follow-up tau sweeps and post-emergence forks have their parents.  Each K is its own sequence
length, its own compile, its own shape bucket.
"""
from __future__ import annotations
import argparse, json, os, subprocess

BASE = dict(model=dict(d=256, nl=6, nh=8), bs=128, lr=3e-3, wd=0.1, warmup=500,
            p_schedule="1.0", steps=120000, eval_every=250, logit_every=1000, stop_at=0.90,
            # ckpt_every=8000 (not 4000): 16 runs x 120k at 4000 would be ~28G of the 50G
            # left on disk; dense early ckpt_at covers the pre-emergence fork ages the tau
            # sweeps actually need
            mask_value="finite", ckpt_every=8000, ckpt_at=[1000, 2000, 3000, 4000, 6000],
            health_gate=dict(step=2000, min_recap=0.5))


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
    ap.add_argument("--out", required=True)
    ap.add_argument("--cores", default="0-31")
    ap.add_argument("--seeds", type=int, default=8)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    lo, hi = (int(x) for x in a.cores.split("-"))
    cores = [c for c in range(lo, hi + 1) if c not in busy_cores()]
    assert cores
    queue, n = [], 0
    for K in (3, 6):
        for s in range(a.seeds):
            man = dict(BASE, run_id=f"k{K}_s{s}", init_seed=s, task=dict(K=K, D=32),
                       out_dir="runs/kgen")
            p = os.path.join(a.out, f"k{K}_s{s}.manifest.json")
            with open(p, "w") as f:
                json.dump(man, f, indent=1)
            queue.append(dict(manifest=p, core=cores[n % len(cores)]))
            n += 1
    with open(os.path.join(a.out, "queue.jsonl"), "w") as f:
        for q in queue:
            f.write(json.dumps(q) + "\n")
    print(f"[k36] {n} runs (K=3 and K=6, {a.seeds} seeds each) -> {a.out}")


if __name__ == "__main__":
    main()
