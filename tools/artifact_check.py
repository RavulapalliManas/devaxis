"""Try to KILL the critical-period finding.  Each check is a way the result could be an
artifact rather than a fact; each prints PASS (artifact ruled out) or FAIL (artifact present).

A1  Did the rescue actually happen?  The engine records p_now = p_at(schedule, step) at every
    eval.  If p_now is not 1.0 after the rescue step, the "rescued" models were never rescued
    and the whole finding is a schedule bug.  This is the check that matters most, because a
    broken schedule reproduces the observation exactly (rescue would look like deprive — and
    right now rescue and deprive DO look identical).

A2  Did restoring supply change the gradient the model actually receives?  p controls a loss
    MASK, so restoring it adds one supervised token per sequence.  The training loss should
    show a visible discontinuity at the rescue step.  If nothing changes in the loss, the mask
    is not moving even if p_now says it is.

A3  Is the model merely broken?  If deprivation destroyed the READ circuit too, "no emergence"
    is trivial. recap must remain ~1.0 in the deprived/rescued arms.

A4  Is the readout stuck at exactly chance, or is it moving?  A frozen number can indicate a
    dead eval path rather than a model that fails to learn.

A5  Correct unit of inference.  Arms do not contain the same parents, and parents differ
    hugely in intrinsic emergence time (7,000 to 31,750 steps).  An unpaired test across
    unequal parent sets is anti-conservative.  Recompute PAIRED, parent by parent.
"""
from __future__ import annotations
import glob
import json
import os
import statistics
from math import comb

WORK = os.path.expanduser("~/devaxis-work")
ONSET = 0.625
RESCUE_AT = 14000
FORK = 4000


def recs(d):
    out = []
    for f in sorted(glob.glob(os.path.join(WORK, "runs", d, "*.json"))):
        if f.endswith(".manifest.json"):
            continue
        try:
            out.append(json.load(open(f)))
        except Exception:
            pass
    return out


def em(r):
    return next((e["step"] for e in r.get("evals", []) if e.get("query_ctx", 0) >= ONSET), None)


def arm(r):
    return r["run_id"].split("_")[1]


def parent(r):
    return r.get("parent_run_id") or r["run_id"].split("_", 2)[-1]


B = recs("branch")
by_arm = {}
for r in B:
    by_arm.setdefault(arm(r), []).append(r)

print("=" * 72)
print("A1  DID THE RESCUE ACTUALLY HAPPEN?  (p_now after the rescue step must be 1.0)")
ok = True
for r in by_arm.get("rescue10k", []):
    post = [(e["step"], e.get("p_now")) for e in r["evals"] if e["step"] >= RESCUE_AT]
    pre = [(e["step"], e.get("p_now")) for e in r["evals"] if FORK <= e["step"] < RESCUE_AT]
    bad_post = [x for x in post if x[1] != 1.0]
    bad_pre = [x for x in pre if x[1] != 0.0]
    print(f"  {r['run_id']:28s} evals>=14000: {len(post)}  p_now!=1.0: {len(bad_post)}"
          f" | evals in [4000,14000): {len(pre)}  p_now!=0.0: {len(bad_pre)}")
    if bad_post or bad_pre or not post:
        ok = False
        print(f"     sample post-rescue: {post[:3]}  pre: {pre[:3]}")
print("  ->", "PASS: schedule verified, rescue really happened" if ok
      else "FAIL: THE RESCUE DID NOT HAPPEN — finding is a schedule artifact")

print("=" * 72)
print("A2  DID THE GRADIENT CHANGE AT RESCUE?  (loss discontinuity when the mask reopens)")
for r in by_arm.get("rescue10k", [])[:3]:
    ev = [e for e in r["evals"] if "train_loss_mean" in e]
    before = [e["train_loss_mean"] for e in ev if RESCUE_AT - 2000 <= e["step"] < RESCUE_AT]
    after = [e["train_loss_mean"] for e in ev if RESCUE_AT <= e["step"] < RESCUE_AT + 2000]
    if before and after:
        b, a = statistics.mean(before), statistics.mean(after)
        print(f"  {r['run_id']:28s} loss {b:.4f} -> {a:.4f}  delta {a-b:+.4f}"
              f"  {'DISCONTINUITY' if abs(a-b) > 0.005 else 'NO CHANGE (suspicious)'}")
    else:
        print(f"  {r['run_id']:28s} insufficient evals around rescue")

print("=" * 72)
print("A3  IS THE READ CIRCUIT INTACT?  (recap must stay ~1.0 — else the model is just broken)")
for a_name in ("deprive", "rescue10k"):
    rs = by_arm.get(a_name, [])
    finals = [r["evals"][-1]["recap"] for r in rs if r.get("evals")]
    if finals:
        print(f"  {a_name:10s} final recap: min {min(finals):.3f} median "
              f"{statistics.median(finals):.3f} max {max(finals):.3f}"
              f"  -> {'PASS (read intact)' if min(finals) > 0.9 else 'FAIL (model broken)'}")

print("=" * 72)
print("A4  IS THE READOUT MOVING?  (query_ctx range over the last 20 evals; chance = 0.25)")
for a_name in ("deprive", "rescue10k", "noop"):
    for r in by_arm.get(a_name, [])[:2]:
        q = [e["query_ctx"] for e in r["evals"][-20:]]
        if q:
            print(f"  {a_name:10s} {r['run_id']:28s} min {min(q):.3f} max {max(q):.3f} "
                  f"last {q[-1]:.3f}")

print("=" * 72)
print("A5  PAIRED ANALYSIS (same parent in both arms) — the honest unit of inference")
noop = {parent(r): r for r in by_arm.get("noop", [])}
resc = {parent(r): r for r in by_arm.get("rescue10k", [])}
pairs = sorted(set(noop) & set(resc))
print(f"  parents in BOTH arms: {pairs}")
rev = 0
for p in pairs:
    n_em, r_em = em(noop[p]), em(resc[p])
    n_delay = n_em - FORK if n_em else None
    r_last = resc[p]["evals"][-1]["step"]
    r_delay = (r_em - RESCUE_AT) if r_em else f">{r_last - RESCUE_AT} (censored)"
    if n_em and not r_em:
        rev += 1
    print(f"  {p}: noop delay {n_delay}  vs  rescue delay {r_delay}")
if pairs:
    p_sign = sum(comb(len(pairs), k) for k in range(rev, len(pairs) + 1)) / 2 ** len(pairs)
    print(f"  paired reversals {rev}/{len(pairs)}  -> exact sign test one-tailed p = {p_sign:.4f}")
    print("  NOTE: the unpaired Fisher test quoted earlier ignores this pairing AND used")
    print("  unequal parent sets; parents differ 4x in intrinsic emergence time, so the")
    print("  paired number is the defensible one.")

print("=" * 72)
print("ARM COMPLETENESS (n is not what was designed until every arm has all 7 parents)")
for a_name in sorted(by_arm):
    rs = by_arm[a_name]
    print(f"  {a_name:10s} runs {len(rs)}/7  terminal {sum(1 for r in rs if r.get('done') or r.get('failed'))}"
          f"  emerged {sum(1 for r in rs if em(r))}  parents {sorted(parent(r) for r in rs)}")
