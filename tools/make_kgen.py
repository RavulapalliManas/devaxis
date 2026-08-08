"""Phase K — does any of this generalise beyond K = 4?

Everything measured so far uses K = 4 bindings.  If the supply-dependence account is about the
task's structure rather than one arbitrary setting, the same phenomena should appear at other
binding loads, and the maintenance threshold may scale with load.

This trains fresh baselines at K = 2 and K = 8 (8 seeds each, dense early checkpoints so the
post-emergence forks the follow-ups need will exist).  It is the prerequisite for a K-generality
maintenance sweep, which is queued separately once these have emerged.

K = 2 halves the load and has chance 0.50; K = 8 doubles it, chance 0.125.  Sequence length
changes with K, so each is its own compile and its own shape bucket.
"""
from __future__ import annotations
import argparse, json, os, subprocess

def busy_cores():
    out=set()
    for p in subprocess.run(["pgrep","-f","training[.]train"],capture_output=True,text=True).stdout.split():
        try:
            for x in open(f"/proc/{p}/environ","rb").read().decode(errors="ignore").split("\0"):
                if x.startswith("NEURON_RT_VISIBLE_CORES="): out.add(int(x.split("=",1)[1]))
        except Exception: pass
    return out

BASE = dict(model=dict(d=256, nl=6, nh=8), bs=128, lr=3e-3, wd=0.1, warmup=500,
            p_schedule="1.0", steps=120000, eval_every=250, logit_every=1000, stop_at=0.90,
            mask_value="finite", ckpt_every=4000, ckpt_at=[1000,2000,3000],
            health_gate=dict(step=2000, min_recap=0.5))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--cores", default="0-31")
    ap.add_argument("--seeds", type=int, default=8)
    a=ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    lo,hi=(int(x) for x in a.cores.split("-"))
    cores=[c for c in range(lo,hi+1) if c not in busy_cores()]; assert cores
    queue,n=[],0
    for K in (2,8):
        for s in range(a.seeds):
            man=dict(BASE, run_id=f"k{K}_s{s}", init_seed=s, task=dict(K=K, D=32),
                     out_dir="runs/kgen")
            p=os.path.join(a.out,f"k{K}_s{s}.manifest.json")
            with open(p,"w") as f: json.dump(man,f,indent=1)
            queue.append(dict(manifest=p, core=cores[n%len(cores)])); n+=1
    with open(os.path.join(a.out,"queue.jsonl"),"w") as f:
        for q in queue: f.write(json.dumps(q)+"\n")
    print(f"[kgen] {n} runs (K=2 and K=8, {a.seeds} seeds each) -> {a.out}")

if __name__=="__main__": main()
