# devaxis overnight report — Mon Aug 10 16:51:22 UTC 2026

Every number below is recomputed from run JSONs at report time.

## Confirmed verdicts (hand-maintained, 2026-08-09 02:20 IST)

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

## Phase state

- window: ALREADY_COMPLETE
- mech: ALREADY_COMPLETE
- wd0: ALREADY_COMPLETE
- dd10: ALREADY_COMPLETE
- postem: ALREADY_COMPLETE
- maint: OK
- early: ALREADY_COMPLETE
- thresh: OK
- kgen: OK
- continuity: OK
- tomopulse: OK
- zero: OK
- k36: DRAINING
- k2maint: OK
- k2expbase: OK
- k2exparms: OK
- pulse: OK
- chi8k: OK
- k2exp2base: OK
- k2exp2arms: OK
- k4xbase: OK
- txcanary: OK
- txbattery: OK
- sb12: OK
- prestore: OK
- sb24: OK
- x9rep: OK
- sevrate: OK
- k4xtraj: OK
- k4xpulse: OK

## bench — n=1 terminal=0 failed=0 emerged=0 steps=250-250
```
                 bench_n1_c0 step=    250 q=0.000 recap=0.000 emerge@None running
```

## branch — n=21 terminal=21 failed=0 emerged=7 steps=9250-60000
```
            br_deprive_q4_s1 step=  60000 q=0.281 recap=1.000 emerge@None done
            br_deprive_q4_s2 step=  60000 q=0.266 recap=1.000 emerge@None done
            br_deprive_q4_s3 step=  60000 q=0.238 recap=1.000 emerge@None done
            br_deprive_q4_s4 step=  60000 q=0.248 recap=1.000 emerge@None done
            br_deprive_q4_s5 step=  60000 q=0.254 recap=1.000 emerge@None done
            br_deprive_q4_s6 step=  60000 q=0.230 recap=1.000 emerge@None done
            br_deprive_q4_s7 step=  60000 q=0.242 recap=1.000 emerge@None done
               br_noop_q4_s1 step=  16000 q=0.992 recap=1.000 emerge@15500 done
               br_noop_q4_s2 step=   9500 q=0.949 recap=1.000 emerge@8500 done
               br_noop_q4_s3 step=  11000 q=0.908 recap=1.000 emerge@9750 done
               br_noop_q4_s4 step=  11750 q=0.930 recap=1.000 emerge@10500 done
               br_noop_q4_s5 step=   9250 q=0.953 recap=1.000 emerge@7000 done
               br_noop_q4_s6 step=  33750 q=0.957 recap=1.000 emerge@31750 done
               br_noop_q4_s7 step=  10250 q=0.938 recap=1.000 emerge@8750 done
          br_rescue10k_q4_s1 step=  60000 q=0.244 recap=1.000 emerge@None done
          br_rescue10k_q4_s2 step=  60000 q=0.281 recap=1.000 emerge@None done
          br_rescue10k_q4_s3 step=  60000 q=0.234 recap=1.000 emerge@None done
          br_rescue10k_q4_s4 step=  60000 q=0.289 recap=1.000 emerge@None done
          br_rescue10k_q4_s5 step=  60000 q=0.264 recap=1.000 emerge@None done
          br_rescue10k_q4_s6 step=  60000 q=0.262 recap=1.000 emerge@None done
          br_rescue10k_q4_s7 step=  60000 q=0.268 recap=1.000 emerge@None done
```

## continuity — n=32 terminal=32 failed=0 emerged=1 steps=33000-70000
```
                  bend_q4_s0 step=  70000 q=0.250 recap=1.000 emerge@None done
                  bend_q4_s1 step=  70000 q=0.252 recap=1.000 emerge@None done
                  bend_q4_s2 step=  70000 q=0.209 recap=1.000 emerge@None done
                  bend_q4_s3 step=  70000 q=0.236 recap=1.000 emerge@None done
                  bend_q4_s4 step=  70000 q=0.236 recap=1.000 emerge@None done
                  bend_q4_s5 step=  70000 q=0.271 recap=1.000 emerge@None done
                  bend_q4_s6 step=  70000 q=0.270 recap=1.000 emerge@None done
                  bend_q4_s7 step=  70000 q=0.230 recap=1.000 emerge@None done
                bstart_q4_s0 step=  70000 q=0.250 recap=1.000 emerge@None done
                bstart_q4_s1 step=  70000 q=0.230 recap=1.000 emerge@None done
                bstart_q4_s2 step=  70000 q=0.242 recap=1.000 emerge@None done
                bstart_q4_s3 step=  70000 q=0.234 recap=1.000 emerge@None done
                bstart_q4_s4 step=  70000 q=0.262 recap=1.000 emerge@None done
                bstart_q4_s5 step=  70000 q=0.256 recap=1.000 emerge@None done
                bstart_q4_s6 step=  70000 q=0.246 recap=1.000 emerge@None done
                bstart_q4_s7 step=  70000 q=0.242 recap=1.000 emerge@None done
               cont003_q4_s0 step=  70000 q=0.486 recap=1.000 emerge@None done
               cont003_q4_s1 step=  70000 q=0.477 recap=1.000 emerge@None done
               cont003_q4_s2 step=  70000 q=0.496 recap=1.000 emerge@None done
               cont003_q4_s3 step=  70000 q=0.242 recap=1.000 emerge@None done
               cont003_q4_s4 step=  33000 q=0.953 recap=1.000 emerge@32000 done
               cont003_q4_s5 step=  70000 q=0.258 recap=1.000 emerge@None done
               cont003_q4_s6 step=  70000 q=0.252 recap=1.000 emerge@None done
               cont003_q4_s7 step=  70000 q=0.213 recap=1.000 emerge@None done
                 micro_q4_s0 step=  70000 q=0.268 recap=1.000 emerge@None done
                 micro_q4_s1 step=  70000 q=0.236 recap=1.000 emerge@None done
                 micro_q4_s2 step=  70000 q=0.234 recap=1.000 emerge@None done
                 micro_q4_s3 step=  70000 q=0.252 recap=1.000 emerge@None done
                 micro_q4_s4 step=  70000 q=0.221 recap=1.000 emerge@None done
                 micro_q4_s5 step=  70000 q=0.270 recap=1.000 emerge@None done
                 micro_q4_s6 step=  70000 q=0.250 recap=1.000 emerge@None done
                 micro_q4_s7 step=  70000 q=0.242 recap=1.000 emerge@None done
```

