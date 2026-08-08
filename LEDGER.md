# devaxis ledger

## 2026-08-08 ~23:05Z — THE DOSE-RESPONSE LANDED. Monotone, p = 7.8e-05.

Deprivation length tau, applied at the same pre-emergence state (step 4,000), same schedule
shape, same parents, same everything else:

| tau | emerged | n | rate | final query_ctx per run (chance 0.25) |
|---|---|---|---|---|
| 0 (no-op) | 7 | 7 | **1.00** | all emerged, median delay 5,750 |
| 2,000 | 4 | 8 | **0.50** | 0.25, 0.28, 0.48, 0.50, 0.94, 0.98, 1.00, 1.00 |
| 5,000 | 2 | 8 | **0.25** | 0.25, 0.47, 0.48, 0.48, 0.51, 0.52, 0.93, 0.99 |
| 10,000 | 0 | 7 | **0.00** | 0.23–0.29 (all at chance) |
| 20,000 | 0 | 8 | **0.00** | 0.22–0.26 (all at chance) |

**Cochran-Armitage trend test: z = -3.783, one-tailed p = 7.8e-05, n = 38 runs.**

Two features beyond the headline:
1. **The intermediate shelf.** At tau = 2,000 and 5,000 several runs sit at query_ctx ~0.47-0.52
   — the half-solved plateau — while at tau >= 10,000 nothing leaves chance at all. Short
   deprivation degrades gracefully; long deprivation forecloses the intermediate state too.
2. **The confound that could have explained it does not.** Longer tau leaves fewer use-supplied
   steps inside the budget (46,000 at tau=20,000 vs 64,000 at tau=2,000). But the slowest
   control ever needed 27,750, so EVERY arm had at least 1.7x the opportunity the slowest
   control required. "Not enough time" cannot produce this curve.

Together with the paired branch result (7/7 reversals, p = 0.0078) and the artifact battery
(schedule verified, gradient reopens, recap = 1.000, zero learning across 42k steps), the
phenomenon is established on this task: **there is a deprivation dose beyond which the use
circuit does not form, while the read circuit remains perfect.**

Still open, and running: WHERE the window sits in developmental time (phase W, fixed insult at
5 ages — the test of whether this is a critical PERIOD or merely dose-dependent damage), and
WHAT carries the block (phase M: optimizer state vs LR scale vs weights).

Scope, unchanged: one task family, one model size (4.9M), one architecture, 7-8 seeds per arm,
one fork state so far. Cross-session consistency: clocks-law reports tau=2,000 7/10 vs
tau=6,000 0/10 on different hardware — same shape, independently.

## 2026-08-08 ~20:55Z — DEEP PROGRAM QUEUED (open-ended, extensible without restarts)

Health verified: 4 units active, exactly 1 dispatcher, 26/26 tests green, factorial 49/49
terminal, branch 21/21 (18 terminal, the 3 stragglers cannot change any conclusion).

The critical-period result is real, so the next questions are the ones that turn a phenomenon
into a mechanism. Queued in `PROGRAM.json`, executed by a new `devaxis-program` unit:

**Phase W — WHERE is the window? (is this a critical PERIOD at all?)**
Hold the insult FIXED (tau = 10,000 deprived steps) and move the AGE at which it lands:
forks at 1k / 2k / 4k / 8k / 12k x 5 seeds = 25 runs. 8k-12k straddles the baseline emergence
band (median 9,750), so some parents will ALREADY have the use circuit when deprivation hits —
the most informative cell, since it asks whether a formed circuit survives what an unformed one
cannot. Predictions declared: age-dependent = critical period; uniform = "damage, not a period";
late-only = refutes the developmental framing outright.

**Phase M — WHAT blocks the rescue?**
Fork the DEPRIVED models and rescue four ways: plain (replication, must fail again),
optimizer-reset (weights kept, Adam moments dropped), LR-rewarm (restart the warmup ramp), both.
Declared interpretation: optreset rescues => the blocker is OPTIMIZER STATE; rewarm rescues =>
it is the LR/landscape scale; NEITHER rescues => the block is in the WEIGHTS, which is the
strongest and most interesting version. Engine gained `reset_optimizer` and `lr_rewarm` knobs,
both default-off and regression-tested (26/26).

**Phase D — DD10** (same data from two developmental states) carried over.

