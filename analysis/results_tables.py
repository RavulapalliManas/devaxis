"""Every remaining results table, recomputed from the raw run JSONs with exact tests.

Written on 2026-08-10 to close a provenance hole: the rescue-rate, severity, tau_c(K),
continuity, transplant and symmetry-breaking numbers had been produced by ad-hoc tick scripts
that were never committed, so no referee could re-derive them.  Global rule: a number with no
script is a fabrication until proven otherwise.  Everything the write-up quotes that is not
already produced by km_rescued / mcnemar_k2 / chi_paired / chi_matrix / chi_normal /
supply_map / savings_k2 / unit_collapse is produced HERE.

Emergence criterion, everywhere, from each run's own recorded chance level:
    crit = chance_query_ctx + 0.5 * (1 - chance_query_ctx)
so K=2 (chance 0.50) needs 0.75 and K=4 (chance 0.25) needs 0.625.  Never hard-code 0.75:
that silently applies the K=2 bar to K=4 runs.

chi (the plasticity instrument) = Delta gold_mass between a pulse fork (p=1) and its control
fork (p=0) from the SAME checkpoint on identical bytes, at the matched last logit eval.
"""
from __future__ import annotations
import glob
import json
import os
from collections import defaultdict
from math import comb, sqrt

W = os.path.expanduser("~/devaxis-work")


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def runs(d):
    out = []
    for p in glob.glob(os.path.join(W, "runs", d, "*.json")):
        r = load(p)
        if r and (r.get("done") or r.get("failed")):
            out.append(r)
    return out


def crit(r):
    ch = r.get("chance_query_ctx")
    return None if ch is None else ch + 0.5 * (1 - ch)


def emerged_after(r, step):
    c = crit(r)
    if c is None:
        return False
    return any(e["step"] >= step and e.get("query_ctx", 0) >= c for e in r.get("evals", []))


def held_at_end(r):
    """Retention arms have no rescue segment: did the circuit still clear crit at the last eval?"""
    c, ev = crit(r), r.get("evals") or []
    return bool(ev) and c is not None and ev[-1].get("query_ctx", 0) >= c


def schedule(r):
    """(p_during, p_rescue, gap_start, rescue_start) from the run's own p_schedule."""
    man = r.get("manifest") if isinstance(r.get("manifest"), dict) else {}
    ps = man.get("p_schedule") or r.get("p_schedule")
    fs = r.get("fork_step")
    if not ps or fs is None:
        return None
    segs = sorted((int(k.split(":")[0]), float(k.split(":")[1])) for k in ps.split(","))
    after = [(s, v) for s, v in segs if s >= fs]
    if not after:
        return None
    return (after[0][1], after[1][1] if len(after) > 1 else None,
            after[0][0], after[1][0] if len(after) > 1 else None)


def fisher_two_sided(a, b, c, d):
    """Two-sided Fisher exact on [[a,b],[c,d]]: sum of tables no more probable than observed."""
    n = a + b + c + d
    r1, c1 = a + b, a + c

    def prob(x):
        return comb(r1, x) * comb(n - r1, c1 - x) / comb(n, c1)

    p0 = prob(a)
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= p0 * (1 + 1e-9)))


def mean_sd(xs):
    if not xs:
        return None, None, 0
    m = sum(xs) / len(xs)
    if len(xs) < 2:
        return m, 0.0, len(xs)
    return m, sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1)), len(xs)


def rate(hits, n):
    return f"{hits}/{n}"


# ---------------------------------------------------------------- tau_c(K)

def tau_boundary():
    print("\n=== A. tau_c(K): recovery after a TOTAL gap of length tau, full supply restored ===")
    print("    (fork pre-emergence; emergence judged after the rescue step, each run's own crit)")
    print("  K   tau_dep   emerged      n")
    rowsK = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for d, K in (("kgen_tau", 2), ("k3tau", 3), ("tau", 4)):
        for r in runs(d):
            s = schedule(r)
            if not s or s[3] is None:
                continue
            tau = s[3] - s[2]
            rowsK[K][tau][0] += bool(emerged_after(r, s[3]))
            rowsK[K][tau][1] += 1
    for K in sorted(rowsK):
        for tau in sorted(rowsK[K]):
            ok, n = rowsK[K][tau]
            print(f"  {K}  {tau:>7}   {rate(ok, n):>7}   {n:>4}")
    print("  tau_c(K) = the gap length at which recovery collapses; read off the first 0/n row.")
    return rowsK


# ---------------------------------------------------------------- continuity

