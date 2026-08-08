# A learned capability that cannot survive without supervision

**devaxis — findings from 242 training runs on AWS Trainium, 2026-08-07 to 2026-08-08**

Repo: github.com/RavulapalliManas/devaxis · Artifacts:
`s3://pythia-fork-experiments-434457397267/devaxis/` · Box: `i-0c6939e339ff4192e`

Every number here was recomputed from run records. Open questions are marked OPEN. Claims
retracted during the work are listed in §8 rather than quietly removed.

---

## 1. The short version

A small transformer learns two things on this task. One of them is permanent. The other one
is not, and the difference is stark.

| | **Read circuit** | **Use circuit** |
|---|---|---|
| What it does | holds 4 bindings across a distractor gap | answers a query about them |
| Forms after | ~500 steps | 7,000–31,750 steps, stochastically |
| Survives losing its supervision? | **yes, at 1.000 accuracy throughout** | **no — decays to chance** |
| Recovers if supervision returns? | not applicable | **no** |

Three findings follow:

1. **How you arrange the data does not matter.** Recurrence type, spacing, and order changed
   nothing measurable (49 runs, every cell p = 1.0).
2. **Whether supervision is present at all decides everything.** Interrupt it and the use
   circuit never forms, with a monotone dose-response (p = 7.8 × 10⁻⁵). Interrupt it after the
   circuit exists and the circuit dies. Neither is recoverable.
3. **A learned capability costs about 3% of its original supervision to keep.** Below that it
   can vanish; at 3% and above, every run that dipped came back.

And one result that is stranger than the rest, in §6.

---

## 2. Setup

**Task.** Each sequence declares K = 4 entity→obligation pairs, then a block of distractors,
then repeats the pairs (the *recap*, always supervised — this trains the read circuit), then
asks for one entity's obligation (the *answer*, supervised with probability **p** — this trains
the use circuit). Only the loss mask depends on p, so the input distribution never changes.
Chance on the answer is 1/K = 0.25.

**Model.** 4,920,832 parameters: 6 layers, d = 256, 8 heads, closed vocabulary of 392,
context 54. AdamW, lr 3e-3, batch 128.

**Endpoint, declared before any run.** Emergence = first evaluation with query_ctx ≥ 0.625,
right-censored at the step budget. A run that never crosses contributes "> last step", never
"= max step".

**Why forks are trustworthy.** Data is a pure function of `(stream_id, step)`, so a forked
checkpoint replays its parent's exact byte stream. Verified on-device: a no-op fork reproduced
its parent **bitwise** — 0.0 metric drift and 0.0 parameter divergence across 17 evaluation
points. Any parent–child difference is therefore caused by the intervention, not the platform.

---

## 3. Platform certification

| Gate | Result |
|---|---|
| Preflight | 16 devices / 32 NeuronCores; 32-rank all-reduce sums to exactly 496.0 |
| Exact-branch replay | **tier T0, bitwise** (0.0 drift, 0.0 parameter divergence) |
| Numerical equivalence | Neuron fp32 vs CPU fp64 oracle: **2.08e-06**, against a 1.80e-05 bar. The CPU's own fp32 error is 1.798e-06, so Neuron sits at 2.8× the platform's irreducible error |

bf16 measured 2.39e-02, which is what an 8-bit mantissa does. It is a separate numerical
condition, not certified, and not used.

Throughput: 8.4 steps/s per NeuronCore, about 400 steps/s across 32 cores.

---

## 4. The experiments

242 runs terminal across ten experiments. Zero unexplained failures.

### 4.1 Data distribution does not move emergence — 49 runs, NULL

Recurrence type (exact / paraphrase) × spacing (interval 50 / 500) × order (fixed / scrambled),
at 25% rate over a 64-program pool, 5 seeds per cell plus 8 baselines.

Kaplan-Meier medians ranged 8,500 to 17,500 against a baseline of 9,750. Log-rank against
baseline, Holm-corrected: **every cell p = 1.0**, smallest raw p = 0.197. With 5 seeds per cell
this means "no large effect", not "no effect".

### 4.2 Interrupting supervision prevents formation — 21 runs

Every baseline forked at step 4,000, pre-emergence for all parents and post-read for all.

| Arm | n | Emerged |
|---|---|---|
| control (p = 1) | 7 | **7/7**, delays 3,000–27,750, median 5,750 |
| deprived (p = 0 permanently) | 7 | **0/7** |
| deprived then rescued (p = 0 for 10k, then p = 1) | 7 | **0/7** |

