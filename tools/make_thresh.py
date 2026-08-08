"""Phase T — bracket the maintenance threshold.

Phase N put it between 1% and 5%: p = 0.01 collapsed 6/7, p = 0.05 held 7/7 (dipping to
0.41-0.84 before recovering).  The dip at 5% says the threshold sits close to that value, not
far below it.  This brackets it: p in {0.02, 0.03, 0.04}, same post-emergence forks, 7 parents.

Endpoint: query_ctx at the end of a fixed 30,000-step budget, and the minimum reached after the
fork (the dip depth, which is the sensitive quantity near the threshold).

Declared: a monotone rise in final query_ctx across 0.01 -> 0.05 locates the threshold to within
one percentage point and turns "about 5%" into a measured interval.
"""
from __future__ import annotations
import argparse, glob, json, os, subprocess
ONSET, BUDGET_AFTER = 0.625, 30000

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
        rp,mp=os.path.join(a.runs,f"{rid}.json"),os.path.join(a.factorial,f"{rid}.manifest.json")
        if not (os.path.exists(rp) and os.path.exists(mp)): continue
        rec=json.load(open(rp))
        em=next((e["step"] for e in rec["evals"] if e.get("query_ctx",0)>=ONSET), None)
        if em is None: continue
        cks=sorted(int(os.path.basename(f)[4:-3]) for f in glob.glob(os.path.join(a.runs,"ckpt",rid,"step*.pt")))
        post=[c for c in cks if c>em]
        if not post: continue
        fork=post[0]; pman=json.load(open(mp))
        for pv in (0.02,0.03,0.04):
            child=dict(pman); child.pop("condition",None)
            child.update(run_id=f"thr{int(pv*100):03d}_{rid}", parent_run_id=rid, fork_step=fork,
                         resume_ckpt=os.path.abspath(os.path.join(a.runs,"ckpt",rid,f"step{fork}.pt")),
                         p_schedule=f"0:1.0,{fork}:{pv}", steps=fork+BUDGET_AFTER, stop_at=0.0,
                         ckpt_every=0, ckpt_at=[], out_dir="runs/thresh",
                         data_streams=[dict(from_step=0, stream_id=rid)],
                         health_gate=dict(step=fork+2000, min_recap=0.5))
            p=os.path.join(a.out,f"{child['run_id']}.manifest.json")
            with open(p,"w") as f: json.dump(child,f,indent=1)
            queue.append(dict(manifest=p, core=cores[n%len(cores)])); n+=1
    with open(os.path.join(a.out,"queue.jsonl"),"w") as f:
        for q in queue: f.write(json.dumps(q)+"\n")
    print(f"[thresh] {n} runs (p in 0.02/0.03/0.04) -> {a.out}")

if __name__=="__main__": main()
