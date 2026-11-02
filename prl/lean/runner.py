"""Run a Lean source file under the pinned toolchain with a wall-clock guard and parse messages."""
from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from prl.config import PATHS, ensure_dir, lean_env, study_config

_HDR = re.compile(r"^Main\.lean:(\d+):(\d+): (error|warning|info)(?:\([^)]*\))?: ?", re.M)


@dataclass(frozen=True)
class Msg:
    line: int
    col: int
    severity: str
    text: str


@dataclass
class LeanRun:
    returncode: int
    messages: list[Msg]
    stdout: str
    elapsed_s: float
    timeout: bool
    infra_error: str | None = None
    extra: dict = field(default_factory=dict)

    def errors(self) -> list[Msg]:
        return [m for m in self.messages if m.severity == "error"]


def parse_messages(out: str) -> list[Msg]:
    out = out.replace("\r\n", "\n")
    hdrs = list(_HDR.finditer(out))
    msgs = []
    for i, h in enumerate(hdrs):
        end = hdrs[i + 1].start() if i + 1 < len(hdrs) else len(out)
        msgs.append(Msg(int(h.group(1)), int(h.group(2)), h.group(3), out[h.end():end].rstrip("\n")))
    return msgs


_SEM_LOCK = threading.Lock()
_SEM: threading.BoundedSemaphore | None = None


def set_workers(n: int) -> None:
    global _SEM
    with _SEM_LOCK:
        _SEM = threading.BoundedSemaphore(max(1, n))


def _sem() -> threading.BoundedSemaphore:
    global _SEM
    with _SEM_LOCK:
        if _SEM is None:
            _SEM = threading.BoundedSemaphore(int(os.environ.get("PRL_LEAN_WORKERS", "6")))
        return _SEM


def _kill_tree(proc: subprocess.Popen) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, timeout=30)
        else:
            os.killpg(proc.pid, 9)
    except Exception:  # noqa: BLE001
        pass
    try:
        proc.kill()
    except Exception:  # noqa: BLE001
        pass


# --------------------------------------------------------------------------- REPL backend
# `lean_env/PrlRepl.lean` (our own server) imports Mathlib once per process and elaborates each
# request against a fresh copy of that environment: ~0.6 s per check instead of ~25-40 s.

REPL_EXE = PATHS.lean_env / ".lake" / "build" / "bin" / ("prlrepl.exe" if os.name == "nt" else "prlrepl")
_SEV = {"error": "error", "warning": "warning", "information": "info"}


def _mem_limit_bytes() -> int:
    gb = os.environ.get("PRL_LEAN_MEM_GB")
    if gb is None:
        try:
            from prl.config import study_config
            gb = str(study_config()["lean"].get("mem_limit_gb", 4))
        except Exception:  # noqa: BLE001
            gb = "4"
    return int(float(gb) * 2**30)
_DEAD_CPU = 0.0
_DEAD_LOCK = threading.Lock()


def dead_worker_cpu_seconds() -> float:
    """CPU seconds consumed by Lean workers that have since been killed (for energy accounting)."""
    with _DEAD_LOCK:
        return _DEAD_CPU


def _record_cpu(pid: int) -> None:
    global _DEAD_CPU
    try:
        import psutil
        t = psutil.Process(pid).cpu_times()
        with _DEAD_LOCK:
            _DEAD_CPU += t.user + t.system
    except Exception:  # noqa: BLE001
        pass