**The runner itself is the deliverable that matters for "never run out of ideas":**
`tools/program.py` reads its phase list from a FILE every iteration, so experiments can be
appended at any time without restarting anything or killing a live dispatcher. It judges
completion by diffing the QUEUE against the RESULTS (so a never-started job cannot hide, the
failure that cost us 6 branch runs), keeps state in PROGRAM_STATE.json so a restart resumes
rather than repeats, revives a dead dispatcher up to 5 times, abandons a stalled phase after 60
min instead of blocking the night, and regenerates the morning report after EVERY phase so
there is always a current answer.

Sequencing race closed: the runner waits both for zero trainers AND for the overnight
orchestrator to go inactive — between its phases the trainer count momentarily hits zero, and
both runners would otherwise grab cores in that gap.

## 2026-08-08 ~20:35Z — RESULTS: factorial is a clean NULL; the critical period reaches p = 0.0078

### 1. DD factorial — COMPLETE (49/49 terminal) — NULL

| cell | n | events | censored | KM median emergence |
|---|---|---|---|---|
| baseline (no recurrence) | 8 | 7 | 1 | 9,750 |
| exact / short / fixed | 5 | 5 | 0 | 10,000 |
| exact / short / scrambled | 5 | 5 | 0 | 9,000 |
| exact / long / fixed | 5 | 3 | 2 | 16,750 |
| exact / long / scrambled | 5 | 3 | 2 | 12,000 |
| paraphrase / short / fixed | 5 | 4 | 1 | 17,500 |
| paraphrase / short / scrambled | 5 | 5 | 0 | 8,500 |
| paraphrase / long / fixed | 5 | 4 | 1 | 9,250 |
| paraphrase / long / scrambled | 5 | 4 | 1 | 9,500 |

Log-rank vs baseline, Holm-corrected: **every cell p_holm = 1.0** (smallest raw p = 0.197).
At rate 0.25 with a 64-program pool, recurrence TYPE (exact vs paraphrase), SPACING (50 vs 500)
and ORDER (fixed vs scrambled) do not measurably move when the use circuit emerges. Honest
scope: n = 5 per cell powers only large shifts, so this is "no large effect", not "no effect".

### 2. Branch matrix — all arms COMPLETE at 7/7 parents — POSITIVE

| arm | n | emerged | use-supplied steps |
|---|---|---|---|
| noop (p = 1) | 7 | **7/7** | delays 3000, 4500, 4750, 5750, 6500, 11500, 27750 (median 5,750) |
| deprive (p = 0 forever) | 7 | **0/7** | to 46,000 |
| rescue10k (p=0 at 4k, p=1 at 14k) | 7 | **0/7** | 5 censored >46,000, 2 censored >13,250 |

**PAIRED sign test over all 7 parents: 7/7 reversals, one-tailed p = 0.0078.**

The sign is LOCKED for every pair, including the two shorter censorings: q4_s2's control emerged
at 4,500 use-supplied steps and its rescued twin is already past 13,250 without emerging;
q4_s4's control took 6,500 against >13,250. A pair can no longer flip, so this p-value will not
change when those two finish.

**Read the two results together:** how repetition is DISTRIBUTED did not move emergence at all;
WHEN the supply arrives decided whether it happens. Same task, same model, same corpus, same
platform, same analysis.

Still owed before this is a claim rather than a result: the tau dose-response {2k, 5k, 20k}
(running tonight) — a monotone curve is far harder to explain away than one contrast; and the
scope limits stand (one fork state, one task, one model size, 7 seeds).

## 2026-08-08 ~19:50Z — 6 lost branch runs RECOVERED; the paired design will be complete

Caught during the tick: the branch matrix reported "all lanes drained" with only **15 of 21**
runs. The 6 missing ones never produced a run JSON at all — they were launched onto NeuronCores
still held by factorial runs, failed at runtime init, exhausted their retries, and vanished.
They were invisible in the results because a run that never starts writes nothing.

**Why it mattered scientifically:** the missing set was `br_noop_q4_s1`, `br_noop_q4_s4`,
`br_noop_q4_s7`, `br_rescue10k_q4_s2`, `br_rescue10k_q4_s4`, `br_deprive_q4_s6` — i.e. THREE OF
THE MISSING RUNS WERE NO-OP CONTROLS, the exact arm (4/7) that was limiting the paired analysis
to 3 parents and p = 0.125. Recovering them takes every arm to 7/7 and the paired comparison to
7 parents; 7/7 reversals would be p = 0.0078.