def continuity():
    print("\n=== B. Matched-dose continuity: identical dose D=300 p-step-equivalents, 4 shapes ===")
    order = {"cont003": 0, "micro": 970, "bstart": 9700, "bend": 9700}
    got = defaultdict(lambda: [0, 0])
    for r in runs("continuity"):
        arm = r["run_id"].split("_q4_")[0]
        s = schedule(r)
        rescue = s[3] if s and s[3] is not None else 14000
        got[arm][0] += bool(emerged_after(r, rescue))
        got[arm][1] += 1
    print("  arm        max_gap   emerged      n")
    for arm in sorted(got, key=lambda a: order.get(a, 99999)):
        ok, n = got[arm]
        print(f"  {arm:<9} {order.get(arm, '?'):>8}   {rate(ok, n):>7}   {n:>4}")
    if "micro" in got and "bstart" in got:
        (m_ok, m_n), (b_ok, b_n) = got["micro"], got["bstart"]
        p = fisher_two_sided(m_ok, m_n - m_ok, b_ok, b_n - b_ok)
        print(f"  registered sharpest signature micro ({rate(m_ok, m_n)}) vs bstart "
              f"({rate(b_ok, b_n)}) at identical dose: Fisher p = {p:.4f}")
    return got


# ---------------------------------------------------------------- maintenance

def maintenance():
    print("\n=== C. Maintenance threshold: supply held THROUGH, no rescue — did it survive? ===")
    got = defaultdict(lambda: [0, 0])
    for d in ("maint", "thresh", "k2maint"):
        for r in runs(d):
            s = schedule(r)
            if not s or s[1] is not None:
                continue            # retention arms only (no rescue segment)
            man = r.get("manifest") if isinstance(r.get("manifest"), dict) else {}
            K = (man.get("task") or {}).get("K")
            got[(K, s[0])][0] += bool(held_at_end(r))
            got[(K, s[0])][1] += 1
    print("  K   p_during    held      n")
    for K, pd in sorted(got, key=lambda k: (k[0] or 0, k[1])):
        ok, n = got[(K, pd)]
        print(f"  {K}  {pd:>9}   {rate(ok, n):>6}   {n:>4}")
    return got


# ---------------------------------------------------------------- rescue statistics

def rescue_cells():
    """K=2 post-emergence forks keyed by (tau, p_during, p_rescue)."""
    cells = defaultdict(lambda: [0, 0])
    for d in ("k2post", "k2exp", "prestore"):
        for r in runs(d):
            s = schedule(r)
            if not s or s[3] is None:
                continue
            pd, pr, g0, r0 = s
            man = r.get("manifest") if isinstance(r.get("manifest"), dict) else {}
            if (man.get("task") or {}).get("K") != 2:
                continue
            fork_q = next((e.get("query_ctx") for e in r.get("evals", [])
                           if e["step"] == r.get("fork_step")), None)
            c = crit(r)
            if fork_q is None or c is None or fork_q < c:
                continue            # recovery question only: parent must be past crit at fork
            cells[(r0 - g0, pd, pr)][0] += bool(emerged_after(r, r0))
            cells[(r0 - g0, pd, pr)][1] += 1
    return cells


def rescue_stats():
    print("\n=== D. Rescue after a total gap (K=2, post-emergence forks) ===")
    cells = rescue_cells()
    print("  tau_dep  p_during  p_rescue   recovered      n")
    for key in sorted(cells):
        tau, pd, pr = key
        ok, n = cells[key]
        print(f"  {tau:>7}  {pd:>8}  {pr:>8}   {rate(ok, n):>9}   {n:>4}")

    def pool(pred):
        ok = n = 0
        for key, (o, m) in cells.items():
            if pred(*key):
                ok += o
                n += m
        return ok, n

    print("\n  DECLARED CONTRASTS (two-sided Fisher exact):")
    tests = [
        ("TRICKLE: p_during in {0.005,0.01,0.02} vs total gap, both then rescued at p=1",
         lambda t, pd, pr: t == 10000 and pd in (0.005, 0.01, 0.02) and pr == 1.0,
         lambda t, pd, pr: t == 10000 and pd == 0.0 and pr == 1.0),
        ("REVIVAL RATE THRESHOLD: p_rescue <= 0.05 vs p_rescue = 0.20 (tau=10000)",
         lambda t, pd, pr: t == 10000 and pd == 0.0 and pr is not None and pr <= 0.05,
         lambda t, pd, pr: t == 10000 and pd == 0.0 and pr == 0.20),
        ("SEVERITY x RATE at p_rescue=0.20: tau=2500 vs tau=10000",
         lambda t, pd, pr: t == 2500 and pd == 0.0 and pr == 0.20,
         lambda t, pd, pr: t == 10000 and pd == 0.0 and pr == 0.20),
        ("SEVERITY at full restore: tau=3000 vs tau=10000",
         lambda t, pd, pr: t == 3000 and pd == 0.0 and pr == 1.0,
         lambda t, pd, pr: t == 10000 and pd == 0.0 and pr == 1.0),
        ("POST-HOC (not registered): p_rescue=0.20 vs p_rescue=1.0 at tau=10000",
         lambda t, pd, pr: t == 10000 and pd == 0.0 and pr == 0.20,
         lambda t, pd, pr: t == 10000 and pd == 0.0 and pr == 1.0),
    ]
    for label, f1, f2 in tests:
        a, na = pool(f1)
        c, nc = pool(f2)
        if na == 0 or nc == 0:
            print(f"  - {label}: MISSING CELL (n={na} vs n={nc}) — not reportable")
            continue
        p = fisher_two_sided(a, na - a, c, nc - c)
        print(f"  - {label}\n      {rate(a, na)} vs {rate(c, nc)}   Fisher p = {p:.6f}")
    return cells


