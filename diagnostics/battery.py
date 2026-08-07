"""Behavioral battery — the eval half of lag_law.collect + critical_period.answer_logit_stats.

Eval batches come from the shared EVAL stream (keys.eval_key(i)), so every run in the program is
evaluated on byte-identical data, and every eval point within a run re-uses the same batches
(the lag_law fixed-generator discipline).

query_ctx is the headline behavioral clock: argmax restricted to the K obligations present in
context (chance = 1/K, the honest present-token baseline).  Representation probes are deliberately
NOT in this slice — they are CPU-side AX machinery, added when AX experiments schedule them.

ans_offset exists for the audit's wrong_eval_position mutation: reading the logits one position off
must collapse query_ctx to chance on a competent model, or the battery's position indexing cannot
be trusted.
"""
from __future__ import annotations
import numpy as np
import torch
import torch.nn.functional as F

from generators import binding, keys


@torch.no_grad()
def behavioral(model, K: int, D: int, v: binding.Vocab, device,
               n: int = 512, bs: int = 128, want_logit_stats: bool = False,
               ans_offset: int = 0) -> dict:
    recap_hit = recap_n = 0
    q_all = q_ctx = q_n = 0
    t1 = t2 = 0
    ent, gold_mass, margin = [], [], []

    for i in range(max(1, n // bs)):
        b = binding.build_batch(bs, K, D, 1.0, keys.eval_key(i), v, force_loss=True)
        ids = torch.from_numpy(b["ids"]).to(device)
        tgt = torch.from_numpy(b["tgt"]).to(device)
        ap_true = torch.from_numpy(b["ans_pos"]).to(device)
        ap = ap_true + ans_offset                       # offset shifts the READ position only
        r = torch.arange(bs, device=device)

        logits, _ = model(ids)
        pred = logits.argmax(-1)

        rmask = tgt >= 0
        rmask[r, ap_true] = False                        # recap tokens only
        recap_hit += int((pred[rmask] == tgt[rmask]).sum())
        recap_n += int(rmask.sum())

        gold = tgt[r, ap_true]                           # force_loss=True puts gold in the mask
        q_all += int((pred[r, ap] == gold).sum())

        # present-token baseline: restrict the decision to the K obligations in context
        obl_ids = ids[:, 2:2 * K + 1:2]
        lg = logits[r, ap].float()
        sub = lg.gather(1, obl_ids)
        pick = obl_ids.gather(1, sub.argmax(-1, keepdim=True)).squeeze(1)
        q_ctx += int((pick == gold).sum())
        q_n += bs

        if want_logit_stats:
            pr = F.softmax(sub, -1)
            order = sub.argsort(-1, descending=True)
            pick1 = obl_ids.gather(1, order[:, :1]).squeeze(1)
            pick2 = obl_ids.gather(1, order[:, :2])
            t1 += int((pick1 == gold).sum())
            t2 += int((pick2 == gold[:, None]).any(1).sum())
            gi = (obl_ids == gold[:, None]).float().argmax(1)
            gold_mass.append(pr.gather(1, gi[:, None]).squeeze(1).cpu())
            ent.append((-(pr * pr.clamp_min(1e-9).log()).sum(-1)).cpu())
            s2 = pr.sort(-1, descending=True).values
            margin.append((s2[:, 0] - s2[:, 1]).cpu())

    out = dict(recap=recap_hit / max(recap_n, 1),
               query=q_all / max(q_n, 1),
               query_ctx=q_ctx / max(q_n, 1))
    if want_logit_stats:
        out["logit"] = dict(top1=t1 / q_n, top2=t2 / q_n,
                            ent=float(torch.cat(ent).mean()), ent_max=float(np.log(K)),
                            gold_mass=float(torch.cat(gold_mass).mean()),
                            margin=float(torch.cat(margin).mean()), n=q_n)
    return out
