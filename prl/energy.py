"""Energy accounting.

* GPU: **measured** — NVML cumulative energy counter (mJ) of the GPU, read at block boundaries.
* CPU (Lean verification): **estimated** — CPU-seconds consumed by the Lean worker processes × a per-thread
  power figure (CPU base power / logical CPUs; i7-14650HX: 55 W / 24). Windows exposes no RAPL counters,
  so this is labelled as an estimate everywhere it is reported.
* CO2: energy × grid carbon intensity (configurable; default 0.716 kg/kWh, India CEA grid average).

Blocks: the driver runs (model, condition) blocks one after another and records one `EnergyBlock` per block;
within a block, energy is attributed to attempts in proportion to completion tokens (GPU) and Lean
seconds (CPU). Concurrent requests inside a block make finer attribution ill-defined.
"""
from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass

try:  # optional at import time so unit tests run without a GPU
    import pynvml  # type: ignore
except Exception:  # noqa: BLE001
    pynvml = None  # type: ignore

import psutil

_NVML_LOCK = threading.Lock()
_NVML_OK: bool | None = None


def _nvml() -> bool:
    global _NVML_OK
    with _NVML_LOCK:
        if _NVML_OK is None:
            try:
                pynvml.nvmlInit()  # type: ignore[union-attr]
                _NVML_OK = True
            except Exception:  # noqa: BLE001
                _NVML_OK = False
        return _NVML_OK


def gpu_energy_mj(index: int = 0) -> int | None:
    if pynvml is None or not _nvml():
        return None
    try:
        h = pynvml.nvmlDeviceGetHandleByIndex(index)
        return int(pynvml.nvmlDeviceGetTotalEnergyConsumption(h))
    except Exception:  # noqa: BLE001
        return None


def lean_cpu_seconds(proc_name: str = "prlrepl") -> float:
    """Total CPU seconds (user + system) of live Lean workers plus workers killed earlier in this process."""
    from prl.lean.runner import dead_worker_cpu_seconds

    tot = dead_worker_cpu_seconds()
    for p in psutil.process_iter(["name"]):
        try:
            if (p.info["name"] or "").lower().startswith(proc_name):
                t = p.cpu_times()
                tot += t.user + t.system
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return tot


@dataclass
class EnergyBlock:
    model: str
    condition: str
    t_start: float
    t_end: float = 0.0
    gpu_j: float | None = None
    lean_cpu_s: float = 0.0
    cpu_j_est: float = 0.0
    co2_g_est: float = 0.0

    def to_json(self) -> dict:
        return asdict(self)


class EnergyMeter:
    """Measure one (model, condition) block."""

    def __init__(self, model: str, condition: str, *, watts_per_thread: float, kg_per_kwh: float):
        self.block = EnergyBlock(model, condition, time.time())
        self.w = watts_per_thread
        self.kg = kg_per_kwh
        self._g0 = gpu_energy_mj()
        self._c0 = lean_cpu_seconds()

    def finish(self) -> EnergyBlock:
        b = self.block
        b.t_end = time.time()
        g1 = gpu_energy_mj()
        if self._g0 is not None and g1 is not None and g1 >= self._g0:
            b.gpu_j = (g1 - self._g0) / 1000.0
        b.lean_cpu_s = max(0.0, lean_cpu_seconds() - self._c0)
        b.cpu_j_est = b.lean_cpu_s * self.w
        total_j = (b.gpu_j or 0.0) + b.cpu_j_est
        b.co2_g_est = total_j / 3.6e6 * self.kg * 1000.0
        return b
