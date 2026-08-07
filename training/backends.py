"""One interface, three accelerators.  Everything XLA-specific lives here and in engine.py's
sync-placement discipline; nothing else in the repo may import torch_xla.

Precision contract (part of the Q3 numerical-equivalence certificate):
  fp32          — no autocast anywhere (Q3 reference legs).
  fp64          — model.double(), cpu only (Q3 oracle leg).
  bf16_autocast — params/optimizer/LayerNorm fp32; matmuls bf16 under torch.autocast; CE/loss
                  computed in fp32 OUTSIDE the autocast region (engine calls logits.float()).
On neuron the compiler must not override this: bootstrap pins NEURON_CC_FLAGS="--auto-cast=none"
and NEURON_RT_STOCHASTIC_ROUNDING_EN=0 (stochastic rounding would break deterministic replay).
"""
from __future__ import annotations
import contextlib
import torch


class Backend:
    name = "cpu"
    autocast_device = "cpu"

    def device(self):
        return torch.device("cpu")

    def sync(self):
        pass

    def save(self, obj, path):
        torch.save(obj, path)

    def compile_count(self):
        """Number of graph compiles so far; None where the concept does not exist."""
        return None

    def metrics(self) -> dict:
        return {}

    def autocast(self, enabled: bool):
        if not enabled:
            return contextlib.nullcontext()
        return torch.autocast(device_type=self.autocast_device, dtype=torch.bfloat16)


class CudaBackend(Backend):
    name = "cuda"
    autocast_device = "cuda"

    def device(self):
        return torch.device("cuda")

    def sync(self):
        torch.cuda.synchronize()


class NeuronBackend(Backend):
    name = "neuron"
    autocast_device = "xla"

    def __init__(self):
        import torch_xla  # noqa: F401  — only this module may import it
        import torch_xla.core.xla_model as xm
        self._xla = __import__("torch_xla")
        self._xm = xm
        try:
            import torch_xla.debug.metrics as met
            self._met = met
        except Exception:
            self._met = None

    def device(self):
        return self._xm.xla_device()

    def sync(self):
        if hasattr(self._xla, "sync"):
            self._xla.sync()
        else:
            self._xm.mark_step()

    def save(self, obj, path):
        self._xm.save(obj, path)

    def compile_count(self):
        if self._met is None:
            return None
        for name in ("UncachedCompile", "CachedCompile"):
            try:
                v = self._met.counter_value(name)
                if name == "UncachedCompile" and v is not None:
                    return int(v)
            except Exception:
                pass
        try:
            d = self._met.metric_data("CompileTime")
            return int(d[0]) if d else None
        except Exception:
            return None

    def metrics(self) -> dict:
        if self._met is None:
            return {}
        try:
            return {"report": self._met.metrics_report()}
        except Exception:
            return {}


def make_backend(name: str) -> Backend:
    if name == "cpu":
        return Backend()
    if name == "cuda":
        return CudaBackend()
    if name == "neuron":
        return NeuronBackend()
    raise ValueError(f"unknown backend {name!r}")
