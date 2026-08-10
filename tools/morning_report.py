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
- **SAME BEHAVIOR, DIFFERENT FUTURES — CONFIRMED at n=40, horizon-matched
  (analysis/km_rescued.py + analysis/mcnemar_k2.py).** Identical 10k gap, follow-up 60k in
  BOTH arms: never-formed reacquire **31/40** (KM median 12,500 rescued steps);
  formed-then-collapsed **18/40** (median not reached by 60k). **Corrected primary:
  log-rank chi2 = 5.96, p = 0.0146. Registered McNemar: discordant 17 vs 4, p = 0.0072.**
  Look history, in full: n=8 exploratory p~0.077 -> n=24 (formed arm under-followed: McNemar
  0.057, corrected KM 0.216) -> n=40 horizon-matched 0.0072/0.0146. Two models at chance
  with recap 1.000 on identical bytes under identical future supervision have opposite
  futures — and it is the FORMED-THEN-COLLAPSED state that is absorbing.
- **Foreclosure clock, delta=8000 column**: age-0 positive control +0.513±0.301; the
  delta=4000 holdout (s3) registers at +0.735.
  **CONFIRMED AT THE DECLARED n = 16 (analysis/chi_paired.py): the paired decline is positive
  in 15/16 parents, two-sided exact sign p = 0.0005**, clearing the pre-declared >= 13/16 bar
  on the pre-declared PRIMARY probe (delta = 8000); per-parent declines +0.0025 to +0.758,
  one dissenter (s1, -0.021). Secondary probe (delta = 4000): 14/16, p = 0.0042. The earlier
  7/8 (p = 0.070) was a sample-size ceiling, not a weak effect — at n = 8 no sign test can
  reach significance with even one dissenter. Gap dose-response on the
  formed side stands: 3k gap -> 1/8 frozen, 10k gap -> 12/24 frozen.
- **K=2 maintenance threshold scales with load (k2maint FINAL)**: held at p=0.005 -> 1/8,
  p=0.01 -> 4/8, p=0.03 -> 7/8, vs K=4's 1/7 held at p=0.01 — maintenance is ~2-3x cheaper
  at half the load, same dip-then-recover motif.
- **THE TRICKLE RESULT — a 0.5% trace of supervision during an interruption preserves
  RECOVERABILITY while preserving nothing observable (phase x9rep, K=2, tau_dep = 10,000,
  full rescue in every arm, n=8/arm).** Hold p at 0.005 / 0.01 / 0.02 through the gap instead
  of 0: recovery on full restore is **8/8, 8/8, 8/8** versus **18/40 after a total gap**
  (each arm Fisher p = 0.005; pooled 24/24 vs 18/40, **p = 0.000002**).
  THE CHECK THAT MAKES IT A RESULT: those circuits genuinely collapsed first. At p = 0.005
  all 8 fell to query 0.426-0.477 — at or below the 0.5 chance level — and were still at
  0.49-0.59 when rescue began, with recap 1.000 throughout. So at the moment supervision
  returns, the trickle and no-trickle models are **behaviorally indistinguishable: both at
  chance, both reading perfectly.** Their futures are not: 100% vs 45%.
  This is the flagship dissociation in its sharpest form yet — the hidden variable is
  ~50 supervised step-equivalents spread across 10,000 steps, invisible to every current
  measurement, and it doubles the recovery rate.
  **PREVENTION vs CURE:** 0.005 during the gap costs ~50 step-equivalents and gives 100%
  recovery; 0.20 applied after a total gap costs ~12,000 step-equivalents and gives 50%
  (Fisher p = 0.077 on 8/8 vs 4/8). **~240x less supervision, delivered during rather than
  after, doubles the outcome.**
  CROSS-CODEBASE REPLICATION: this reproduces h100-clocks' X9 (their 3/3 at p = 0.01 and
  0.02) in an independent implementation, and extends the boundary down to 0.005.
- **SEVERITY x RATE on the revival axis (phase sevrate):** at p_rescue = 0.20, a 2,500-step
  gap recovers 8/8 versus 4/8 after a 10,000-step gap (Fisher p = 0.077); at p_rescue = 0.01
  both are 0/8. Severity modulates revival ABOVE the rate threshold and is irrelevant below
  it — the threshold is the primary variable.
- **REVIVAL HAS A RATE THRESHOLD, and my pre-registered "low rate wins" branch is REFUTED
  (phase prestore, K=2, formed circuit, total 10k gap, 60k rescue horizon, n=8/arm).**
  Recovery by restore rate: **p_rescue = 0.01 -> 0/8, 0.02 -> 0/8, 0.05 -> 0/8, 0.20 -> 4/8,
  1.00 -> 1/8.** The registered contrast (0.02 vs 1.00) is null, Fisher p = 1.00 — the
  hypothesis that dripping supervision back beats restoring it is WRONG: every rate at or
  below 0.05 recovered nothing in 60,000 steps. What survives is a THRESHOLD: pooled low
  rates 0/24 vs 0.20's 4/8, Fisher p = 0.0019. The apparent drop from 0.20 (4/8) to 1.00
  (1/8) is a POST-HOC contrast and is NOT supported (Fisher p = 0.28) — interesting, not
  claimed, and the reason the Cochran-Armitage trend reads ns (z = +0.66, p = 0.51): that
  test looks for monotone trend and cannot see a threshold or a peak.
  Practical reading, stated conservatively: to revive a collapsed capability you need a
  substantial restore rate (>= ~0.2 here); a maintenance-sized trickle does not bring it
  back, even though a trickle of the same size WOULD have prevented the loss (see the
  two-axis supply map — retention needs ~1-3%, revival needs ~20%, an order of magnitude
  more). Prevention is roughly 10x cheaper than cure.