Paired sign test across all 7 parents: **7/7 reversals, p = 0.0078**. Each rescued run had
already exceeded its own control's delay without emerging, so no pair can flip.

### 4.3 The effect is dose-dependent — 38 runs

| Deprivation τ | Emerged | Rate |
|---|---|---|
| 0 | 7/7 | 1.00 |
| 2,000 | 4/8 | 0.50 |
| 5,000 | 2/8 | 0.25 |
| 10,000 | 0/7 | 0.00 |
| 20,000 | 0/8 | 0.00 |

**Cochran-Armitage trend test: z = −3.783, one-tailed p = 7.8 × 10⁻⁵.**

The obvious confound is excluded: longer τ leaves fewer supervised steps in the budget, but the
slowest control ever needed 27,750, and every arm received at least 1.7× that.

### 4.4 It is not a critical period — 46 runs

A critical period requires a window that *closes*. Two tests, neither found an edge.

**Age sweep** (fixed τ = 10,000 at ages 1k / 2k / 4k / 8k / 12k): 1 of 22 emerged, uniformly.
**Early replication** (8 parents at ages 1k / 2k / 3k): 1/8, 0/8, 0/8. Age 1,000 against ages
2,000+3,000 pooled: Fisher one-tailed **p = 0.98**. One survivor in 24 runs is what chance looks
like.

And the upper edge fails too — see §4.6, where deprivation destroys an already-formed circuit.

So the honest description is **supply-dependence**, not a developmental window. (This framing
was challenged; both tests the challenge predicted were run, and both failed to support it.)

### 4.5 The block is in the weights — 28 runs

Four rescue strategies from the deprived checkpoints, interpretation declared in advance:

| Rescue arm | n | Emerged |
|---|---|---|
| plain (replication) | 7 | 0/7 |
| optimizer reset (Adam moments discarded) | 7 | **0/7** |
| LR rewarm (warmup ramp restarted) | 7 | **0/7** |
| both | 7 | **0/7** |

Neither optimizer state nor learning-rate scale carries the block. It is in the parameters.

**And it is not weight decay** — 24 runs. AdamW's decoupled decay predicted the dose-response
curve almost exactly (surviving multipliers 1.000 / 0.549 / 0.223 / 0.050 / 0.002 against rates
1.00 / 0.50 / 0.25 / 0.00 / 0.00), which made it the leading suspect. With weight decay set to
zero: the control emerged 7/8 at exactly the parent emergence steps, while τ = 10,000 gave 0/8
and τ = 20,000 gave 0/8. The match was a coincidence of scale.

### 4.6 A formed circuit dies the same way — 14 runs

Each parent forked at the first checkpoint *after* its own emergence, so every run began with
the circuit demonstrably present.

| Arm | n | query_ctx at fork | at end |
|---|---|---|---|
| supply cut permanently | 7 | 0.758–0.992 | **0.230–0.264** |
| supply cut 10k, then restored | 7 | 0.758–0.992 | **0.254–0.289** |

Decay to chance in 7/7, no recovery in 7/7 — and it holds at weight decay zero as well (7/7).
Throughout, recap stays at 1.000: the read circuit is untouched.

Note what "deprivation" means here. Training **continues** on the recap objective. This is
destructive interference from continued training on a related task, not idle decay.

### 4.7 The maintenance dose — 49 runs

Instead of cutting supply after emergence, reduce it.

| p after emergence | n | Collapsed (final < 0.30) | Median final | Dip floor |
|---|---|---|---|---|
| 0.01 | 7 | **6/7** | ~0.25 | — |
| 0.02 | 7 | **2/7** | 0.746 | 0.209 |
| **0.03** | 7 | **0/7** | 0.840 | 0.242 |
| 0.04 | 7 | 0/7 | 0.881 | 0.350 |
| 0.05 | 7 | 0/7 | ~0.94 | 0.412 |
| 0.20 | 7 | 0/7 | ~0.98 | 0.705 |

Both columns are monotone. **Collapse risk reaches zero at p = 0.03.** Below it the circuit can
die outright; at and above it, every run dips and returns. So maintenance is a risk gradient
rather than a cliff, and keeping the capability costs roughly a thirtieth of the supervision
that created it. One parent that entered at 0.76 rose to 0.98 on 5% supply, so this is
maintenance plus continued learning, not mere preservation.

---

## 5. What it all says