# ---------------------------------------------------------------- chi batteries

def chi_arms(d, split):
    """chi per (arm, parent) = gold_mass(pulse) - gold_mass(ctrl) at the matched last logit."""
    gm, prepulse = {}, {}
    for r in runs(d):
        rid = r["run_id"]
        key = split(rid)
        if key is None:
            continue
        arm, kind, parent = key
        lg = [e for e in r.get("evals", []) if "logit" in e and e["step"] > (r.get("fork_step") or 0)]
        if lg:
            gm[(arm, kind, parent)] = lg[-1]["logit"].get("gold_mass")
        fq = next((e.get("query_ctx") for e in r.get("evals", [])
                   if e["step"] == r.get("fork_step")), None)
        if fq is not None:
            prepulse[(arm, kind, parent)] = (fq, crit(r))
    out = defaultdict(list)
    guard = defaultdict(list)
    for (arm, kind, parent), v in gm.items():
        if kind != "pulse":
            continue
        ctrl = gm.get((arm, "ctrl", parent))
        if ctrl is None or v is None:
            continue
        out[arm].append(v - ctrl)
        fq = prepulse.get((arm, "pulse", parent))
        if fq and fq[1] is not None:
            guard[arm].append(fq[0] >= fq[1])
    return out, guard


def transplant():
    print("\n=== E. Transplant battery: where does foreclosure live? (chi per arm) ===")

    def split(rid):
        if not rid.startswith("tx_"):
            return None
        parts = rid.split("_")
        return parts[1], parts[2], "_".join(parts[3:])

    out, guard = chi_arms("transplant", split)
    full = mean_sd(out.get("full", []))[0]
    print("  arm      chi mean +/- sd (n)        pre-pulse above crit   % of full-swap chi")
    for arm in ("noop", "lower", "upper", "full", "revup"):
        if arm not in out:
            continue
        m, s, n = mean_sd(out[arm])
        g = guard.get(arm, [])
        frac = f"{100 * m / full:>6.1f}%" if full else "   n/a"
        print(f"  {arm:<7}  {m:+.4f} +/- {s:.4f} ({n})      {sum(g)}/{len(g)}            {frac}")
    lo, up, fu = out.get("lower", []), out.get("upper", []), out.get("full", [])
    if lo and up and fu:
        add = mean_sd(lo)[0] + mean_sd(up)[0]
        print(f"  additivity check: lower + upper = {add:+.4f} vs full {mean_sd(fu)[0]:+.4f} "
              f"({100 * add / mean_sd(fu)[0]:.1f}% of full) -> "
              f"{'SUB-additive' if add < mean_sd(fu)[0] else 'additive-or-more'}")
    return out


def symbreak():
    print("\n=== F. Symmetry breaking on foreclosed states (chi per arm x source step) ===")

    def split(rid):
        if not rid.startswith("sb"):
            return None
        parts = rid.split("_")
        return f"{parts[0]}:{parts[1]}", parts[2], "_".join(parts[3:])

    out, guard = chi_arms("symbreak", split)
    print("  state    arm      chi mean +/- sd (n)")
    for k in sorted(out):
        st, arm = k.split(":")
        m, s, n = mean_sd(out[k])
        print(f"  {st:<8} {arm:<7}  {m:+.4f} +/- {s:.4f} ({n})")
    return out


def main():
    tau_boundary()
    continuity()
    maintenance()
    rescue_stats()
    transplant()
    symbreak()
    print("\n(every count above is len() over run JSONs on disk; no number is carried from a "
          "prior draft, summary, or memory)")


if __name__ == "__main__":
    main()
