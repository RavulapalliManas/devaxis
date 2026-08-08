"""Phase Z — is ZERO special, or is it just "very little"?

The pairing check forced this.  Two facts now sit side by side:

  * Supply restored to p = 1.0 AFTER an interruption never recovers the circuit.
    0 recoveries in ~21 runs (postresc 0/7, rescue10k 0/7, mech plain/optreset/rewarm/both 0/7).
  * Supply held CONTINUOUSLY at p = 0.03 recovered a circuit that had fallen to chance:
    thr003_q4_s5 (0.242 at step 11,750 -> 0.791) and thr003_q4_s6 (0.275 at 34,750 -> 0.805).

So a model on 3% supervision can climb back from chance, while a model given 100% supervision
after a gap cannot.  Continuity appears to matter independently of quantity.  The obvious
mechanistic reading: with p > 0 the answer-site gradient is intermittently nonzero, and that is
enough to prevent whatever drift makes the state unrecoverable; with p = 0 the drift completes.

THE TEST.  Replace the deprivation window's p = 0 with a TINY BUT NONZERO value, then rescue
exactly as before:

    p = 1.0 until 4000 | p in {0.001, 0.005, 0.01} for 10,000 steps | p = 1.0 after

Baseline for comparison is already measured: p = 0 in that window gives 0/7 emergence.

Declared:
  * tiny-nonzero arms RESCUE (emergence returns) -> ZERO is special. The irreversibility is not
    about how little supervision there is, but about whether it ever stops. That is a sharp,
    surprising claim with an obvious practical reading for continual training.
  * tiny-nonzero arms also fail -> the effect is about QUANTITY integrated over the window, and
    0.03 recovery is explained by dose rather than continuity. Cleaner, less interesting, fine.
"""
from __future__ import annotations
import argparse, json, os, subprocess
FORK, TAU, BUDGET = 4000, 10000, 70000

def busy_cores():
    out=set()
    for p in subprocess.run(["pgrep","-f","training[.]train"],capture_output=True,text=True).stdout.split():
        try:
            for x in open(f"/proc/{p}/environ","rb").read().decode(errors="ignore").split("\0"):
                if x.startswith("NEURON_RT_VISIBLE_CORES="): out.add(int(x.split("=",1)[1]))
        except Exception: pass
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--factorial", default=os.path.expanduser("~/devaxis-work/factorial"))
    ap.add_argument("--runs", default="runs/factorial")
    ap.add_argument("--out", required=True); ap.add_argument("--cores", default="0-31")
    a=ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    lo,hi=(int(x) for x in a.cores.split("-"))
    cores=[c for c in range(lo,hi+1) if c not in busy_cores()]; assert cores
    queue,n=[],0
    for s in range(8):
        rid=f"q4_s{s}"
        mp=os.path.join(a.factorial,f"{rid}.manifest.json")
        ck=os.path.join(a.runs,"ckpt",rid,f"step{FORK}.pt")
        if not (os.path.exists(mp) and os.path.exists(ck)): continue
        pman=json.load(open(mp))
        for pv in (0.001, 0.005, 0.01):
            child=dict(pman); child.pop("condition",None)
            child.update(run_id=f"zero{str(pv).replace('.','p')}_{rid}", parent_run_id=rid,
                         fork_step=FORK, resume_ckpt=os.path.abspath(ck),
                         p_schedule=f"0:1.0,{FORK}:{pv},{FORK+TAU}:1.0",
                         steps=BUDGET, stop_at=0.90, ckpt_every=0, ckpt_at=[],
                         out_dir="runs/zero",
                         data_streams=[dict(from_step=0, stream_id=rid)],
                         health_gate=dict(step=FORK+2000, min_recap=0.5))
            p=os.path.join(a.out,f"{child['run_id']}.manifest.json")
            with open(p,"w") as f: json.dump(child,f,indent=1)
            queue.append(dict(manifest=p, core=cores[n%len(cores)])); n+=1
    with open(os.path.join(a.out,"queue.jsonl"),"w") as f:
        for q in queue: f.write(json.dumps(q)+"\n")
    print(f"[zero] {n} runs (p in 0.001/0.005/0.01 during the window) -> {a.out}")

if __name__=="__main__": main()