**Fixed two ways:**
- recovery queue for the 6 runs launched on verified-free cores (`devaxis-branchfix`); 21/21 run
  records now exist;
- **builders now query /proc for cores already held by a live trainer and skip them**, so a wave
  can never again be launched onto occupied lanes. This was the root cause, not bad luck.

Note the failure mode for the future: `topology.py` marks such a job FAILED after retries, but
with no run JSON it is absent from every downstream count. The morning report counts runs that
EXIST; a job that never started is invisible unless the queue is diffed against the results —
which is what `tools/missing.py` now does.

## 2026-08-08 ~19:20Z — ARTIFACT AUDIT of the critical-period finding (+ a p-value RETRACTION)

Ran a five-check falsification battery (`tools/artifact_check.py`) against my own interim claim.

**MECHANICAL ARTIFACTS — ALL RULED OUT:**
- **A1 the rescue really happens.** 182-185 evals per run with p_now == 1.0 after step 14,000
  and 40 evals with p_now == 0.0 during the window; ZERO violations in 5/5 runs. This was the
  dangerous one: a broken schedule would make rescue identical to deprive, which is exactly
  what the data look like.
- **A2 the gradient really changes.** Training loss jumps 0.0001 -> 0.19 at the rescue step in
  every run. (During deprivation the loss is ~0.0001: the model has perfectly mastered the only
  supervised tokens, the recap.) The mask genuinely reopens.
- **A3 the model is not broken.** recap = 1.000 (min, median, max) in BOTH deprived and rescued
  arms. The read circuit is perfect; only USE fails. This is a represented-but-unusable
  dissociation, not a damaged network.
- **A4 the readout is alive.** query_ctx oscillates 0.20-0.30 around chance 0.25 in the failing
  arms while noop controls reach 0.91-0.95 on the same eval code.
- **NEW, and the strongest single piece of evidence: zero learning progress.** Over the 42,000
  use-supplied steps after rescue, loss goes 0.1863 -> 0.1786 and query_ctx stays 0.252, 0.257,
  0.261, 0.252, 0.247, 0.249 — dead flat, in all 5 runs. Controls forked from the SAME
  checkpoint fall to 0.029-0.09 loss and 0.67-0.93 query_ctx within 5,000-25,000 steps. The
  rescued models are not learning slowly; they are not learning.

**STATISTICS — I OVERSTATED THEM AND RETRACT:**
My Fisher p = 0.0079 (noop 4/4 vs rescue 0/5) was anti-conservative. It ignored that this is a
PAIRED design and it compared unequal parent sets (noop had s2,s3,s5,s6; rescue had
s1,s3,s5,s6,s7) when parents differ ~4x in intrinsic emergence time (3,000 to 27,750 steps).
Only 3 parents are currently in both arms. The defensible number is the paired sign test:
**3/3 reversals, one-tailed p = 0.125 — NOT significant.**
With all 7 parents paired, 7/7 would give p = 0.0078.

**STATUS: mechanism verified real; effect large and perfectly consistent; sample too small.**
Arms are incomplete (noop 4/7, deprive 6/7, rescue 5/7). What decides it: (a) the remaining
pairs, (b) tonight's tau dose-response {2k,5k,20k} — a monotone curve is far harder to explain
away than any single contrast.

**External consistency (NOT my measurement, cross-session):** the clocks-law session reports an
independent tau dose-response on different hardware — tau=2,000 7/10 emerged vs tau=6,000 0/10
(Fisher p~0.0015). Our tau=10,000 giving 0/5 is consistent with their tau=6,000 arm. Encouraging
but it is their result, and it must not be folded into ours.

## 2026-08-08 ~18:55Z — INTERIM (not terminal): the branch matrix is showing a critical period

**Branch matrix, fork at step 4000** (pre-emergence for every parent, post-read for every
parent). Arms differ ONLY in the use-supply schedule p.

| arm | n | terminal | emerged | use-supplied steps |
|---|---|---|---|---|
| noop (p=1) | 4 | 4 | **4/4** | delays to emergence [3000, 4500, 5750, 27750], median 5125 |
| deprive (p=0 forever) | 6 | 0 | **0/6** | ~52,000 elapsed, query_ctx 0.22-0.27 (chance 0.25) |
| rescue10k (p=0 at 4k, p=1 at 14k) | 5 | 0 | **0/5** | **~42,000 since rescue**, query_ctx 0.22-0.27 |

