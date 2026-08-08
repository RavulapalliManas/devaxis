"""Phase E — does the window have a LOWER edge?  The test the critical-period reading predicts.

The window sweep found uniform foreclosure at ages 1k-12k, with ONE exception: at fork age
1,000, one run of five emerged (query_ctx 0.916).  n=1 is nothing on its own, but it is exactly
where a critical period would put its opening edge — before the capability's developmental
phase begins, an insult should do less permanent harm.

This raises power on precisely that question: all 8 parents at ages 1,000 / 2,000 / 3,000 with
the same tau = 10,000 insult (24 runs, versus 5 per age before).  Checkpoints already exist at
those steps, so no re-training is needed.

Declared readings:
  * emergence rate FALLS with age across 1k -> 2k -> 3k -> (4k, already 0/5+0/7) => there is an
    opening edge, the deprivation window has a lower boundary, and "critical period" gains its
    missing structure.
  * emergence stays ~0 at all three => no lower edge in this range; the age-1000 survivor was
    noise, and the uniform-foreclosure reading stands.

This is queued because the user pushed back on the framing, and the disagreement is decidable.
"""
from __future__ import annotations
import argparse, json, os, subprocess
TAU = 10000
AGES = [1000, 2000, 3000]
BUDGET = 80000

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
    queue, n, skipped = [], 0, []
    for s in range(8):
        rid = f"q4_s{s}"
        mp = os.path.join(a.factorial, f"{rid}.manifest.json")
        if not os.path.exists(mp): continue
        pman = json.load(open(mp))
        for age in AGES:
            ck = os.path.join(a.runs, "ckpt", rid, f"step{age}.pt")
            if not os.path.exists(ck): skipped.append(f"{rid}@{age}"); continue
            child = dict(pman); child.pop("condition", None)
            child.update(run_id=f"early{age}_{rid}", parent_run_id=rid, fork_step=age,
                         resume_ckpt=os.path.abspath(ck),
                         p_schedule=f"0:1.0,{age}:0.0,{age+TAU}:1.0",
                         steps=BUDGET, stop_at=0.90, ckpt_every=0, ckpt_at=[],
                         out_dir="runs/early",
                         data_streams=[dict(from_step=0, stream_id=rid)],
                         health_gate=dict(step=age+2000, min_recap=0.5))
            p = os.path.join(a.out, f"{child['run_id']}.manifest.json")
            with open(p,"w") as f: json.dump(child, f, indent=1)
            queue.append(dict(manifest=p, core=cores[n % len(cores)])); n += 1
    with open(os.path.join(a.out,"queue.jsonl"),"w") as f:
        for q in queue: f.write(json.dumps(q)+"\n")
    print(f"[early] {n} runs ({len(AGES)} ages x 8 parents) -> {a.out}"
          + (f" | skipped: {skipped}" if skipped else ""))

if __name__ == "__main__":
    main()