## dd10 — n=11 terminal=11 failed=0 emerged=3 steps=34000-42000
```
           dd10_s12000_q4_s0 step=  42000 q=0.520 recap=1.000 emerge@None done
           dd10_s12000_q4_s1 step=  42000 q=0.471 recap=1.000 emerge@None done
           dd10_s12000_q4_s6 step=  42000 q=0.516 recap=1.000 emerge@None done
            dd10_s4000_q4_s0 step=  34000 q=0.496 recap=1.000 emerge@None done
            dd10_s4000_q4_s1 step=  34000 q=0.998 recap=1.000 emerge@9500 done
            dd10_s4000_q4_s2 step=  34000 q=0.998 recap=1.000 emerge@6750 done
            dd10_s4000_q4_s3 step=  34000 q=0.998 recap=1.000 emerge@8000 done
            dd10_s4000_q4_s4 step=  34000 q=0.248 recap=1.000 emerge@None done
            dd10_s4000_q4_s5 step=  34000 q=0.244 recap=1.000 emerge@None done
            dd10_s4000_q4_s6 step=  34000 q=0.510 recap=1.000 emerge@None done
            dd10_s4000_q4_s7 step=  34000 q=0.447 recap=1.000 emerge@None done
```

## early — n=24 terminal=24 failed=0 emerged=1 steps=46500-80000
```
             early1000_q4_s0 step=  80000 q=0.254 recap=1.000 emerge@None done
             early1000_q4_s1 step=  80000 q=0.236 recap=1.000 emerge@None done
             early1000_q4_s2 step=  46500 q=0.916 recap=1.000 emerge@44500 done
             early1000_q4_s3 step=  80000 q=0.250 recap=1.000 emerge@None done
             early1000_q4_s4 step=  80000 q=0.211 recap=1.000 emerge@None done
             early1000_q4_s5 step=  80000 q=0.232 recap=1.000 emerge@None done
             early1000_q4_s6 step=  80000 q=0.244 recap=1.000 emerge@None done
             early1000_q4_s7 step=  80000 q=0.281 recap=1.000 emerge@None done
             early2000_q4_s0 step=  80000 q=0.260 recap=1.000 emerge@None done
             early2000_q4_s1 step=  80000 q=0.240 recap=1.000 emerge@None done
             early2000_q4_s2 step=  80000 q=0.260 recap=1.000 emerge@None done
             early2000_q4_s3 step=  80000 q=0.256 recap=1.000 emerge@None done
             early2000_q4_s4 step=  80000 q=0.275 recap=1.000 emerge@None done
             early2000_q4_s5 step=  80000 q=0.262 recap=1.000 emerge@None done
             early2000_q4_s6 step=  80000 q=0.223 recap=1.000 emerge@None done
             early2000_q4_s7 step=  80000 q=0.254 recap=1.000 emerge@None done
             early3000_q4_s0 step=  80000 q=0.268 recap=1.000 emerge@None done
             early3000_q4_s1 step=  80000 q=0.246 recap=1.000 emerge@None done
             early3000_q4_s2 step=  80000 q=0.252 recap=1.000 emerge@None done
             early3000_q4_s3 step=  80000 q=0.254 recap=1.000 emerge@None done
             early3000_q4_s4 step=  80000 q=0.229 recap=1.000 emerge@None done
             early3000_q4_s5 step=  80000 q=0.248 recap=1.000 emerge@None done
             early3000_q4_s6 step=  80000 q=0.242 recap=1.000 emerge@None done
             early3000_q4_s7 step=  80000 q=0.277 recap=1.000 emerge@None done
```

## factorial — n=57 terminal=57 failed=0 emerged=46 steps=2000-120000

