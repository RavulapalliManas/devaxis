"""LR as a pure function of step, set BEFORE opt.step() — the critical_period.py bug class
(LR assigned after opt.step(), giving one 500x-oversized first step on every process start)
is structurally impossible here and regression-tested in tests/test_lr_schedule.py.

lr_at matches lag_law's `const` schedule exactly: LambdaLR with lambda s: min(1,(s+1)/warmup)
applies lambda(s) to optimizer step s, i.e. step s trains at base_lr * min(1,(s+1)/warmup).

foreach=False is pinned on ALL backends so the CPU reference and neuron run the same per-tensor
update loop (foreach batching changes reduction order and would poison Q3).
"""
from __future__ import annotations
import torch


def lr_at(step: int, base_lr: float, warmup: int) -> float:
    return base_lr * min(1.0, (step + 1) / warmup)


def set_lr(opt: torch.optim.Optimizer, lr: float) -> None:
    for g in opt.param_groups:
        g["lr"] = lr


def make_optimizer(model: torch.nn.Module, lr: float, wd: float) -> torch.optim.Optimizer:
    return torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd,
                             betas=(0.9, 0.95), foreach=False)


def parse_schedule(spec: str):
    """'1.0' or '0:0.0,20000:1.0' -> [(step, p)]; p(step) = last entry with start <= step.
    Same semantics as critical_period.parse_schedule."""
    try:
        return [(0, float(spec))]
    except ValueError:
        pass
    out = []
    for part in spec.split(","):
        s, v = part.split(":")
        out.append((int(s), float(v)))
    out.sort()
    assert out[0][0] == 0, "schedule must start at step 0"
    return out


def p_at(sched, step: int) -> float:
    v = sched[0][1]
    for s, x in sched:
        if step >= s:
            v = x
        else:
            break
    return v