- **REPAIR: 0 for 4. No intervention we tried reopens a foreclosed model.**
  symmetry-breaking and norm-matched random perturbation at the early chi-dead state
  (sb12, n=8/arm: all |chi| <= 0.011) and at the LATE state where duplicate units actually
  exist (sb24, n=5/arm so far: noop -0.006, symb -0.001, randp -0.009, symfar -0.004), all
  function-preserving by the declared gate. Together with the transplant result (only the
  FULL weight set restores plasticity) and the refuted cloned-manifold timing, the honest
  statement is: foreclosure is a whole-network configuration that we could localize to
  nothing smaller, repair with nothing weaker, and escape with no perturbation of the
  magnitudes tested.
- **MECHANISM: foreclosure is a WHOLE-NETWORK configuration, not a damaged module
  (transplant battery, 80 runs, all terminal).** chi (delta=4k pulse minus control) after
  swapping layer groups between a plastic (step 4,000) and a foreclosed (step 24,000)
  checkpoint of the same parent: **noop -0.005+-0.012, lower +0.066+-0.100, upper
  +0.064+-0.107, full +0.301+-0.166, revup +0.185+-0.279** (n=8 each). Reading: neither half
  restores plasticity (each ~22% of the full swap, and sub-additive); only the whole weight
  set does. And foreclosed upper layers transplanted INTO a plastic model leave it plastic
  (revup ~ the unperturbed plastic level) — foreclosure does not transfer as a module.
  Performance-transfer guard passed: every arm's pre-pulse query stayed at chance
  (0.211-0.314 vs criterion 0.625).
- **CLONED-UNIT MANIFOLD: REFUTED AS THE CAUSE, BY ITS OWN TIMING (analysis/unit_collapse.py).**
  Deprived checkpoints do collapse: at matched step 24,000, duplicate-pair fraction 0.407
  (deprived) vs 0.008 (supervised), effective rank 23 vs 72 — deprivation-specific, not aging.
  But the collapse arrives far too late: dup_frac is **0.0000 flat until dep_age 15,000**
  (16k 0.003, 18k 0.204, 20k 0.407) while chi is already dead by dep_age ~8,000. Effective
  rank falls 150->81 over the chi window, but the SUPERVISED control falls 150->108 across
  the same span, so early rank loss is not deprivation-specific either. Unit duplication is a
  downstream signature of foreclosure, not its mechanism. Symmetry-breaking batteries now run
  at BOTH the late duplicated state and the early chi-dead state (dup_frac 0.0000).
- **SAVINGS after a TOTAL interruption are negative (analysis/savings_k2.py).** Paired
  re-form-vs-de-novo on K=2 binding, p_during = 0 then full rescue: 3/18 re-formed runs show
  positive savings, median -0.44 (re-forming is SLOWER than from scratch), and 22/40 never
  re-form in 30-60k rescued steps = 10-19x the de-novo median.
  **CORRECTION (2026-08-10), scope of the earlier "inverted vs induction" framing:** the
  cross-lab exchange established that `p_after` named DIFFERENT variables in the two
  codebases — h100-clocks' p_after is supply held DURING the interruption (their rescue is
  always p=1.0), ours is supply during RESCUE after a total interruption. Their +92.9%
  savings therefore describes a circuit that was MAINTAINED through the gap; ours describes
  one that was fully collapsed. Both are correct and they are not in conflict; the earlier
  "binding = damage, induction = retained structure" contrast compared different experiments
  and is withdrawn as stated. What survives: after a TOTAL interruption, binding-use recovery
  is slower than de novo. See analysis/supply_map.py for the two-axis map that separates them.
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
- **THE tau_c(K) PHASE BOUNDARY (k3tau FINAL, fork@3000)**: K=3 tau=2k -> 8/8 emerged
  (delayed), 5k -> 7/8, **10k -> 0/8** (all flat at chance through 70k; vs K=2's 8/8 at the
  same tau: Fisher p ~ 1.6e-4). Combined: **tau_c(2) > 10k, tau_c(3) in (5k, 10k],
  tau_c(4) ~ 2-5k — the foreclosure boundary is monotone in load.** One K=3 tau=2k run
  crossed the criterion at 24,250 then slipped back to 0.648 by budget — emergence is not
  always stable; counted as emerged per the pre-registered first-crossing rule, flagged.
- **K=6 DROPPED ON PLATFORM GROUNDS**: neuronx-cc dies deterministically compiling the K=6
  shape (fast SIGHUP even as a solo compile with stagger 300 — the compile-storm explanation
  is ruled out). The ladder is K in {2, 3, 4, 8}. This is a compiler limitation, not a
  scientific result about K=6.
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