## factorial_v1_aborted — n=32 terminal=30 failed=30 emerged=0 steps=500-500
```
      dd_exact_long_fixed_s0 step=    500 q=0.000 recap=0.000 emerge@None FAILED
      dd_exact_long_fixed_s1 step=    500 q=0.000 recap=0.000 emerge@None FAILED
      dd_exact_long_fixed_s2 step=    500 q=0.000 recap=0.000 emerge@None FAILED
  dd_exact_long_scrambled_s0 step=    500 q=0.000 recap=0.000 emerge@None FAILED
  dd_exact_long_scrambled_s1 step=    500 q=0.000 recap=0.000 emerge@None FAILED
  dd_exact_long_scrambled_s2 step=    500 q=0.000 recap=0.000 emerge@None FAILED
     dd_exact_short_fixed_s0 step=    500 q=0.000 recap=0.000 emerge@None FAILED
     dd_exact_short_fixed_s1 step=    500 q=0.000 recap=0.000 emerge@None FAILED
     dd_exact_short_fixed_s2 step=    500 q=0.000 recap=0.000 emerge@None FAILED
 dd_exact_short_scrambled_s0 step=    500 q=0.000 recap=0.000 emerge@None FAILED
 dd_exact_short_scrambled_s1 step=    500 q=0.000 recap=0.000 emerge@None FAILED
 dd_exact_short_scrambled_s2 step=    500 q=0.000 recap=0.000 emerge@None FAILED
 dd_paraphrase_long_fixed_s0 step=    500 q=0.000 recap=0.000 emerge@None FAILED
 dd_paraphrase_long_fixed_s1 step=    500 q=0.000 recap=0.000 emerge@None FAILED
 dd_paraphrase_long_fixed_s2 step=    500 q=0.000 recap=0.000 emerge@None FAILED
dd_paraphrase_long_scrambled_s0 step=    500 q=0.000 recap=0.000 emerge@None FAILED
dd_paraphrase_long_scrambled_s1 step=    500 q=0.000 recap=0.000 emerge@None FAILED
dd_paraphrase_long_scrambled_s2 step=    500 q=0.000 recap=0.000 emerge@None FAILED
dd_paraphrase_short_fixed_s0 step=    500 q=0.000 recap=0.000 emerge@None FAILED
dd_paraphrase_short_fixed_s1 step=    500 q=0.000 recap=0.000 emerge@None FAILED
dd_paraphrase_short_fixed_s2 step=    500 q=0.000 recap=0.000 emerge@None running
dd_paraphrase_short_scrambled_s0 step=    500 q=0.000 recap=0.000 emerge@None FAILED
dd_paraphrase_short_scrambled_s1 step=    500 q=0.000 recap=0.000 emerge@None FAILED
dd_paraphrase_short_scrambled_s2 step=    500 q=0.000 recap=0.000 emerge@None FAILED
                       q4_s0 step=    500 q=0.000 recap=0.000 emerge@None FAILED
                       q4_s1 step=    500 q=0.000 recap=0.000 emerge@None running
                       q4_s2 step=    500 q=0.000 recap=0.000 emerge@None FAILED
                       q4_s3 step=    500 q=0.000 recap=0.000 emerge@None FAILED
                       q4_s4 step=    500 q=0.000 recap=0.000 emerge@None FAILED
                       q4_s5 step=    500 q=0.000 recap=0.000 emerge@None FAILED
                       q4_s6 step=    500 q=0.000 recap=0.000 emerge@None FAILED
                       q4_s7 step=    500 q=0.000 recap=0.000 emerge@None FAILED
```

## k2exp — n=64 terminal=64 failed=0 emerged=55 steps=13750-74000

## k2maint — n=24 terminal=24 failed=0 emerged=24 steps=32000-39500
```
              k2m0p005_k2_s0 step=  32750 q=0.504 recap=1.000 emerge@2750 done
              k2m0p005_k2_s1 step=  32750 q=0.547 recap=1.000 emerge@2750 done
              k2m0p005_k2_s2 step=  34500 q=0.482 recap=1.000 emerge@4500 done
              k2m0p005_k2_s3 step=  32250 q=0.859 recap=1.000 emerge@2250 done
              k2m0p005_k2_s4 step=  32000 q=0.504 recap=1.000 emerge@2000 done
              k2m0p005_k2_s5 step=  35750 q=0.492 recap=1.000 emerge@5750 done
              k2m0p005_k2_s6 step=  34000 q=0.480 recap=1.000 emerge@4000 done
              k2m0p005_k2_s7 step=  39500 q=0.500 recap=1.000 emerge@9500 done
               k2m0p01_k2_s0 step=  32750 q=0.447 recap=1.000 emerge@2750 done
               k2m0p01_k2_s1 step=  32750 q=0.928 recap=1.000 emerge@2750 done
               k2m0p01_k2_s2 step=  34500 q=0.533 recap=1.000 emerge@4500 done
               k2m0p01_k2_s3 step=  32250 q=0.865 recap=1.000 emerge@2250 done
               k2m0p01_k2_s4 step=  32000 q=0.988 recap=1.000 emerge@2000 done
               k2m0p01_k2_s5 step=  35750 q=0.984 recap=1.000 emerge@5750 done
               k2m0p01_k2_s6 step=  34000 q=0.490 recap=1.000 emerge@4000 done
               k2m0p01_k2_s7 step=  39500 q=0.486 recap=1.000 emerge@9500 done
               k2m0p03_k2_s0 step=  32750 q=0.975 recap=1.000 emerge@2750 done
               k2m0p03_k2_s1 step=  32750 q=0.992 recap=1.000 emerge@2750 done
               k2m0p03_k2_s2 step=  34500 q=0.943 recap=1.000 emerge@4500 done
               k2m0p03_k2_s3 step=  32250 q=0.988 recap=1.000 emerge@2250 done
               k2m0p03_k2_s4 step=  32000 q=0.959 recap=1.000 emerge@2000 done
               k2m0p03_k2_s5 step=  35750 q=0.988 recap=1.000 emerge@5750 done
               k2m0p03_k2_s6 step=  34000 q=0.934 recap=1.000 emerge@4000 done
               k2m0p03_k2_s7 step=  39500 q=0.506 recap=1.000 emerge@9500 done
```

## k2post — n=16 terminal=16 failed=0 emerged=16 steps=35000-49500
```
                k2post_k2_s0 step=  35750 q=1.000 recap=1.000 emerge@2750 done
                k2post_k2_s1 step=  35750 q=1.000 recap=1.000 emerge@2750 done
                k2post_k2_s2 step=  37500 q=1.000 recap=1.000 emerge@4500 done
                k2post_k2_s3 step=  35250 q=1.000 recap=1.000 emerge@2250 done
                k2post_k2_s4 step=  35000 q=1.000 recap=1.000 emerge@2000 done
                k2post_k2_s5 step=  38750 q=0.512 recap=1.000 emerge@5750 done
                k2post_k2_s6 step=  37000 q=1.000 recap=1.000 emerge@4000 done
                k2post_k2_s7 step=  42500 q=1.000 recap=1.000 emerge@9500 done
          k2postd10000_k2_s0 step=  42750 q=0.500 recap=1.000 emerge@2750 done
          k2postd10000_k2_s1 step=  42750 q=1.000 recap=1.000 emerge@2750 done
          k2postd10000_k2_s2 step=  44500 q=1.000 recap=1.000 emerge@4500 done
          k2postd10000_k2_s3 step=  42250 q=0.475 recap=1.000 emerge@2250 done
          k2postd10000_k2_s4 step=  42000 q=0.516 recap=1.000 emerge@2000 done
          k2postd10000_k2_s5 step=  45750 q=0.494 recap=1.000 emerge@5750 done
          k2postd10000_k2_s6 step=  44000 q=0.998 recap=1.000 emerge@4000 done
          k2postd10000_k2_s7 step=  49500 q=1.000 recap=1.000 emerge@9500 done
```

