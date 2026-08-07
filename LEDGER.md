# devaxis ledger

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