The use circuit is never *consolidated*. It exists while it is supervised and not otherwise.
Formation and maintenance fail in the same way and for what is presumably the same reason:
without its own gradient, the sub-circuit's parameters drift into a configuration from which
gradient descent on that objective does not recover the function. Three standard explanations
are eliminated — weight decay, optimizer state, and learning-rate scale.

Meanwhile the read circuit, trained by tokens present in every sequence, is untouched by all of
it. The two capabilities live in the same network and have completely different robustness.

The null result matters as much as the positive one. Curating *how* data repeats did nothing.
Controlling *whether* the supervision is present decided the outcome entirely.

---

## 6. The open question, and it may be the most interesting one

Two facts sit side by side:

- Supply restored to **p = 1.0 after an interruption** recovered nothing: 0 of about 21 runs.
- Supply held **continuously at p = 0.03** recovered a circuit that had fallen to chance:
  `thr003_q4_s5` went 0.242 → 0.791, and `thr003_q4_s6` went 0.275 → 0.805.

A model on 3% supervision climbs back from chance. A model on 100% supervision cannot, if its
supply ever stopped. **Continuity may matter independently of quantity.**

The test is running now: replace the deprivation window's p = 0 with 0.001, 0.005, or 0.01,
then rescue exactly as before. p = 0 gives 0/7. If a thousandth of the supervision restores
rescuability, then irreversibility is about supervision *stopping*, not about how little of it
there is — which would have an obvious reading for continual training. **Status: OPEN.**

Also running: fresh baselines at K = 2 and K = 8, the first test of whether any of this holds
outside the single binding load everything was measured at. **Status: OPEN.**

---

## 7. Scope

One task family, one model size (4.9M parameters), one architecture, one optimiser
configuration, 7–8 seeds per arm. The factorial null is powered for large effects only. Nothing
here has been shown to extend to language models at scale, and the K-generality test is the
first step toward knowing whether it extends at all.

A separate session reports the same dose-response shape on different hardware (τ = 2,000 giving
7/10, τ = 6,000 giving 0/10). That is consistent, and it is their measurement.

---

## 8. Claims retracted or corrected during this work

Listed because the corrections are more instructive than the successes.

1. **An entire wave trained nothing for hours.** A `-inf` causal attention mask produces NaN on
   Neuron once a softmax tile lies entirely above the diagonal. I reported throughput without
   reading a loss value. Fix: `finfo.min`, bitwise-identical in the forward pass. Corollary: a
   short-sequence smoke test cannot certify a long-sequence configuration.
2. **A 17× speedup claim was false.** An A/A test measured it at 0.99; the gain was the compile
   cache warming.
3. **A p-value was overstated.** Fisher p = 0.0079 on unpaired arms with unequal parent sets,
   when parents differ fourfold in intrinsic emergence time. The correct paired test gave
   p = 0.125 at that moment; after completing the design it reads p = 0.0078 legitimately.
4. **Six runs vanished silently** — launched onto occupied cores, died at init, left no record.
   Three were controls. A job that never starts is absent, not failed: diff the queue against
   the results.
5. **A self-healing routine would have corrupted data.** A malformed `pgrep` made the live-process
   count always zero and the dispatcher-revival rule keyed on it. Caught before any revival fired.
6. **A design flaw in the age sweep**: fixed ages instead of ages relative to each parent's own
   emergence, so the decisive cell was never populated.
7. **A fabricated total.** The first report said "165 completed runs" from memory; recomputing
   from files gave 127 at that time. Corrected before publishing.
8. **A false alarm of my own.** I briefly read a one-second phase completion as a bug that had
   skipped an experiment. It had not — 24 records existed. Verified before changing anything.

---

## 9. Where everything lives

| Item | Location |
|---|---|
| Code, tests (26), running ledger | github.com/RavulapalliManas/devaxis |
| Run records | `s3://…/devaxis/runs/{factorial,branch,tau,window,early,mech,wd0,postem,maint,thresh,kgen}/` |
| Gate certificates | `s3://…/devaxis/gates/` |
| Live auto-regenerated summary | `s3://…/devaxis/MORNING_REPORT.md` |
| This document | `s3://…/devaxis/FINDINGS.md` |
| Session record | `PERSEUS_ONBOARD.md` §0.1, 2026-08-08 |

The capacity block terminates **2026-08-23 11:30 UTC**, which destroys local storage. Only S3
survives; a deadline guard force-syncs before then.