## k3tau — n=24 terminal=24 failed=0 emerged=15 steps=8500-70000
```
            k3tau10000_k3_s0 step=  70000 q=0.303 recap=1.000 emerge@None done
            k3tau10000_k3_s1 step=  70000 q=0.359 recap=1.000 emerge@None done
            k3tau10000_k3_s2 step=  70000 q=0.336 recap=1.000 emerge@None done
            k3tau10000_k3_s3 step=  70000 q=0.357 recap=1.000 emerge@None done
            k3tau10000_k3_s4 step=  70000 q=0.291 recap=1.000 emerge@None done
            k3tau10000_k3_s5 step=  70000 q=0.348 recap=1.000 emerge@None done
            k3tau10000_k3_s6 step=  70000 q=0.320 recap=1.000 emerge@None done
            k3tau10000_k3_s7 step=  70000 q=0.352 recap=1.000 emerge@None done
             k3tau2000_k3_s0 step=  18250 q=0.975 recap=1.000 emerge@18000 done
             k3tau2000_k3_s1 step=  11000 q=0.912 recap=1.000 emerge@9750 done
             k3tau2000_k3_s2 step=  12000 q=0.953 recap=1.000 emerge@11000 done
             k3tau2000_k3_s3 step=  70000 q=0.648 recap=1.000 emerge@24250 done
             k3tau2000_k3_s4 step=   8500 q=0.996 recap=1.000 emerge@7750 done
             k3tau2000_k3_s5 step=  18750 q=1.000 recap=1.000 emerge@6750 done
             k3tau2000_k3_s6 step=  11750 q=0.934 recap=1.000 emerge@9500 done
             k3tau2000_k3_s7 step=  15000 q=0.908 recap=1.000 emerge@10000 done
             k3tau5000_k3_s0 step=  31500 q=0.953 recap=1.000 emerge@30250 done
             k3tau5000_k3_s1 step=  14250 q=0.988 recap=1.000 emerge@12250 done
             k3tau5000_k3_s2 step=  34250 q=0.920 recap=1.000 emerge@33500 done
             k3tau5000_k3_s3 step=  18750 q=0.920 recap=1.000 emerge@18000 done
             k3tau5000_k3_s4 step=  14750 q=0.986 recap=1.000 emerge@11750 done
             k3tau5000_k3_s5 step=  25750 q=0.971 recap=1.000 emerge@12500 done
             k3tau5000_k3_s6 step=  18000 q=0.996 recap=1.000 emerge@16500 done
             k3tau5000_k3_s7 step=  70000 q=0.348 recap=1.000 emerge@None done
```

## kgen — n=64 terminal=56 failed=0 emerged=50 steps=0-120000

## kgen_tau — n=24 terminal=24 failed=0 emerged=24 steps=3750-47500
```
            k2tau10000_k2_s0 step=  46750 q=0.947 recap=1.000 emerge@46000 done
            k2tau10000_k2_s1 step=  15750 q=0.938 recap=1.000 emerge@14750 done
            k2tau10000_k2_s2 step=  20250 q=0.969 recap=1.000 emerge@20000 done
            k2tau10000_k2_s3 step=  21000 q=0.926 recap=1.000 emerge@20250 done
            k2tau10000_k2_s4 step=  28750 q=0.973 recap=1.000 emerge@28250 done
            k2tau10000_k2_s5 step=  34250 q=0.996 recap=1.000 emerge@33500 done
            k2tau10000_k2_s6 step=  47500 q=0.980 recap=1.000 emerge@47000 done
            k2tau10000_k2_s7 step=  22250 q=0.967 recap=1.000 emerge@21750 done
             k2tau2000_k2_s0 step=   4000 q=0.992 recap=1.000 emerge@3500 done
             k2tau2000_k2_s1 step=   5000 q=0.994 recap=1.000 emerge@4500 done
             k2tau2000_k2_s2 step=   5250 q=0.980 recap=1.000 emerge@5000 done
             k2tau2000_k2_s3 step=   4000 q=0.990 recap=1.000 emerge@3750 done
             k2tau2000_k2_s4 step=   3750 q=1.000 recap=1.000 emerge@3500 done
             k2tau2000_k2_s5 step=   3750 q=1.000 recap=1.000 emerge@3500 done
             k2tau2000_k2_s6 step=   6250 q=0.984 recap=1.000 emerge@5750 done
             k2tau2000_k2_s7 step=   3750 q=0.986 recap=1.000 emerge@3500 done
             k2tau5000_k2_s0 step=  12000 q=0.945 recap=1.000 emerge@10750 done
             k2tau5000_k2_s1 step=  11750 q=0.975 recap=1.000 emerge@11250 done
             k2tau5000_k2_s2 step=   7000 q=0.998 recap=1.000 emerge@6750 done
             k2tau5000_k2_s3 step=   7750 q=0.961 recap=1.000 emerge@7500 done
             k2tau5000_k2_s4 step=  12500 q=0.939 recap=1.000 emerge@11500 done
             k2tau5000_k2_s5 step=  16250 q=0.926 recap=1.000 emerge@15500 done
             k2tau5000_k2_s6 step=  10000 q=0.984 recap=1.000 emerge@8250 done
             k2tau5000_k2_s7 step=  10500 q=0.990 recap=1.000 emerge@10000 done
```

