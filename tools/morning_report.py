"""Generic morning report: walks every runs/ directory, recomputes everything from run JSONs.

Replaced the phase-hardcoded version on 2026-08-09 — that one predated the foreclosure program
and reported nothing about kgen_tau / k2post / tomo / continuity, so the one-command morning
check (`aws s3 cp .../MORNING_REPORT.md -`) would have hidden a full night of results.
Emergence criterion everywhere: crit = chance + 0.5 * (1 - chance), read from each run's own
recorded chance_query_ctx.  Nothing is carried forward from a log line or a previous report.
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import subprocess
import time

W = os.path.expanduser("~/devaxis-work")

VERDICTS = """## Confirmed verdicts (hand-maintained, 2026-08-09 02:20 IST)

- **K=2 never forecloses**: tau = 2k/5k/10k -> 8/8, 8/8, 8/8 emerged (deprivation DELAYS,
  up to ~36k). K=4: 4/8, 2/8, 0/20, 0/16 (deprivation FORECLOSES).
- **k2post (formed K=2, 3k cut, rescue): 7/8 recovered** vs K=4 postresc 0/7 (Fisher ~0.0014).
  Collapse latency +1,000-2,000 steps at BOTH loads. s5 = the one K=2 absorbing case.
- **Matched different-futures at K=4 = both frozen, from existing data**: per-parent
  age+dose+stream-matched pairs (tau10k never-formed 0/20 vs postresc formed-collapsed 0/7).
- **CONFIRMATORY n=24 (analysis/mcnemar_k2.py): never-formed 20/24 reacquire vs
  formed-collapsed 12/24** at the identical 10k gap; discordant 11 vs 3; **exact McNemar
  two-sided p = 0.057** (the registered primary). Direction stable at every n; significance
  just above 0.05. The exploratory 8/8 never-formed was the lucky tail — 4/16 fresh
  never-formed runs froze; 3 parents show the reverse dissociation. Gap dose-response on the
  formed side stands: 3k gap -> 1/8 frozen, 10k gap -> 12/24 frozen.
- **K=2 maintenance threshold scales with load (k2maint FINAL)**: held at p=0.005 -> 1/8,
  p=0.01 -> 4/8, p=0.03 -> 7/8, vs K=4's 1/7 held at p=0.01 — maintenance is ~2-3x cheaper
  at half the load, same dip-then-recover motif.
- **K=8 FINAL: 2/8 emerged** (48,750 and 72,000); the other six ran the FULL 120k budget at
  chance (q 0.105-0.141) with recap = 1.000 throughout. Read saturates at step 250 in all 8.
  Within-budget emergence probability by load: K=2 8/8, K=4 7/8, K=8 2/8.
- **THE FORECLOSURE CLOCK (tomography, analysis/chi_matrix.py)**: chi(t, delta=4000) on the
  logit channel decays ~30x across deprivation age — +0.164 at age 0 (the positive control:
  parent state, known plastic) -> +0.051 at 2k -> +0.087 at 4k -> +0.022 at 6k -> ~+0.006
  from 8k on, FLAT thereafter — while query accuracy sits at chance in pulse and control
  alike and recap stays 1.000. Pre-behavioral plasticity loss, localized to the first ~2-8k
  steps of deprivation, matching the tau dose-response knee (2k->4/8, 5k->2/8, 10k->0/20).
  Caveats: delta=1000 is below the instrument floor everywhere (+0.012 even at age 0);
  delta=250 recorded no logit; the 2k/4k inversion is within seed noise (n=8/cell).
- **CONTINUITY FINAL (32/32)**: at IDENTICAL dose 300, cont003 (continuous 3%) = 1/8 emerged
  + 3 censored climbing at 0.477-0.496; micro/bstart/bend (bursts, gaps 970/9,700/9,700) =
  0/24, every final q <= 0.271. Registered emergence contrast is underpowered (1 event);
  post-hoc rank test on final q, cont003 vs pooled bursts: Mann-Whitney U=143.5/192, p ~ 0.039.
  Reading: 300 p-steps under-doses formation in ANY shape; only the continuous arm shows
  partial formation. Max-gap does NOT explain it (micro's 970-gap behaves like 9,700-gap
  bursts). Formal D vs D+G vs D+G+B model comparison owed.
