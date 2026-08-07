"""The training loop.  One backend.sync() per step; exactly TWO stable graphs on neuron
(train-step, eval-step); any recompile after the probe step is a loud crash, not a slow leak.

The manifest is the only input.  Data is a pure function of (stream_id, "train", step) — see
generators/keys.py — so the loop holds no loader state and a resume at step s replays exactly
what the parent would have seen at step s.

XLA discipline, all of it, lives in this file:
  * host reads (.item()) happen only at eval boundaries;
  * checkpoints are written only immediately after sync();
  * eval is a second graph, compiled once (fixed shapes, force_loss=True);
  * after COMPILE_PROBE steps the compile counter must be static (allow_recompile overrides).
"""
from __future__ import annotations
import hashlib
import json
import os
import time
import numpy as np
import torch
import torch.nn.functional as F

from generators import binding, keys
from generators.binding import Vocab, seq_len
from training.model import GPT, nparam
from training import checkpoint
from training.backends import make_backend
from training.optim import lr_at, set_lr, make_optimizer, parse_schedule, p_at
from diagnostics import battery

COMPILE_PROBE = 500          # steps after which the graph set must be frozen (neuron)

DEFAULTS = dict(logit_every=1000, ckpt_every=0, ckpt_at=[], stop_at=0.0, precision="fp32",
                eval_n=512, eval_bs=128, allow_recompile=False, attn="mha")


def manifest_hash(man: dict) -> str:
    return hashlib.sha256(json.dumps(man, sort_keys=True).encode()).hexdigest()[:16]


def stream_id_for(streams, step: int) -> str:
    sid = streams[0]["stream_id"]
    for s in streams:
        if step >= s["from_step"]:
            sid = s["stream_id"]
        else:
            break
    return sid


