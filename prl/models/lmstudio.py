"""LM Studio (OpenAI-compatible) client and model management."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass

import httpx

BASE_URL = os.environ.get("PRL_LMSTUDIO_URL", "http://localhost:1234")


class InfraError(RuntimeError):
    """Infrastructure failure (server down, model not loaded): retried, never charged to the model."""


@dataclass
class Completion:
    text: str
    tokens_in: int
    tokens_out: int
    finish_reason: str
    elapsed_s: float
    model: str


_THINK = re.compile(r"<think>.*?</think>", re.S)


def strip_think(text: str) -> str:
    text = _THINK.sub("", text)
    if "<think>" in text and "</think>" not in text:  # truncated reasoning: drop it
        text = text.split("<think>")[0]
    return text.strip()


class LMStudio:
    def __init__(self, base_url: str = BASE_URL, timeout_s: float = 600):
        self.base = base_url.rstrip("/")
        self.http = httpx.Client(timeout=timeout_s)
        self._lock = threading.Lock()
        self.loaded: str | None = None

    def complete(self, model: str, messages: list[dict[str, str]], *, seed: int, temperature: float,
                 top_p: float, max_tokens: int) -> Completion:
        body = {
            "model": model, "messages": messages, "temperature": temperature, "top_p": top_p,
            "max_tokens": max_tokens, "seed": seed, "stream": False,
            # hidden reasoning is disabled for every model: it would consume the token budget invisibly
            # (verified: reasoning_tokens == 0 with this flag in LM Studio 0.4.x)
            "reasoning_effort": "none",
        }
        delay = 1.0
        last: Exception | None = None
        for _ in range(7):
            t0 = time.perf_counter()
            try:
                r = self.http.post(f"{self.base}/v1/chat/completions", json=body)
                if r.status_code >= 500 or r.status_code in (404, 409, 429):
                    raise InfraError(f"HTTP {r.status_code}: {r.text[:300]}")
                r.raise_for_status()
                d = r.json()
                ch = d["choices"][0]
                msg = ch.get("message", {})
                text = msg.get("content") or ""
                if msg.get("reasoning_content"):
                    text = "<think>" + msg["reasoning_content"] + "</think>\n" + text
                u = d.get("usage", {})
                return Completion(text, int(u.get("prompt_tokens", 0)), int(u.get("completion_tokens", 0)),
                                  ch.get("finish_reason") or "", time.perf_counter() - t0, model)
            except (httpx.HTTPError, InfraError, KeyError, ValueError) as e:
                last = e
                time.sleep(delay)
                delay = min(delay * 2, 30)
        raise InfraError(f"LM Studio request failed: {last}")

    def models(self) -> list[str]:
        r = self.http.get(f"{self.base}/v1/models")
        r.raise_for_status()
        return [m["id"] for m in r.json().get("data", [])]

    # ------------------------------------------------------------------ model loading via `lms`
    def ensure_loaded(self, key: str, ctx: int = 8192, parallel: int = 4) -> None:
        with self._lock:
            if self.loaded == key and key in self._loaded_ids():
                return
            lms = shutil.which("lms") or os.path.expanduser("~/.lmstudio/bin/lms")
            subprocess.run([lms, "unload", "--all"], capture_output=True, timeout=300, encoding="utf-8", errors="replace")
            cmd = [lms, "load", key, "--context-length", str(ctx), "--gpu", "max", "-y", "--identifier", key]
            if parallel:
                cmd += ["--parallel", str(parallel)]
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=900, encoding="utf-8", errors="replace")
            if p.returncode != 0 and "--parallel" in cmd:
                cmd = cmd[: cmd.index("--parallel")]
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=900, encoding="utf-8", errors="replace")
            if p.returncode != 0:
                raise InfraError(f"lms load {key} failed: {p.stdout[-500:]} {p.stderr[-500:]}")
            self.loaded = key

    def _loaded_ids(self) -> list[str]:
        try:
            return self.models()
        except Exception:  # noqa: BLE001
            return []
