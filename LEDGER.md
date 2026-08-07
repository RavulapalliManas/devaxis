# devaxis ledger

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
