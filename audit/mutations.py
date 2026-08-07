"""Metric-mutation audit (master-plan T2 mutation tests, pruned to this slice's machinery).

Each mutation is injected by engine.run(mutate=...) and MUST trip its named detector; a clean run
must trip none.  A measurement pipeline that cannot detect its own sabotage is not a measurement
(master-plan G0: fail -> stop science, repair instrumentation).

Mutations and their detectors:
  constant_loss       loss replaced by 1.0            -> zero grads AND loss == 1.0 exactly
  detached_head       logits detached before loss     -> zero grads, loss real (varies)
  random_labels       answer labels permuted in-batch -> eval query_ctx stays at chance while the
                                                         paired clean run exceeds it (test_audit)
  wrong_eval_position battery reads ans_pos - 1       -> query_ctx collapses to ~chance on a
                                                         competent model (test_audit)
"""
from __future__ import annotations

MUTATIONS = ["constant_loss", "detached_head", "random_labels", "wrong_eval_position"]


def detect(rec: dict) -> dict:
    """Given a finished run record with audit telemetry, return {mutation: fired?}."""
    aud = rec.get("audit", {})
    gt = aud.get("grad_total", [])
    ls = aud.get("loss", [])
    zero_grads = bool(gt) and max(gt) == 0.0
    const_loss = bool(ls) and all(x == 1.0 for x in ls)
    finals = [e for e in rec.get("evals", []) if "query_ctx" in e]
    qctx = finals[-1]["query_ctx"] if finals else None
    chance = rec.get("chance_query_ctx")
    return dict(
        constant_loss=zero_grads and const_loss,
        detached_head=zero_grads and not const_loss,
        at_chance=(qctx is not None and chance is not None and qctx <= chance + 0.12),
        final_query_ctx=qctx,
        chance=chance,
    )