## maint — n=28 terminal=28 failed=0 emerged=28 steps=38000-62000
```
              maint001_q4_s1 step=  46000 q=0.250 recap=1.000 emerge@16000 done
              maint001_q4_s2 step=  39500 q=0.668 recap=1.000 emerge@9500 done
              maint001_q4_s3 step=  41000 q=0.250 recap=1.000 emerge@11000 done
              maint001_q4_s4 step=  41750 q=0.260 recap=1.000 emerge@11750 done
              maint001_q4_s5 step=  38000 q=0.258 recap=1.000 emerge@8000 done
              maint001_q4_s6 step=  62000 q=0.262 recap=1.000 emerge@32000 done
              maint001_q4_s7 step=  40250 q=0.234 recap=1.000 emerge@10250 done
              maint005_q4_s1 step=  46000 q=0.994 recap=1.000 emerge@16000 done
              maint005_q4_s2 step=  39500 q=0.916 recap=1.000 emerge@9500 done
              maint005_q4_s3 step=  41000 q=0.877 recap=1.000 emerge@11000 done
              maint005_q4_s4 step=  41750 q=0.941 recap=1.000 emerge@11750 done
              maint005_q4_s5 step=  38000 q=0.977 recap=1.000 emerge@8000 done
              maint005_q4_s6 step=  62000 q=0.908 recap=1.000 emerge@32000 done
              maint005_q4_s7 step=  40250 q=0.938 recap=1.000 emerge@10250 done
              maint020_q4_s1 step=  46000 q=0.996 recap=1.000 emerge@16000 done
              maint020_q4_s2 step=  39500 q=0.980 recap=1.000 emerge@9500 done
              maint020_q4_s3 step=  41000 q=0.979 recap=1.000 emerge@11000 done
              maint020_q4_s4 step=  41750 q=0.982 recap=1.000 emerge@11750 done
              maint020_q4_s5 step=  38000 q=1.000 recap=1.000 emerge@8000 done
              maint020_q4_s6 step=  62000 q=0.969 recap=1.000 emerge@32000 done
              maint020_q4_s7 step=  40250 q=0.990 recap=1.000 emerge@10250 done
                wd0dep_q4_s1 step=  46000 q=0.260 recap=1.000 emerge@16000 done
                wd0dep_q4_s2 step=  39500 q=0.236 recap=1.000 emerge@9500 done
                wd0dep_q4_s3 step=  41000 q=0.230 recap=1.000 emerge@11000 done
                wd0dep_q4_s4 step=  41750 q=0.240 recap=1.000 emerge@11750 done
                wd0dep_q4_s5 step=  38000 q=0.273 recap=1.000 emerge@8000 done
                wd0dep_q4_s6 step=  62000 q=0.248 recap=1.000 emerge@32000 done
                wd0dep_q4_s7 step=  40250 q=0.244 recap=1.000 emerge@10250 done
```

## mech — n=28 terminal=28 failed=0 emerged=0 steps=70000-70000
```
             mech_both_q4_s1 step=  70000 q=0.250 recap=1.000 emerge@None done
             mech_both_q4_s2 step=  70000 q=0.225 recap=1.000 emerge@None done
             mech_both_q4_s3 step=  70000 q=0.232 recap=1.000 emerge@None done
             mech_both_q4_s4 step=  70000 q=0.252 recap=1.000 emerge@None done
             mech_both_q4_s5 step=  70000 q=0.250 recap=1.000 emerge@None done
             mech_both_q4_s6 step=  70000 q=0.250 recap=1.000 emerge@None done
             mech_both_q4_s7 step=  70000 q=0.240 recap=1.000 emerge@None done
         mech_optreset_q4_s1 step=  70000 q=0.244 recap=1.000 emerge@None done
         mech_optreset_q4_s2 step=  70000 q=0.238 recap=1.000 emerge@None done
         mech_optreset_q4_s3 step=  70000 q=0.230 recap=1.000 emerge@None done
         mech_optreset_q4_s4 step=  70000 q=0.246 recap=1.000 emerge@None done
         mech_optreset_q4_s5 step=  70000 q=0.273 recap=1.000 emerge@None done
         mech_optreset_q4_s6 step=  70000 q=0.256 recap=1.000 emerge@None done
         mech_optreset_q4_s7 step=  70000 q=0.244 recap=1.000 emerge@None done
            mech_plain_q4_s1 step=  70000 q=0.242 recap=1.000 emerge@None done
            mech_plain_q4_s2 step=  70000 q=0.232 recap=1.000 emerge@None done
            mech_plain_q4_s3 step=  70000 q=0.244 recap=1.000 emerge@None done
            mech_plain_q4_s4 step=  70000 q=0.266 recap=1.000 emerge@None done
            mech_plain_q4_s5 step=  70000 q=0.246 recap=1.000 emerge@None done
            mech_plain_q4_s6 step=  70000 q=0.279 recap=1.000 emerge@None done
            mech_plain_q4_s7 step=  70000 q=0.260 recap=1.000 emerge@None done
           mech_rewarm_q4_s1 step=  70000 q=0.236 recap=1.000 emerge@None done
           mech_rewarm_q4_s2 step=  70000 q=0.211 recap=1.000 emerge@None done
           mech_rewarm_q4_s3 step=  70000 q=0.248 recap=1.000 emerge@None done
           mech_rewarm_q4_s4 step=  70000 q=0.232 recap=1.000 emerge@None done
           mech_rewarm_q4_s5 step=  70000 q=0.244 recap=1.000 emerge@None done
           mech_rewarm_q4_s6 step=  70000 q=0.258 recap=1.000 emerge@None done
           mech_rewarm_q4_s7 step=  70000 q=0.201 recap=1.000 emerge@None done
```

