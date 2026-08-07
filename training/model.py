"""The lag_law GPT, ported verbatim (6L / d256 / 8h / learned pos-emb, 4.92M at default vocab).

Module creation order is IDENTICAL to lag_law.py, so torch.manual_seed(s) + construction yields the
same initial weights as the reference sweep at the same seed.  No dropout anywhere — device RNG is
never consumed by training math, which is what makes the exact-branch contract params+opt+step only.

attn="explicit" is a FALLBACK for the case that nn.MultiheadAttention miscompiles on neuronx-cc
(plan risk #3).  It has its own parameterization (separate q/k/v/o Linears), so switching implies
re-baselining under Q4 — it is not weight-compatible with "mha".
"""
from __future__ import annotations
import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class ExplicitAttention(nn.Module):
    def __init__(s, d, h):
        super().__init__()
        assert d % h == 0
        s.h, s.dk = h, d // h
        s.q = nn.Linear(d, d); s.k = nn.Linear(d, d); s.v = nn.Linear(d, d); s.o = nn.Linear(d, d)

    def forward(s, x, m):
        B, T, d = x.shape
        q = s.q(x).view(B, T, s.h, s.dk).transpose(1, 2)
        k = s.k(x).view(B, T, s.h, s.dk).transpose(1, 2)
        v = s.v(x).view(B, T, s.h, s.dk).transpose(1, 2)
        att = (q @ k.transpose(-2, -1)) / math.sqrt(s.dk) + m
        att = F.softmax(att.float(), dim=-1).to(v.dtype)
        y = (att @ v).transpose(1, 2).reshape(B, T, d)
        return s.o(y)


class Block(nn.Module):
    def __init__(s, d, h, attn="mha"):
        super().__init__()
        s.ln1 = nn.LayerNorm(d)
        if attn == "mha":
            s.att = nn.MultiheadAttention(d, h, batch_first=True)
        else:
            s.att = ExplicitAttention(d, h)
        s.attn_impl = attn
        s.ln2 = nn.LayerNorm(d)
        s.mlp = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Linear(4 * d, d))

    def forward(s, x, m):
        h = s.ln1(x)
        if s.attn_impl == "mha":
            a, _ = s.att(h, h, h, attn_mask=m, need_weights=False)
        else:
            a = s.att(h, m)
        x = x + a
        return x + s.mlp(s.ln2(x))


class GPT(nn.Module):
    def __init__(s, vocab, d=256, nl=6, nh=8, ctx=512, attn="mha"):
        super().__init__()
        s.tok = nn.Embedding(vocab, d); s.pos = nn.Embedding(ctx, d)
        s.blocks = nn.ModuleList([Block(d, nh, attn) for _ in range(nl)])
        s.lnf = nn.LayerNorm(d); s.head = nn.Linear(d, vocab, bias=False)
        s.ctx = ctx

    def forward(s, ids, want_hidden=False):
        T = ids.shape[1]
        m = torch.triu(torch.full((T, T), float("-inf"), device=ids.device, dtype=s.tok.weight.dtype), 1)
        x = s.tok(ids) + s.pos(torch.arange(T, device=ids.device))[None]
        hs = []
        for b in s.blocks:
            x = b(x, m)
            if want_hidden:
                hs.append(x)
        x = s.lnf(x)
        return s.head(x), hs


def nparam(model: nn.Module) -> int:
    return sum(q.numel() for q in model.parameters())
