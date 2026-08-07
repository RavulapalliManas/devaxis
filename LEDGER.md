# devaxis ledger

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
