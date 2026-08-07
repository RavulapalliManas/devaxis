# devaxis

Developmental-pretraining toolkit — the Trainium slice: qualification gates (Q0–Q4) plus the
DD recurrence/spacing/order factorial with an exact-branch matrix, on one trn1.32xlarge
(32 independent single-core replicas of a ~5M-param GPT on the K-binding task).

Lineage: the generator, model, and training loop are ports of flagship-04's `lag_law.py` /
`critical_period.py` (with the resume-LR bug fixed and regression-tested); the ops discipline is
the H100 pretraining playbook's.

## Invariants (non-negotiable)

1. **Data is a pure function.** Every batch = f(stream_id, "train", step) via `generators/keys.py`.
   No loader state; the cursor is the step. Branches replay bytes exactly.
2. **One writer per output path.** The S3 prefix `s3://pythia-fork-experiments-434457397267/devaxis/`
   is written only by the box's sync timer; run JSONs only by their own engine process.
3. **S3 or it didn't happen.** The capacity block TERMINATES 2026-08-23 11:30 UTC and local disk
   is destroyed. `analysis/verify.py --s3-prefix` audits this nightly.
4. **No number without a file and a script.** Run JSONs are the primary artifacts;
   `analysis/aggregate.py` (tables) / `analyse` (stats) / `verify.py` (invariants) — three
   scripts, not a framework. n is counted from files, never from queue length.
5. **The graph set is frozen.** On neuron: two graphs (train, eval); a recompile after step 500
   crashes the run on purpose. Precision contract: fp32 everywhere except bf16 matmuls under
   autocast; `--auto-cast=none`; stochastic rounding off.
6. **Measurements must fail under sabotage** (`audit/mutations.py`): a battery that can't detect
   its own corruption is not a measurement.

## Quickstart (CPU)

```bash
pip install -e .[dev] && pip install torch --index-url https://download.pytorch.org/whl/cpu
pytest -m "not slow"                     # fast suite
pytest -m slow                           # detector validation (~minutes)
python -m training.train --manifest configs/tiny_cpu.json --backend cpu
```

## Trainium sequence

Day-3 order: `platforms/neuron/launch_trn1.sh` (DRY=0) → `bootstrap.sh` on the box →
`preflight.py` + `torchrun --nproc_per_node=32 preflight.py --allreduce` (Q0) →
`bench_topology.py` (Q1) → branch/no-op certs (Q2) → precision legs (Q3) → 8-seed baseline (Q4)
→ Phase-F waves via `topology.py --queue queue.jsonl`.

Gate outputs land in `gates/*.json`; every gate has a numeric pass criterion recorded in the file.
