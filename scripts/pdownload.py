"""Parallel HTTP range downloader.

Used during environment setup because GitHub release assets are throttled
per connection on this network. Usage:

    python scripts/pdownload.py URL OUT_PATH [--parts 48]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import os
import sys
import time
import urllib.request


def _resolve(url: str) -> tuple[str, int]:
    req = urllib.request.Request(url, method="GET", headers={"Range": "bytes=0-0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        final = r.geturl()
        cr = r.headers.get("Content-Range")
        if not cr:
            raise RuntimeError("server does not support range requests")
        return final, int(cr.split("/")[-1])


def _fetch(url: str, start: int, end: int, path: str, retries: int = 20) -> int:
    done = os.path.getsize(path) if os.path.exists(path) else 0
    want = end - start + 1
    while done < want and retries > 0:
        try:
            hdr = {"Range": f"bytes={start + done}-{end}"}
            req = urllib.request.Request(url, headers=hdr)
            with urllib.request.urlopen(req, timeout=60) as r, open(path, "ab") as f:
                while True:
                    chunk = r.read(1 << 16)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
        except Exception:  # noqa: BLE001 - retry any network error
            retries -= 1
            time.sleep(2)
    if done != want:
        raise RuntimeError(f"part {start}-{end} incomplete: {done}/{want}")
    return done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out")
    ap.add_argument("--parts", type=int, default=48)
    a = ap.parse_args()

    url, size = _resolve(a.url)
    n = max(1, a.parts)
    step = -(-size // n)
    ranges = [(i * step, min(size, (i + 1) * step) - 1) for i in range(n) if i * step < size]
    tmpdir = a.out + ".parts"
    os.makedirs(tmpdir, exist_ok=True)
    t0 = time.time()
    with cf.ThreadPoolExecutor(len(ranges)) as ex:
        futs = [ex.submit(_fetch, url, s, e, os.path.join(tmpdir, f"{i:04d}")) for i, (s, e) in enumerate(ranges)]
        for f in cf.as_completed(futs):
            f.result()
    with open(a.out, "wb") as out:
        for i in range(len(ranges)):
            p = os.path.join(tmpdir, f"{i:04d}")
            with open(p, "rb") as f:
                out.write(f.read())
            os.remove(p)
    os.rmdir(tmpdir)
    dt = time.time() - t0
    print(f"downloaded {size} bytes in {dt:.0f}s ({size / max(dt, 1e-9) / 1e6:.2f} MB/s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