## nanbisect — n=9 terminal=8 failed=0 emerged=0 steps=300-400
```
                     A_repro step=    400 q=0.000 recap=0.000 emerge@None done
                     B_smoke step=    400 q=0.000 recap=0.000 emerge@None done
                    C_finite step=    400 q=0.250 recap=1.000 emerge@None done
                  D_explicit step=    400 q=0.000 recap=0.000 emerge@None done
                      E_bf16 step=    300 q=0.000 recap=0.000 emerge@None running
                      F_bs32 step=    400 q=0.000 recap=0.000 emerge@None done
                       G_nl2 step=    400 q=0.000 recap=0.000 emerge@None done
                     H_ctx22 step=    400 q=0.000 recap=0.000 emerge@None done
                  I_fin_expl step=    400 q=0.281 recap=1.000 emerge@None done
```

## postem — n=14 terminal=14 failed=0 emerged=14 steps=48000-72000
```
               postdep_q4_s1 step=  56000 q=0.230 recap=1.000 emerge@16000 done
               postdep_q4_s2 step=  49500 q=0.258 recap=1.000 emerge@9500 done
               postdep_q4_s3 step=  51000 q=0.264 recap=1.000 emerge@11000 done
               postdep_q4_s4 step=  51750 q=0.264 recap=1.000 emerge@11750 done
               postdep_q4_s5 step=  48000 q=0.248 recap=1.000 emerge@8000 done
               postdep_q4_s6 step=  72000 q=0.262 recap=1.000 emerge@32000 done
               postdep_q4_s7 step=  50250 q=0.242 recap=1.000 emerge@10250 done
              postresc_q4_s1 step=  56000 q=0.273 recap=1.000 emerge@16000 done
              postresc_q4_s2 step=  49500 q=0.289 recap=1.000 emerge@9500 done
              postresc_q4_s3 step=  51000 q=0.254 recap=1.000 emerge@11000 done
              postresc_q4_s4 step=  51750 q=0.268 recap=1.000 emerge@11750 done
              postresc_q4_s5 step=  48000 q=0.271 recap=1.000 emerge@8000 done
              postresc_q4_s6 step=  72000 q=0.258 recap=1.000 emerge@32000 done
              postresc_q4_s7 step=  50250 q=0.258 recap=1.000 emerge@10250 done
```

## prestore — n=72 terminal=72 failed=0 emerged=72 steps=65000-73750

## pulse — n=96 terminal=96 failed=0 emerged=6 steps=2000-21000

## q0 — n=1 terminal=1 failed=0 emerged=0 steps=200-200
```
                    q0_smoke step=    200 q=0.000 recap=0.000 emerge@None done
```

## qgates — n=3 terminal=3 failed=0 emerged=1 steps=200-8000
```
               q2_noop_q4_s5 step=   8000 q=0.758 recap=1.000 emerge@7000 done
              q3_neuron_bf16 step=    200 q=0.609 recap=1.000 emerge@None done
              q3_neuron_fp32 step=    200 q=0.609 recap=1.000 emerge@None done
```

## symbreak — n=128 terminal=128 failed=0 emerged=0 steps=16000-28000

## tau — n=24 terminal=24 failed=0 emerged=6 steps=15250-70000
```
              tau20000_q4_s0 step=  70000 q=0.248 recap=1.000 emerge@None done
              tau20000_q4_s1 step=  70000 q=0.248 recap=1.000 emerge@None done
              tau20000_q4_s2 step=  70000 q=0.219 recap=1.000 emerge@None done
              tau20000_q4_s3 step=  70000 q=0.230 recap=1.000 emerge@None done
              tau20000_q4_s4 step=  70000 q=0.250 recap=1.000 emerge@None done
              tau20000_q4_s5 step=  70000 q=0.244 recap=1.000 emerge@None done
              tau20000_q4_s6 step=  70000 q=0.260 recap=1.000 emerge@None done
              tau20000_q4_s7 step=  70000 q=0.232 recap=1.000 emerge@None done
               tau2000_q4_s0 step=  61250 q=0.975 recap=1.000 emerge@60500 done
               tau2000_q4_s1 step=  49750 q=1.000 recap=1.000 emerge@43750 done
               tau2000_q4_s2 step=  70000 q=0.496 recap=1.000 emerge@None done
               tau2000_q4_s3 step=  70000 q=0.482 recap=1.000 emerge@None done
               tau2000_q4_s4 step=  70000 q=0.250 recap=1.000 emerge@None done
               tau2000_q4_s5 step=  70000 q=0.279 recap=1.000 emerge@None done
               tau2000_q4_s6 step=  45750 q=1.000 recap=1.000 emerge@18250 done
               tau2000_q4_s7 step=  15250 q=0.941 recap=1.000 emerge@12750 done
               tau5000_q4_s0 step=  70000 q=0.479 recap=1.000 emerge@None done
               tau5000_q4_s1 step=  70000 q=0.250 recap=1.000 emerge@None done
               tau5000_q4_s2 step=  70000 q=0.508 recap=1.000 emerge@None done
               tau5000_q4_s3 step=  70000 q=0.520 recap=1.000 emerge@None done
               tau5000_q4_s4 step=  70000 q=0.471 recap=1.000 emerge@None done
               tau5000_q4_s5 step=  18000 q=0.932 recap=1.000 emerge@17000 done
               tau5000_q4_s6 step=  39750 q=0.994 recap=1.000 emerge@39000 done
               tau5000_q4_s7 step=  70000 q=0.480 recap=1.000 emerge@None done
```

