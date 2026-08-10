"""The two-axis supply map: recovery as a function of (supply DURING the gap, supply DURING rescue).

Built after the 2026-08-10 cross-lab exchange established that `p_after` named different
variables in the two codebases.  There are two independent supply axes and every published
claim in this area sits on one of them:

    p_during  — supply held THROUGH the interruption window (h100-clocks' p_after;
                our maint / thresh / k2maint / zero phases).  Question: does the circuit
                SURVIVE the gap?
    p_rescue  — supply applied AFTER a total (p=0) interruption (our prestore / sevrate).
                Question: once collapsed, can it be REVIVED, and at what rate?

They are not the same experiment and they do not answer the same question.  Conflating them
produced an apparent inter-lab contradiction that was purely notational.

This script reads every phase that carries either coordinate, assigns each run its
(K, tau_dep, p_during, p_rescue, pre/post-emergence) cell, and prints the map with n per cell
plus the cells that are empty.  Formation (fork before emergence) and recovery (fork after
emergence) are NEVER pooled: the zero phase forks pre-emergence and answers a formation
question; k2post/prestore fork post-emergence and answer a recovery question.
"""
from __future__ import annotations
import glob
import json
import os
import re
from collections import defaultdict

W = os.path.expanduser("~/devaxis-work")


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def schedule(r):
    """(p_during, p_rescue, gap_start, rescue_start) parsed from the run's own p_schedule."""
    man = r.get("manifest") if isinstance(r.get("manifest"), dict) else {}
    ps = man.get("p_schedule") or r.get("p_schedule")
    if not ps:
        return None
    segs = sorted((int(k.split(":")[0]), float(k.split(":")[1])) for k in ps.split(","))
    fs = r.get("fork_step")
    if fs is None:
        return None
    after = [(s, v) for s, v in segs if s >= fs]
    if not after:
        return None
    p_during = after[0][1]
    p_rescue = after[1][1] if len(after) > 1 else None
    return p_during, p_rescue, after[0][0], (after[1][0] if len(after) > 1 else None)


def emerged_after(r, step):
    ch = r.get("chance_query_ctx")
    if ch is None:
        return None
    crit = ch + 0.5 * (1 - ch)
    return any(e["step"] >= step and e.get("query_ctx", 0) >= crit for e in r.get("evals", []))


def held(r):
    """Still above criterion at the last eval.

    FIXED 2026-08-10: this hard-coded 0.75, which is the K=2 bar (chance 0.50).  Applied to
    K=4 runs (chance 0.25, crit 0.625) it was STRICTER than the criterion used everywhere
    else, and reported two K=4 maintenance runs as lost that had in fact held: p_during=0.01
    read 0/7 instead of 1/7 and p_during=0.02 read 3/7 instead of 4/7.  Always derive crit
    from the run's own chance level.
    """
    ev = r.get("evals") or []
    ch = r.get("chance_query_ctx")
    if not ev or ch is None:
        return False
    return ev[-1].get("query_ctx", 0) >= ch + 0.5 * (1 - ch)


def main():
    cells = defaultdict(lambda: [0, 0])
    for d in ("postem", "maint", "thresh", "k2maint", "k2post", "k2exp", "prestore", "zero"):
        for p in glob.glob(os.path.join(W, "runs", d, "*.json")):
            r = load(p)
            if not r or not (r.get("done") or r.get("failed")):
                continue
            sch = schedule(r)
            if not sch:
                continue
            p_during, p_rescue, gap0, resc0 = sch
            man = r.get("manifest") if isinstance(r.get("manifest"), dict) else {}
            K = (man.get("task") or r.get("task") or {}).get("K")
            tau = (resc0 - gap0) if resc0 else None
            # formation vs recovery: was the parent past criterion at the fork?
            fork_q = next((e.get("query_ctx") for e in r.get("evals", [])
                           if e["step"] == r.get("fork_step")), None)
            ch = r.get("chance_query_ctx", 0.25)
            kind = "recov" if (fork_q is not None and fork_q >= ch + 0.5 * (1 - ch)) else "form"
            ok = emerged_after(r, resc0) if resc0 else held(r)
            key = (K, kind, tau, p_during, p_rescue)
            cells[key][0] += bool(ok)
            cells[key][1] += 1

    print("K  kind   tau_dep  p_during  p_rescue   outcome     n   source-question")
    print("-" * 78)
    for key in sorted(cells, key=lambda k: (k[0] or 0, k[1], k[2] or 0, k[3], k[4] or -1)):
        K, kind, tau, pd, pr = key
        ok, n = cells[key]
        q = ("SURVIVES gap" if pr is None else
             ("REVIVES after total gap" if pd == 0 else "survives-then-revives"))
        print(f"{K}  {kind:>5} {str(tau):>8} {pd:>9} {str(pr):>9}   {ok:>3}/{n:<3}  {n:>3}   {q}")

    print("\nEMPTY CELLS worth filling:")
    have = {(k[0], k[1], k[3], k[4]) for k in cells}
    for K in (2, 4):
        for pd in (0.005, 0.01):
            if (K, "recov", pd, 1.0) not in have:
                print(f"  K={K} recovery, p_during={pd}, p_rescue=1.0 — the direct h100-X9 cell "
                      f"(their result: K=2 p_during=0.01 -> 3/3 re-form)")
    print("\nNOTE: 'form' rows fork BEFORE emergence and answer a formation question; they are")
    print("never pooled with 'recov' rows.  Retention cells (p_rescue=None) ask whether the")
    print("circuit survived; revival cells ask whether it came back.")


if __name__ == "__main__":
    main()