Two things are already established and do not depend on the runs finishing:

1. **The no-op fork reproduces its parent at the level of the SCIENCE ENDPOINT.** All four
   noop children emerged at exactly their parent's step: 9750/7000/8500/31750 vs parent
   9750/7000/8500/31750. Q2's bitwise certificate showing up where it matters.
2. **The deprived-then-rescued arm has now had 42,000 use-supplied steps — 1.5x the SLOWEST
   noop delay and 8.2x the median — and none of the 5 has emerged.** Fisher exact one-tailed
   on 4/4 vs 0/5 is p = 0.0079.

This is the DAMAGE branch of the pre-registered falsifier, not DELAY: a 10,000-step deprivation
applied at a pre-emergence state appears to FORECLOSE the use circuit rather than postpone it.
The tau sweep queued for tonight (tau in {2k,5k,20k}) turns this single contrast into a
dose-response curve, which is the thing worth believing.

**INTERIM. Not terminal (~4,000 steps left in each arm), n=4 vs n=5, one wave, one fork state.**
Do not quote as a result until the arms terminate and the tau curve exists.

Also noted: one factorial run (dd_paraphrase_short_fixed_s4) restarted and sits at 10,250/120,000,
so it will still be running when the orchestrator advances (it proceeds at 48/49 terminal). The
tau phase may lose at most one run to core contention with it; the dispatcher will mark it
FAILED and the morning report lists failures.

## 2026-08-08 — OVERNIGHT PROGRAM ARMED (unattended, laptop-independent)

Everything runs on the box under systemd; no laptop, no tmux attachment, no SSH session is
required. Units: devaxis-overnight (orchestrator, Restart=on-failure), devaxis-wave,
devaxis-branch, devaxis-guard (deadline), devaxis-sync.timer (S3 every 10 min).

Queue: drain factorial (48) + branch matrix (21) -> Phase B tau dose-response (21 runs,
tau in {2k,5k,20k}; tau=10k already running; tau=0 is the parent, free, since Q2 certified a
no-op fork is BITWISE) -> Phase C DD10 same-data-different-state (fork the SAME exact-recurrence
intervention from step 4000 vs 12000) -> MORNING_REPORT.md written and synced to
s3://.../devaxis/MORNING_REPORT.md.

TWO BUGS CAUGHT BEFORE THEY RAN OVERNIGHT (both mine):
1. `running_count()` used an invalid `pgrep -m` flag and returned 0 ALWAYS, while the revive
   rule read it — that would have spawned a second dispatcher on a live queue, i.e. two writers
   per output file. Verified on the box the corrected pattern returns 20. The revive rule now
   fires only when we have WATCHED OUR OWN dispatcher exit; systemd-owned waves are never
   revived from here. Confirmed zero revives had fired and only the 2 legitimate dispatchers
   existed, so nothing was corrupted.
2. Phase waiters used a hardcoded expected count; a builder that legitimately emits fewer runs
   (a parent missing the checkpoint a fork needs) would have stalled the night for 45 min.
   Expected count is now read from the queue the builder actually wrote.

Report-time discipline: morning_report.py recomputes every number from run JSONs and SUPPRESSES
comparisons for any experiment that is not fully terminal (a table is read; a caveat is not).

## 2026-08-08 (midday) — branch matrix LAUNCHED on idle lanes; factorial 39/48 terminal

Factorial: 48 reporting, 39 terminal, 9 still training (max step 75,750/120,000, ~1.5h).
Comparisons still withheld — cells are not all terminal.

Q2 certified T0 bitwise, so forks are now scientifically interpretable -> launched the
PRE-REGISTERED branch matrix on the 23 idle cores (`devaxis-branch` unit, 21 runs = 7 baseline
parents x 3 arms), forking every parent at step 4000: a state that is PRE-emergence for all of
them (earliest measured emergence 7000) but POST-read (recap saturates ~500).

  noop       p=1.0                          control; must reproduce the parent
  deprive    p->0 at 4000, permanent        positive control (lag_law p=0: no use supply, no use)
  rescue10k  p->0 at 4000, p->1 at 14000    the question

Primary endpoint: emergence step, right-censored. Secondary and decisive: emergence delay in
USE-SUPPLIED steps since rescue — the age-matched comparison that separates "a window closed"
from "a clock started late". Falsifier stated up front: if rescue10k emerges at the same
use-supplied delay as noop, deprivation only postpones and there is no critical period here.