def run(man: dict, backend_name: str, mutate: str | None = None) -> dict:
    m = {**DEFAULTS, **man}
    run_id, out_dir = m["run_id"], m["out_dir"]
    K, D = m["task"]["K"], m["task"]["D"]
    v = Vocab(**m.get("vocab", {}))
    ctx = seq_len(K, D)
    sched = parse_schedule(str(m["p_schedule"]))
    streams = sorted(m.get("data_streams", [dict(from_step=0, stream_id=run_id)]),
                     key=lambda s: s["from_step"])
    ckpt_set = set(m["ckpt_at"])
    eval_every, steps = m["eval_every"], m["steps"]
    assert all(c % eval_every == 0 for c in ckpt_set), "ckpt steps must sit on the eval grid"
    precision = m["precision"]

    be = make_backend(backend_name)
    dev = be.device()
    torch.manual_seed(m["init_seed"])
    np.random.seed(m["init_seed"])
    model = GPT(v.size, d=m["model"]["d"], nl=m["model"]["nl"], nh=m["model"]["nh"],
                ctx=ctx, attn=m.get("attn", "mha")).to(dev)
    if precision == "fp64":
        assert backend_name == "cpu", "fp64 is the CPU oracle leg only"
        model = model.double()
    opt = make_optimizer(model, m["lr"], m["wd"])
    mhash = manifest_hash(man)

    step0 = 0
    if m.get("resume_ckpt"):
        step0 = checkpoint.load(m["resume_ckpt"], model, opt, m["lr"], m["warmup"])

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{run_id}.json")
    ckpt_dir = os.path.join(out_dir, "ckpt", run_id)
    rec = dict(run_id=run_id, parent_run_id=m.get("parent_run_id"), fork_step=m.get("fork_step"),
               manifest=man, manifest_hash=mhash, step0=step0, backend=be.name,
               precision=precision, mutate=mutate, nparam=nparam(model), ctx=ctx,
               generator_version=binding.GENERATOR_VERSION, torch=torch.__version__,
               chance_query_ctx=1.0 / K, chance_query_all=1.0 / v.no,
               evals=[], audit=dict(grad_total=[], grad_head=[], loss=[]))

    print(f"[devaxis] {run_id} backend={be.name} step0={step0}->{steps} K={K} D={D} "
          f"bs={m['bs']} params={rec['nparam']/1e6:.2f}M ctx={ctx} chance={1/K:.4f}", flush=True)

    audit_active = mutate is not None or m.get("audit_mode", False)
    loss_acc, loss_n = None, 0
    compile_baseline = None
    last_ckpt = None
    t0 = time.time()
    hits = 0

    for step in range(step0, steps + 1):
        if step % eval_every == 0:
            model.eval()
            mm = battery.behavioral(model, K, D, v, dev, n=m["eval_n"], bs=m["eval_bs"],
                                    want_logit_stats=(step % m["logit_every"] == 0),
                                    ans_offset=(-2 if mutate == "wrong_eval_position" else 0))
            be.sync()
            ev = dict(step=step, p_now=p_at(sched, step), lr=lr_at(step, m["lr"], m["warmup"]),
                      wall=time.time() - t0, **mm)
            if loss_n:
                ev["train_loss_mean"] = float(loss_acc.item()) / loss_n
                loss_acc, loss_n = None, 0
            if be.name == "neuron" and step >= step0 + COMPILE_PROBE:
                c = be.compile_count()
                if compile_baseline is None:
                    compile_baseline = c
                    ev["compile_count"] = c
                elif c is not None and c > compile_baseline and not m["allow_recompile"]:
                    rec["failed"] = f"recompile after probe: {compile_baseline} -> {c}"
                    with open(out_path, "w") as f:
                        json.dump(rec, f)
                    raise RuntimeError(rec["failed"] + "\n" + be.metrics().get("report", ""))
            rec["evals"].append(ev)
            with open(out_path, "w") as f:
                json.dump(rec, f)                        # incremental: a dead box costs one eval
            if step % (eval_every * 8) == 0:
                print(f"[devaxis] {run_id} step={step:>7} p={ev['p_now']:.2f} "
                      f"recap={mm['recap']:.3f} qctx={mm['query_ctx']:.3f} "
                      f"[{ev['wall']/60:.1f}m]", flush=True)
            if m["stop_at"] > 0 and mm["query_ctx"] >= m["stop_at"] and step > step0 + 1000:
                hits += 1
                if hits >= 2:
                    print(f"[devaxis] {run_id} converged at {step}", flush=True)
                    break
            else:
                hits = 0
            model.train()

        if step > step0 and (step in ckpt_set or (m["ckpt_every"] and step % m["ckpt_every"] == 0)):
            be.sync()
            checkpoint.save(os.path.join(ckpt_dir, f"step{step}.pt"),
                            model, opt, step, m["lr"], m["warmup"], mhash, be)
            last_ckpt = step

        if step == steps:
            break

        rng = keys.key(stream_id_for(streams, step), "train", step)
        b = binding.build_batch(m["bs"], K, D, p_at(sched, step), rng, v)
        ids = torch.from_numpy(b["ids"]).to(dev)
        tgt = torch.from_numpy(b["tgt"]).to(dev)
        if mutate == "random_labels":
            ap = torch.from_numpy(b["ans_pos"]).to(dev)
            r = torch.arange(m["bs"], device=dev)
            sup = tgt[r, ap] >= 0
            vals = tgt[r, ap][sup]
            perm = torch.from_numpy(rng.permutation(int(sup.sum()))).to(dev)
            newv = tgt[r, ap].clone()
            newv[sup] = vals[perm]
            tgt[r, ap] = newv

        with be.autocast(precision == "bf16_autocast"):
            logits, _ = model(ids)
        if precision == "bf16_autocast":
            logits = logits.float()                      # CE and reductions stay fp32
        if mutate == "detached_head":
            logits = logits.detach()
        loss = F.cross_entropy(logits.reshape(-1, v.size), tgt.reshape(-1), ignore_index=-100)
        if mutate == "constant_loss":
            loss = torch.ones_like(loss)
        opt.zero_grad(set_to_none=True)
        if loss.requires_grad:
            loss.backward()
        gn = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        set_lr(opt, lr_at(step, m["lr"], m["warmup"]))   # BEFORE step — the CP-bug fix
        opt.step()
        loss_acc = loss.detach() if loss_acc is None else loss_acc + loss.detach()
        loss_n += 1
        be.sync()

        if audit_active:                                 # host reads: audit runs are CPU-only
            hg = model.head.weight.grad
            rec["audit"]["grad_total"].append(float(gn))
            rec["audit"]["grad_head"].append(0.0 if hg is None else float(hg.norm()))
            rec["audit"]["loss"].append(float(loss.detach()))

    # final checkpoint: early-stop lands exactly at the converged states the branch matrix
    # wants to fork, so never lose them
    if (ckpt_set or m["ckpt_every"]) and step > step0 and step != last_ckpt:
        be.sync()
        checkpoint.save(os.path.join(ckpt_dir, f"step{step}.pt"),
                        model, opt, step, m["lr"], m["warmup"], mhash, be)

    rec["done"] = True
    with open(out_path, "w") as f:
        json.dump(rec, f)
    print(f"[devaxis] DONE {run_id} -> {out_path}", flush=True)
    return rec