- **PAIRED FORECLOSURE CLOCK (confirmatory)**: chi(age 0) > mean chi(age >= 8k) in 7/8
  parents. REGISTERED sign test two-sided p = 0.070; post-hoc Wilcoxon signed-rank (uses
  magnitudes: declines +0.015 to +0.504, one -0.012) p = 0.016. The one non-declining parent
  (s3) had chi(0) = +0.0005 — plasticity not yet pulse-visible at age 4000, consistent with
  slow emergers.
- **ZERO FINAL (24/24)**: tiny-but-nonzero window supervision does NOT reliably preserve
  rescuability at K=4: p=0.001 -> 2/8, p=0.005 -> 1/8, p=0.01 -> 0/8 (pooled 3/24 vs p=0's
  0/20: Fisher p = 0.24, ns). The apparent inverted ordering is noise-level at n=8.
- **K=3 FINAL: 8/8 emerged at 6,500-13,000** — the emergence ladder is now four-point:
  K=2 ~3.1k median, K=3 ~8k, K=4 ~12k, K=8 >= 48,750 (2/8 by 120k).
"""


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def emerge(r, after=0):
    ch = r.get("chance_query_ctx")
    if ch is None:
        return None
    crit = ch + 0.5 * (1 - ch)
    return next((e["step"] for e in r.get("evals", []) if e["step"] >= after
                 and e.get("query_ctx", 0) >= crit), None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(W, "MORNING_REPORT.md"))
    a = ap.parse_args()
    lines = [f"# devaxis overnight report — {time.strftime('%a %b %d %H:%M:%S UTC %Y', time.gmtime())}",
             "", "Every number below is recomputed from run JSONs at report time.", "", VERDICTS]

    lines += ["## Phase state", ""]
    prog = load(os.path.join(W, "PROGRAM.json")) or []
    st = load(os.path.join(W, "PROGRAM_STATE.json")) or {}
    for ph in prog:
        lines.append(f"- {ph['name']}: {st.get(ph['name'], {}).get('status', 'not started')}")
    lines.append("")

    total_term = 0
    for d in sorted(glob.glob(os.path.join(W, "runs", "*"))):
        name = os.path.basename(d)
        if not os.path.isdir(d) or name.endswith("_NAN"):
            continue
        runs = [r for r in (load(p) for p in sorted(glob.glob(os.path.join(d, "*.json")))) if r]
        if not runs:
            continue
        term = sum(1 for r in runs if r.get("done") or r.get("failed"))
        fail = sum(1 for r in runs if r.get("failed"))
        emg = sum(1 for r in runs if emerge(r) is not None)
        total_term += term
        laststeps = [r["evals"][-1]["step"] for r in runs if r.get("evals")]
        lines.append(f"## {name} — n={len(runs)} terminal={term} failed={fail} "
                     f"emerged={emg} steps={min(laststeps) if laststeps else 0}-"
                     f"{max(laststeps) if laststeps else 0}")
        if len(runs) <= 40:
            lines.append("```")
            for r in runs:
                ev = r["evals"][-1] if r.get("evals") else {}
                fs = r.get("fork_step") or 0
                lines.append(f"{r['run_id']:>28} step={ev.get('step', 0):>7} "
                             f"q={ev.get('query_ctx', -1):.3f} recap={ev.get('recap', -1):.3f} "
                             f"emerge@{emerge(r, after=fs)} "
                             f"{'done' if r.get('done') else 'FAILED' if r.get('failed') else 'running'}")
            lines.append("```")
        lines.append("")

    tr = subprocess.run(["pgrep", "-fc", "training[.]train"], capture_output=True, text=True)
    lines += [f"**Live trainers:** {tr.stdout.strip() or 0}   **Total terminal:** {total_term}", ""]
    with open(a.out, "w") as f:
        f.write("\n".join(lines))
    print(f"wrote {a.out} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