Box now at 30/32 cores busy (9 factorial + 21 branch).

## 2026-08-08 — PLATFORM GATES PASSED (Q2 bitwise, Q3 fp32)

**Q2 exact-branch replay: TIER T0 (BITWISE).** Forked q4_s5 at step 4000, replayed to 8000 on
the same NeuronCore: metric_drift_max 0.0, metrics_exact True, bitwise True,
max_rel_param_div 0.0, across 17 eval points. STRONGER than the T1 the plan expected on trn1.
Consequence: in the branch matrix, any parent-child difference is caused by the intervention,
never by the platform.

**Q3 numerical equivalence vs the CPU fp64 oracle (same keyed stream, 200 steps):**
  neuron fp32 : max relative dloss 2.081e-06  -> PASS (bar 1.798e-05; CPU's own fp32 = 1.798e-06)
  neuron bf16 : max relative dloss 2.388e-02  -> fails the fp32 bar, AS IT SHOULD
bf16 has an 8-bit mantissa (eps ~7.8e-03), so ~1e-2 relative error is what bf16 IS, not a
defect — it is a separate numerical condition needing its own developmental-equivalence study
before any science use. The factorial runs fp32, i.e. the certified leg, at 2.8x the platform's
irreducible error. Neuron fp32 results may be pooled with the CPU reference sweep.

## 2026-08-08 (mid-wave) — 37/48 terminal, Q gates running on freed lanes

MEASURED: 48 runs reporting, **37 emerged**, 37 terminal, 11 still training (non-emergers run
the full 120k budget; furthest at 48k). 8.4 steps/s/core, 403 steps/s aggregate, 0 failures.
Emergence steps span 6,750–37,000 across all cells; baseline 7,000–31,750.

NOT reporting comparisons yet: cells started hours apart, so any cross-cell contrast right now
measures launch order. `analyse.py` prints its own NOT FINAL banner and I am honouring it.
(This trap already fired once: paraphrase cells read 0/5 emerged at 07:00 purely because they
had not started — by 08:20 they were at 5/5.)

Built while waiting: `analysis/analyse.py` — Kaplan-Meier + log-rank vs baseline, Holm-corrected,
right-censoring honoured (a non-emerger contributes "> last_step", never "= max step").
VALIDATED ON GROUND TRUTH BOTH WAYS before use: identical groups -> chi2 0.000 p 1.000;
separated groups -> chi2 9.701 p 0.0018; censored observation refuses to become an event.

Q2 (no-op branch replay from q4_s5 @4000 -> 8000) and Q3 (neuron fp32 + bf16 vs the S3 CPU
yardstick: loss <= 1.8e-05, param relL2 <= 2.5e-03) launched on cores 28-30.

## 2026-08-08 — WAVE v3 LIVE AND VERIFIED HEALTHY

Canary gate PASSED (8/8 finite losses, max_recap 1.000) -> wave started under `devaxis-wave`.
MEASURED at ~5 min in: 32 runs, 8.28-8.42 steps/s each, aggregate 276 steps/s, 0 crashes,
0 failures, 0 NaN.  Canary at step 2000: recap 0.999, loss 0.192, query_ctx 0.234 (chance
0.250) — read circuit saturated, use circuit not yet emerged: the reference developmental
pattern, on Neuron, for the first time.

One more trap found and fixed on the way: a dispatcher spawned from the Type=oneshot launcher
was killed when that unit finished (systemd KillMode=control-group; start_new_session detaches
the session, not the cgroup).  The wave now runs under its own long-lived unit and the
launcher only gates (`d0cf737`).

ETA: 120k-step censored run ~4 h; 50 jobs over 32 lanes ~8 h wall, less as runs early-stop.

## 2026-08-08 — ROOT CAUSE: the -inf attention mask NaN'd every Neuron run

**The failure.** The v2 wave ran 32 cores for hours at 8.4 steps/s producing **NaN loss and
recap 0.000 through 36,000 steps** — fast garbage. I reported "17x faster" without checking
that the runs were learning. Wave archived (`runs/factorial_v2_NAN`).

**The cause (9-arm bisect on 9 cores, `tools/nan_bisect.py`, arm JSONs in S3):**

| arm | change from failing config | max recap | loss |
|---|---|---|---|
| A_repro | none (control) | 0.000 | NaN |
| D_explicit | own attention impl | 0.000 | NaN |
| E_bf16 / F_bs32 / G_nl2 | precision / batch / depth | 0.000 | NaN |
| H_ctx22 | K=2,D=8 (ctx 54 -> 22) | 1.000 | 3.58 -> 0.24 |
| **C_finite** | **mask_value=finite** | **1.000** | **4.71 -> 0.24** |
| I_fin_expl | finite + explicit attn | 1.000 | 4.78 -> 0.24 |

`torch.full(..., -inf)` causal mask + Neuron's tiled softmax: at ctx=54 whole tiles sit above
the diagonal, so a tile is entirely -inf and `-inf - (-inf) = NaN`. At ctx=22 no tile is fully
masked — which is exactly why the Q0 smoke (ctx=22) passed and the science config did not.
Fix: `finfo(float32).min`. Forward is bitwise identical (the exponent underflows to 0 either
way) — proven by `test_finite_mask_is_bitwise_identical_on_cpu`; only the backward differs.

**Also corrected:** the "17x from sync_every" claim was WRONG. An A/A comparison measured
speedup 0.99; the 0.5 -> 8.4 steps/s jump was the NEFF **compile cache warming**, not
windowing. sync_every is back to 1 (its windowed engine also SIGHUP'd the compiler under
32-way launch).

**Engineering fixes shipped (`de6f52b`, 25/25 tests):**
- XLA-safe finite attention mask (+ CPU equivalence test).
- Health gate 1: NaN loss fails the run at the first eval.
- Health gate 2: recap < 0.5 by step 2000 fails the run (reference: 45/45 saturate by 500).
- Staggered lane launch (8 s) — the compile storm that SIGHUP'd neuronx-cc.
- Canary-gated launcher (`tools/launch_wave.py`): one run must prove the platform trains this
  exact config (and warm the cache) before 48 cores commit.
- Recompile tripwire -> telemetry (was false-positive killing healthy runs).
- systemd units for wave + launch (SSM child processes were dying with their parent).

**Next:** canary verdict -> wave (48 runs, 5 seeds/cell) -> first emergences -> Q2/Q3 on free
lanes -> branch matrix.


## 2026-08-07 (night) — EXPERIMENTS LIVE

**Last:** DD factorial + Q4 baseline RUNNING on all 32 NeuronCores of i-0c6939e339ff4192e
(launched ~23:50Z): 8 baseline seeds (q4_s0..7, = Q4 gate + none-control) + 8 pre-registered
cells {exact,paraphrase} x interval {50,500} x order {fixed,scrambled} x 3 seeds; rate=0.25,
pool=64; primary endpoint = emergence step of query_ctx>=0.625 (right-censored); ckpt_every=4000
+ {1000,2000,3000} early forks. Measured single-core rate 0.67 steps/s (bench wave-1; K=4 graph
compile ~5 min, now cached) -> full wave <=~50 h wall; S3 sync every 10 min. Q1 grid preempted
deliberately on user direction: single-proc rate captured, 32-proc efficiency will be computed
from the factorial run records themselves vs bench_n1 (intermediate grid waves served no
decision). Q2/Q3 fire on first freed lanes; if they fail, interpretation is scoped per the
failure matrix (platform becomes a factor) — collection is unaffected.

**Next:** monitor ticks every ~45 min (crashes/retries/emergences); Q2+Q3 on freed lanes;
aggregate.py after first emergences; branch matrix from the dense ckpts once cells have
pre/mid/post-emergence coverage.

**Blockers:** none.


## 2026-08-07 (Day 1, late) — box LIVE, G0 complete

**Last:**
- 🚀 `i-0c6939e339ff4192e` (trn1.32xlarge) launched into `cr-0d45dc9efdb38c384` (Sam OK'd,
  user executed the launch command). Bootstrap v2 complete: plain `pytorch_2_8` venv pinned
  (torch 2.8 on this AMI, NOT 2.9 — risk #1 resolved by checking on box), env in
  `~/devaxis-work/env.sh` (DLAMI ships `.bashrc` root-owned — documented quirk), sync timer +
  deadline guard live from first boot. Neuron compiler `neuronxcc-2.23.6484.0`.
- **Q0 preflight PASS [MEASURED]:** 16 devices/32 cores; bf16 matmul value-correct; 155.5 GB
  disk; S3 write-read-back; 384.4 h left; 32-rank all-reduce == 496.0 exactly; compile cache
  serving cached NEFFs. Gate JSON: `gates/q0_preflight.json` (synced to S3 by the timer).
- **G0 measurement gate COMPLETE: 18/18 tests green.** Slow suite passed after two honest
  iterations: (1) emergence is stochastic ACROSS DATA STREAMS at fixed seed → clean arm pinned
  to measured-emergent stream `probe_small_s0`; (2) offset −1 is NOT a valid position mutation —
  answer partially decodable at the entity token (0.695 vs chance 0.5, represent-before-use);
  offset −2 (QMARK, query not yet revealed) is information-theoretically chance (measured
  0.4375). Detectors validated: constant_loss, detached_head, random_labels (srand 0.531 ≈
  chance while pinned clean 1.0), wrong_eval_position (good 0.984 / off 0.4375).
- **Probe complete (6 arms, 12k budget):** dense vocab emerged 2/3 (1500, 4800), default 1/3
  (4500), rest censored — calibrates Phase-F seed counts.
- Mistake logged: first probe launch ran python from /tmp on cpu-angad and hit the documented
  `/tmp/inspect.py` shadow — all 6 arms crashed at import; relaunched from `~/devaxis/tools/`.

**Next:** Q0 train smoke (in flight) → Q1 `bench_topology` {1,8,16,24,32} → Q2 no-op branch on
neuron (T1) → Q3 neuron legs vs the CPU yardstick (≤1.8e-05 / ≤2.5e-03) → Q4 8-seed baseline.

**Blockers:** none. (Linear/Slite still owed pending OAuth.)

## 2026-08-07 (Day 1) — evening close

**Last:**
- Repo live: github.com/RavulapalliManas/devaxis @c526f5c; clone + venv on cpu-angad
  (torch 2.13 cpu). Code tarball + TARBALL_COMMIT staged to
  `s3://pythia-fork-experiments-434457397267/devaxis/staging/`.
- **17/17 fast tests green** on cpu-angad, including bitwise T0 no-op branch and
  intervention-divergence; goldens committed (generator hashes + fp64 trajectory).
- **Q3 CPU yardstick [MEASURED]:** shared stream `q3data`, 200 steps, 2L/d64:
  max |fp32−fp64| windowed loss diff = 1.80e-06; final-param rel L2 = 2.54e-04.
  Neuron pass bar = 10× these. Artifacts: `s3://…/devaxis/reference/q3_cpu/` (11 objects).
- **trn1 launch dry-run VERIFIED** into `cr-0d45dc9efdb38c384` — requires
  `--instance-market-options MarketType=capacity-block` (dry-run caught this; no doc had it).
- **Detector validation, honest status:** constant_loss + detached_head VALIDATED (fast suite).
  random_labels + wrong_eval_position **NOT YET VALIDATED** — the slow test SKIPPED because the
  clean tiny run did not emerge in 4000 steps (recap 1.0 by step 400; qctx at chance for 4000
  steps, max 0.672 — the read/use lag reproduced in miniature; emergence is stochastic and the
  budget was naive). 6-arm probe now running on cpu-angad (3 seeds × {default vocab, dense
  ne=no=8 vocab}, 12k budget, stop_at 0.9) to find a fast-emerging config for the detector test.
- Q4 reference band measured from the 45 sweep files: K=4 D=32 bs=128 lr=3e-3 wd=0.1 warmup=500
  const, 120k budget, nparam 4,920,832; p=1.0 emergence {5.5k, 18.5k, 76k, cens, cens}.

**Next:**
- Probe results → bake winning config into test_audit (eval_every=100), rerun `pytest -m slow`,
  commit. THEN detector validation is complete; G0 clean before any Trainium hour.
- Day 3 (Aug 9): DRY=0 launch, bootstrap, preflight, Q0, guard rehearsal, Q1.

**Blockers:**
- **Sam's sign-off on `cr-0d45dc9efdb38c384`** — owed before the Aug 9 launch. (User to obtain.)
- Linear/Slite logging blocked on interactive OAuth (user must complete browser flow).

**Artifacts:** run JSONs + ckpts on cpu-angad `~/devaxis/runs/`; S3 `devaxis/` prefix;
plan `~/.claude/plans/dapper-skipping-perlis.md`; PERSEUS_ONBOARD §0.1 entry 2026-08-07h.
