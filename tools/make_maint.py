"""Phase N — two follow-ups forced by the post-emergence result.

The post-emergence runs showed a FORMED circuit (query_ctx 0.76-0.99) decaying to chance when
its supply is cut, and not returning when supply is restored.  Those runs inherited the parent's
weight decay (0.1), so two things must be separated before the decay is interpreted:

  A. DECAY vs WEIGHT DECAY.  Repeat post-emergence deprivation with wd = 0.  The formation
     experiment already showed foreclosure survives wd = 0, but decay of an existing circuit is
     a different quantity and needs its own control.
  B. THE MAINTENANCE DOSE.  If the circuit needs ongoing supply to persist, how little is
     enough?  After emergence, drop p to 0.01 / 0.05 / 0.20 instead of 0 and watch.  A threshold
     would turn "needs supply" into a number.

Declared: if the wd=0 arm still decays, the decay is not weight decay.  If some low p holds
query_ctx up, maintenance is cheap and the phenomenon is a supply floor, not fragility.
"""
from __future__ import annotations
import argparse, glob, json, os, subprocess
ONSET = 0.625
BUDGET_AFTER = 30000

def busy_cores():
    out = set()
    for p in subprocess.run(["pgrep","-f","training[.]train"],capture_output=True,text=True).stdout.split():
        try:
            for x in open(f"/proc/{p}/environ","rb").read().decode(errors="ignore").split("\0"):
                if x.startswith("NEURON_RT_VISIBLE_CORES="): out.add(int(x.split("=",1)[1]))
        except Exception: pass
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
    cores = [c for c in range(lo,hi+1) if c not in busy_cores()]
    assert cores, "no free cores"
    arms = [("wd0dep", "0.0", 0.0)] + [(f"maint{int(p*100):03d}", str(p), 0.1)
                                       for p in (0.01, 0.05, 0.20)]
    queue, n = [], 0
    for s in range(8):
        rid = f"q4_s{s}"
        rp, mp = os.path.join(a.runs,f"{rid}.json"), os.path.join(a.factorial,f"{rid}.manifest.json")
        if not (os.path.exists(rp) and os.path.exists(mp)): continue
        rec = json.load(open(rp))
        em = next((e["step"] for e in rec["evals"] if e.get("query_ctx",0) >= ONSET), None)
        if em is None: continue
        cks = sorted(int(os.path.basename(f)[4:-3])
                     for f in glob.glob(os.path.join(a.runs,"ckpt",rid,"step*.pt")))
        post = [c for c in cks if c > em]
        if not post: continue
        fork = post[0]
        pman = json.load(open(mp))
        for arm, pval, wd in arms:
            child = dict(pman); child.pop("condition", None)
            child.update(run_id=f"{arm}_{rid}", parent_run_id=rid, fork_step=fork,
                         resume_ckpt=os.path.abspath(os.path.join(a.runs,"ckpt",rid,f"step{fork}.pt")),
                         p_schedule=f"0:1.0,{fork}:{pval}", wd=wd,
                         steps=fork+BUDGET_AFTER, stop_at=0.0, ckpt_every=0, ckpt_at=[],
                         out_dir="runs/maint",
                         data_streams=[dict(from_step=0, stream_id=rid)],
                         health_gate=dict(step=fork+2000, min_recap=0.5))
            p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
            with open(p,"w") as f: json.dump(child, f, indent=1)
            queue.append(dict(manifest=p, core=cores[n % len(cores)])); n += 1
    with open(os.path.join(a.out,"queue.jsonl"),"w") as f:
        for q in queue: f.write(json.dumps(q)+"\n")
    print(f"[maint] {n} runs ({len(arms)} arms) -> {a.out}")

if __name__ == "__main__":
    main()