def _limit_memory(pid: int, limit: int) -> bool:
    """Windows: put the process in a Job Object with a per-process memory cap (final architecture G3).
    Exceeding the cap makes the allocation fail and the worker die; the harness treats that as described
    in the failure taxonomy (re-run once in a fresh worker, then a candidate resource failure)."""
    if os.name != "nt" or limit <= 0:
        return False
    import ctypes
    from ctypes import wintypes

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in ("r_ops", "w_ops", "o_ops", "r_b", "w_b", "o_b")]

    class BASIC(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class EXTENDED(ctypes.Structure):
        _fields_ = [("Basic", BASIC), ("Io", IO_COUNTERS), ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.OpenProcess.restype = wintypes.HANDLE
    job = k32.CreateJobObjectW(None, None)
    if not job:
        return False
    info = EXTENDED()
    info.Basic.LimitFlags = 0x00000100  # JOB_OBJECT_LIMIT_PROCESS_MEMORY
    info.ProcessMemoryLimit = limit
    if not k32.SetInformationJobObject(wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info)):
        return False
    hproc = k32.OpenProcess(0x0001 | 0x0100, False, pid)  # PROCESS_TERMINATE | PROCESS_SET_QUOTA
    if not hproc:
        return False
    ok = bool(k32.AssignProcessToJobObject(wintypes.HANDLE(job), wintypes.HANDLE(hproc)))
    k32.CloseHandle(wintypes.HANDLE(hproc))
    return ok  # the job handle is intentionally kept open for the lifetime of the worker


def auto_workers(per_worker_gb: float = 3.0, reserve_gb: float = 4.0, cap: int = 6) -> int:
    """Lean workers that fit in currently free RAM (other jobs on the machine are respected)."""
    try:
        import psutil
        free = psutil.virtual_memory().available / 2**30
    except Exception:  # noqa: BLE001
        return 2
    return max(1, min(cap, int((free - reserve_gb) // per_worker_gb)))


class _ReplWorker:
    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None
        self.q: list[str] = []
        self.lines: queue.Queue[str | None] = queue.Queue()

    def _env(self) -> dict[str, str]:
        e = lean_env().env()
        tc_bin = str(Path(lean_env().lean_exe).parent)
        e["PATH"] = tc_bin + os.pathsep + e.get("PATH", "")
        return e

    def start(self) -> None:
        kwargs: dict = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        else:
            kwargs["start_new_session"] = True
        self.proc = subprocess.Popen([str(REPL_EXE)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, env=self._env(), text=True, encoding="utf-8",
                                     errors="replace", bufsize=1, **kwargs)
        self.mem_capped = _limit_memory(self.proc.pid, _mem_limit_bytes())
        self.lines = queue.Queue()
        proc = self.proc

        def pump() -> None:
            assert proc.stdout is not None
            for ln in proc.stdout:
                self.lines.put(ln)
            self.lines.put(None)

        threading.Thread(target=pump, daemon=True).start()
        first = self.lines.get(timeout=600)
        if not first or '"ready"' not in first:
            raise RuntimeError(f"prlrepl failed to start: {first!r}")

    def kill(self) -> None:
        if self.proc is not None:
            _record_cpu(self.proc.pid)
            _kill_tree(self.proc)
            self.proc = None

    def request(self, path: Path, wall_s: float) -> tuple[dict | None, bool, float]:
        if self.proc is None or self.proc.poll() is not None:
            self.start()
        assert self.proc is not None and self.proc.stdin is not None
        t0 = time.perf_counter()
        self.proc.stdin.write(str(path) + "\n")
        self.proc.stdin.flush()
        try:
            ln = self.lines.get(timeout=wall_s)
        except queue.Empty:
            self.kill()
            return None, True, time.perf_counter() - t0
        el = time.perf_counter() - t0
        if ln is None:  # process died (e.g. stack overflow / OOM inside elaboration)
            self.kill()
            return None, False, el
        return json.loads(ln), False, el


_POOL: queue.Queue[_ReplWorker] | None = None
_POOL_LOCK = threading.Lock()


def _pool() -> queue.Queue[_ReplWorker]:
    global _POOL
    with _POOL_LOCK:
        if _POOL is None:
            configured = int(study_config()["lean"].get("workers", 0))
            n = configured or auto_workers()
            override = os.environ.get("PRL_LEAN_WORKERS")
            if override is not None:
                n = max(1, int(override))
            _POOL = queue.Queue()
            for _ in range(n):
                _POOL.put(_ReplWorker())
        return _POOL


def set_repl_workers(n: int) -> None:
    global _POOL
    with _POOL_LOCK:
        if _POOL is not None:
            while not _POOL.empty():
                _POOL.get().kill()
        _POOL = queue.Queue()
        for _ in range(max(1, n)):
            _POOL.put(_ReplWorker())


def shutdown() -> None:
    global _POOL
    with _POOL_LOCK:
        if _POOL is not None:
            while not _POOL.empty():
                _POOL.get().kill()
        _POOL = None


def run_lean_repl(source: str, *, wall_s: float = 300) -> LeanRun:
    tmp = ensure_dir(PATHS.cache / "tmp" / uuid.uuid4().hex)
    path = tmp / "Main.lean"
    path.write_text(source, encoding="utf-8", newline="\n")
    pool = _pool()
    w = pool.get()
    try:
        try:
            res, timeout, el = w.request(path, wall_s)
        except Exception as e:  # noqa: BLE001
            w.kill()
            return LeanRun(-1, [], "", 0.0, False, infra_error=f"repl: {e}")
    finally:
        pool.put(w)
        shutil.rmtree(tmp, ignore_errors=True)
    if timeout:
        return LeanRun(-9, [], "", el, True)
    if res is None:
        return LeanRun(-1, [], "", el, False, infra_error="repl process died", extra={"died": True})
    if not res.get("ok"):
        return LeanRun(-1, [], "", el, False, infra_error="repl: " + str(res.get("error"))[:500])
    msgs = [Msg(int(m["line"]), int(m["col"]), _SEV.get(m["severity"], m["severity"]), m["text"])
            for m in res["messages"]]
    # synthesise CLI-like stdout so text-level parsers (axioms, eval markers) work for both backends
    out = "\n".join(f"Main.lean:{m.line}:{m.col}: {m.severity}: {m.text}" for m in msgs)
    rc = 1 if any(m.severity == "error" for m in msgs) else 0
    return LeanRun(rc, msgs, out, el, False)


def backend() -> str:
    b = os.environ.get("PRL_LEAN_BACKEND", "repl")
    if b == "repl" and not REPL_EXE.exists():
        return "cli"
    return b


def run_lean(source: str, *, wall_s: float = 300, keep: bool = False) -> LeanRun:
    if backend() == "repl" and not keep:
        return run_lean_repl(source, wall_s=wall_s)
    return run_lean_cli(source, wall_s=wall_s, keep=keep)


def run_lean_cli(source: str, *, wall_s: float = 300, keep: bool = False) -> LeanRun:
    env = lean_env()
    tmp = ensure_dir(PATHS.cache / "tmp" / uuid.uuid4().hex)
    try:
        (tmp / "Main.lean").write_text(source, encoding="utf-8", newline="\n")
        kwargs: dict = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        else:
            kwargs["start_new_session"] = True
        with _sem():
            t0 = time.perf_counter()
            try:
                proc = subprocess.Popen(
                    [env.lean_exe, "Main.lean"], cwd=tmp, env=env.env(), stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs,
                )
            except OSError as e:
                return LeanRun(-1, [], "", 0.0, False, infra_error=f"spawn: {e}")
            timeout = False
            try:
                out_b, _ = proc.communicate(timeout=wall_s)
            except subprocess.TimeoutExpired:
                timeout = True
                _kill_tree(proc)
                try:
                    out_b, _ = proc.communicate(timeout=30)
                except Exception:  # noqa: BLE001
                    out_b = b""
            elapsed = time.perf_counter() - t0
        out = out_b.decode("utf-8", errors="replace")
        infra = None
        rc = proc.returncode if proc.returncode is not None else -9
        if not timeout and rc not in (0, 1):
            infra = f"lean exited with code {rc}"
        if not timeout and rc == 1 and not _HDR.search(out):
            infra = "lean failed without diagnostics: " + out[-500:]
        return LeanRun(rc, parse_messages(out), out, elapsed, timeout, infra)
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)


def run_lean_retry(source: str, *, wall_s: float = 300, retries: int = 1) -> LeanRun:
    r = run_lean(source, wall_s=wall_s)
    while r.infra_error and retries > 0:
        retries -= 1
        time.sleep(2)
        r = run_lean(source, wall_s=wall_s)
    return r


def lean_version() -> str:
    env = lean_env()
    return subprocess.run([env.lean_exe, "--version"], capture_output=True, text=True).stdout.strip()


def tmp_cleanup() -> None:
    d = PATHS.cache / "tmp"
    if d.exists():
        for p in d.iterdir():
            shutil.rmtree(p, ignore_errors=True)


__all__ = ["Msg", "LeanRun", "run_lean", "run_lean_cli", "run_lean_repl", "run_lean_retry", "parse_messages", "set_workers", "set_repl_workers", "shutdown", "lean_version"]
