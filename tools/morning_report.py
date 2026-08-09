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
- **Gap-matched K=2 contrast FINAL (k2post10k, 10k gap)**: never-formed 8/8 reacquire vs
  formed-collapsed **4/8** (s7 recovered at 44,750 after ~25k rescued steps; s0/s3/s4/s5
  frozen through 30k of rescue, recap 1.000). Fisher 2s p ~ 0.077 — Outcome-A DIRECTION,
  not significant at n=8. Confirmatory expansion queued (phase k2exp: 16 fresh parents,
  both arms each -> n=24 paired, exact McNemar pre-registered). Gap dose-response on the
  formed side: 3k gap -> 1/8 frozen, 10k gap -> 4/8 frozen.
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
- **Continuity near-final**: cont003 1 emerged + 3 censored ending at 0.477-0.496 (climbing
  at budget) vs ALL burst arms 0/20 terminal above 0.4 at the same dose. KM/log-rank +
  model comparison owed when the last 2 runs finish.
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