## thresh — n=21 terminal=21 failed=0 emerged=21 steps=38000-62000
```
                thr002_q4_s1 step=  46000 q=0.977 recap=1.000 emerge@16000 done
                thr002_q4_s2 step=  39500 q=0.809 recap=1.000 emerge@9500 done
                thr002_q4_s3 step=  41000 q=0.432 recap=1.000 emerge@11000 done
                thr002_q4_s4 step=  41750 q=0.746 recap=1.000 emerge@11750 done
                thr002_q4_s5 step=  38000 q=0.229 recap=1.000 emerge@8000 done
                thr002_q4_s6 step=  62000 q=0.248 recap=1.000 emerge@32000 done
                thr002_q4_s7 step=  40250 q=0.883 recap=1.000 emerge@10250 done
                thr003_q4_s1 step=  46000 q=0.973 recap=1.000 emerge@16000 done
                thr003_q4_s2 step=  39500 q=0.854 recap=1.000 emerge@9500 done
                thr003_q4_s3 step=  41000 q=0.812 recap=1.000 emerge@11000 done
                thr003_q4_s4 step=  41750 q=0.840 recap=1.000 emerge@11750 done
                thr003_q4_s5 step=  38000 q=0.791 recap=1.000 emerge@8000 done
                thr003_q4_s6 step=  62000 q=0.805 recap=1.000 emerge@32000 done
                thr003_q4_s7 step=  40250 q=0.941 recap=1.000 emerge@10250 done
                thr004_q4_s1 step=  46000 q=0.973 recap=1.000 emerge@16000 done
                thr004_q4_s2 step=  39500 q=0.881 recap=1.000 emerge@9500 done
                thr004_q4_s3 step=  41000 q=0.881 recap=1.000 emerge@11000 done
                thr004_q4_s4 step=  41750 q=0.865 recap=1.000 emerge@11750 done
                thr004_q4_s5 step=  38000 q=0.852 recap=1.000 emerge@8000 done
                thr004_q4_s6 step=  62000 q=0.926 recap=1.000 emerge@32000 done
                thr004_q4_s7 step=  40250 q=0.883 recap=1.000 emerge@10250 done
```

## tomo_pulse — n=264 terminal=264 failed=0 emerged=12 steps=4250-28000

## tomo_traj — n=16 terminal=16 failed=0 emerged=0 steps=24000-24000
```
              tomotraj_q4_s0 step=  24000 q=0.277 recap=1.000 emerge@None done
              tomotraj_q4_s1 step=  24000 q=0.246 recap=1.000 emerge@None done
             tomotraj_q4_s10 step=  24000 q=0.232 recap=1.000 emerge@None done
             tomotraj_q4_s11 step=  24000 q=0.254 recap=1.000 emerge@None done
             tomotraj_q4_s12 step=  24000 q=0.268 recap=1.000 emerge@None done
             tomotraj_q4_s13 step=  24000 q=0.229 recap=1.000 emerge@None done
             tomotraj_q4_s14 step=  24000 q=0.262 recap=1.000 emerge@None done
             tomotraj_q4_s15 step=  24000 q=0.273 recap=1.000 emerge@None done
              tomotraj_q4_s2 step=  24000 q=0.248 recap=1.000 emerge@None done
              tomotraj_q4_s3 step=  24000 q=0.250 recap=1.000 emerge@None done
              tomotraj_q4_s4 step=  24000 q=0.246 recap=1.000 emerge@None done
              tomotraj_q4_s5 step=  24000 q=0.256 recap=1.000 emerge@None done
              tomotraj_q4_s6 step=  24000 q=0.223 recap=1.000 emerge@None done
              tomotraj_q4_s7 step=  24000 q=0.211 recap=1.000 emerge@None done
              tomotraj_q4_s8 step=  24000 q=0.258 recap=1.000 emerge@None done
              tomotraj_q4_s9 step=  24000 q=0.248 recap=1.000 emerge@None done
```

## transplant — n=81 terminal=81 failed=0 emerged=5 steps=8000-28000

## wd0 — n=24 terminal=24 failed=0 emerged=7 steps=9250-70000
```
          wd0_noop_wd0_q4_s0 step=  70000 q=0.508 recap=1.000 emerge@None done
          wd0_noop_wd0_q4_s1 step=  16000 q=0.992 recap=1.000 emerge@15500 done
          wd0_noop_wd0_q4_s2 step=   9500 q=0.949 recap=1.000 emerge@8500 done
          wd0_noop_wd0_q4_s3 step=  11000 q=0.908 recap=1.000 emerge@9750 done
          wd0_noop_wd0_q4_s4 step=  11750 q=0.930 recap=1.000 emerge@10500 done
          wd0_noop_wd0_q4_s5 step=   9250 q=0.953 recap=1.000 emerge@7000 done
          wd0_noop_wd0_q4_s6 step=  33750 q=0.957 recap=1.000 emerge@31750 done
          wd0_noop_wd0_q4_s7 step=  10250 q=0.938 recap=1.000 emerge@8750 done
       wd0_resc10k_wd0_q4_s0 step=  70000 q=0.277 recap=1.000 emerge@None done
       wd0_resc10k_wd0_q4_s1 step=  70000 q=0.254 recap=1.000 emerge@None done
       wd0_resc10k_wd0_q4_s2 step=  70000 q=0.215 recap=1.000 emerge@None done
       wd0_resc10k_wd0_q4_s3 step=  70000 q=0.225 recap=1.000 emerge@None done
       wd0_resc10k_wd0_q4_s4 step=  70000 q=0.248 recap=1.000 emerge@None done
       wd0_resc10k_wd0_q4_s5 step=  70000 q=0.240 recap=1.000 emerge@None done
       wd0_resc10k_wd0_q4_s6 step=  70000 q=0.258 recap=1.000 emerge@None done
       wd0_resc10k_wd0_q4_s7 step=  70000 q=0.219 recap=1.000 emerge@None done
       wd0_resc20k_wd0_q4_s0 step=  70000 q=0.248 recap=1.000 emerge@None done
       wd0_resc20k_wd0_q4_s1 step=  70000 q=0.248 recap=1.000 emerge@None done
       wd0_resc20k_wd0_q4_s2 step=  70000 q=0.219 recap=1.000 emerge@None done
       wd0_resc20k_wd0_q4_s3 step=  70000 q=0.230 recap=1.000 emerge@None done
       wd0_resc20k_wd0_q4_s4 step=  70000 q=0.250 recap=1.000 emerge@None done
       wd0_resc20k_wd0_q4_s5 step=  70000 q=0.244 recap=1.000 emerge@None done
       wd0_resc20k_wd0_q4_s6 step=  70000 q=0.260 recap=1.000 emerge@None done
       wd0_resc20k_wd0_q4_s7 step=  70000 q=0.232 recap=1.000 emerge@None done
```

