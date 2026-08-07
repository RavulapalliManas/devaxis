# devaxis ledger

## 2026-08-07 (Day 1)

**Last:**
- Plan approved (`~/.claude/plans/dapper-skipping-perlis.md`). Repo scaffolded from scratch;
  lag_law generator/model ported (vectorized, keyed-Philox pure-function data), CP resume-LR bug
  fixed by construction + regression test; checkpoint/branch engine + difference certificates;
  audit mutations; neuron platform scripts (launch/bootstrap/preflight/topology/bench/guard/sync).
- AWS dry-run launch into `cr-0d45dc9efdb38c384` VERIFIED ("would have succeeded") — the
  non-obvious flag is `--instance-market-options MarketType=capacity-block`.
- Q4 reference params measured from the 45-run sweep files (K=4 D=32 bs=128 lr=3e-3 warmup=500
  const, 120k budget, nparam=4,920,832; p=1.0 emergence {5.5k, 18.5k, 76k, cens, cens}).

**Next:**
- Push to GitHub (RavulapalliManas/devaxis, private); clone on cpu-angad; venv; `pytest -m "not slow"`;
  `python -m tests.regen_goldens` on cpu-angad; commit goldens; run `pytest -m slow` (detector
  validation); fp64 Q3 CPU legs overnight on cpu-angad.
- Day 3 (Aug 9): launch box, bootstrap, Q0/Q1. **Blocker to clear first: Sam's sign-off on the CR.**

**Blockers:**
- Sam's sign-off on `cr-0d45dc9efdb38c384` (owner tag is his). Owed before Aug 9 launch.

**Artifacts:** this repo; plan file; session-bus entry `devaxis-trainium`.