## window — n=22 terminal=22 failed=0 emerged=1 steps=46500-80000
```
               win1000_q4_s0 step=  80000 q=0.254 recap=1.000 emerge@None done
               win1000_q4_s1 step=  80000 q=0.236 recap=1.000 emerge@None done
               win1000_q4_s2 step=  46500 q=0.916 recap=1.000 emerge@44500 done
               win1000_q4_s3 step=  80000 q=0.250 recap=1.000 emerge@None done
               win1000_q4_s4 step=  80000 q=0.211 recap=1.000 emerge@None done
              win12000_q4_s0 step=  80000 q=0.252 recap=1.000 emerge@None done
              win12000_q4_s1 step=  80000 q=0.242 recap=1.000 emerge@None done
               win2000_q4_s0 step=  80000 q=0.260 recap=1.000 emerge@None done
               win2000_q4_s1 step=  80000 q=0.240 recap=1.000 emerge@None done
               win2000_q4_s2 step=  80000 q=0.260 recap=1.000 emerge@None done
               win2000_q4_s3 step=  80000 q=0.256 recap=1.000 emerge@None done
               win2000_q4_s4 step=  80000 q=0.275 recap=1.000 emerge@None done
               win4000_q4_s0 step=  80000 q=0.230 recap=1.000 emerge@None done
               win4000_q4_s1 step=  80000 q=0.258 recap=1.000 emerge@None done
               win4000_q4_s2 step=  80000 q=0.262 recap=1.000 emerge@None done
               win4000_q4_s3 step=  80000 q=0.254 recap=1.000 emerge@None done
               win4000_q4_s4 step=  80000 q=0.227 recap=1.000 emerge@None done
               win8000_q4_s0 step=  80000 q=0.250 recap=1.000 emerge@None done
               win8000_q4_s1 step=  80000 q=0.236 recap=1.000 emerge@None done
               win8000_q4_s2 step=  80000 q=0.262 recap=1.000 emerge@None done
               win8000_q4_s3 step=  80000 q=0.221 recap=1.000 emerge@None done
               win8000_q4_s4 step=  80000 q=0.229 recap=1.000 emerge@None done
```

## zero — n=24 terminal=24 failed=0 emerged=3 steps=31250-70000
```
             zero0p001_q4_s0 step=  45000 q=0.953 recap=1.000 emerge@44500 done
             zero0p001_q4_s1 step=  43000 q=0.904 recap=1.000 emerge@40750 done
             zero0p001_q4_s2 step=  70000 q=0.238 recap=1.000 emerge@None done
             zero0p001_q4_s3 step=  70000 q=0.492 recap=1.000 emerge@None done
             zero0p001_q4_s4 step=  70000 q=0.490 recap=1.000 emerge@None done
             zero0p001_q4_s5 step=  70000 q=0.252 recap=1.000 emerge@None done
             zero0p001_q4_s6 step=  70000 q=0.484 recap=1.000 emerge@None done
             zero0p001_q4_s7 step=  70000 q=0.248 recap=1.000 emerge@None done
             zero0p005_q4_s0 step=  70000 q=0.502 recap=1.000 emerge@None done
             zero0p005_q4_s1 step=  70000 q=0.236 recap=1.000 emerge@None done
             zero0p005_q4_s2 step=  31250 q=0.998 recap=1.000 emerge@30750 done
             zero0p005_q4_s3 step=  70000 q=0.238 recap=1.000 emerge@None done
             zero0p005_q4_s4 step=  70000 q=0.240 recap=1.000 emerge@None done
             zero0p005_q4_s5 step=  70000 q=0.289 recap=1.000 emerge@None done
             zero0p005_q4_s6 step=  70000 q=0.248 recap=1.000 emerge@None done
             zero0p005_q4_s7 step=  70000 q=0.242 recap=1.000 emerge@None done
              zero0p01_q4_s0 step=  70000 q=0.502 recap=1.000 emerge@None done
              zero0p01_q4_s1 step=  70000 q=0.242 recap=1.000 emerge@None done
              zero0p01_q4_s2 step=  70000 q=0.250 recap=1.000 emerge@None done
              zero0p01_q4_s3 step=  70000 q=0.232 recap=1.000 emerge@None done
              zero0p01_q4_s4 step=  70000 q=0.232 recap=1.000 emerge@None done
              zero0p01_q4_s5 step=  70000 q=0.273 recap=1.000 emerge@None done
              zero0p01_q4_s6 step=  70000 q=0.480 recap=1.000 emerge@None done
              zero0p01_q4_s7 step=  70000 q=0.246 recap=1.000 emerge@None done
```

**Live trainers:** 0   **Total terminal:** 1237
