"""Mede o ganho de baixar arquivos em paralelo (threads) com o HttpClient do core.

Baixa os 12 ZIPs mensais mais recentes de `fi-inf-diario` (CVM) com 1, 4 e 8
threads, cada thread com o seu `HttpClient`, como faz o `sync` do `FetcherApp`.
Cada rodada usa uma pasta nova (nada é reaproveitado). Alterna os modos para
diluir variações da rede.

    uv run python docs/benchmarks/measure_downloads.py --out docs/benchmarks/downloads.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import statistics
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from cvm_fetcher.plugin import fetcher
from quantilica.core.http import HttpClient

GROUP = "fi-inf-diario"
N_FILES = 12


def run(urls: list[str], workers: int) -> tuple[float, int]:
    local = threading.local()
    clients: list[HttpClient] = []

    def client() -> HttpClient:
        if not hasattr(local, "c"):
            local.c = HttpClient()
            clients.append(local.c)
        return local.c

    tmp = Path(tempfile.mkdtemp(prefix="dl-bench-"))
    try:

        def one(url: str) -> int:
            dest = tmp / url.rsplit("/", 1)[1]
            client().download_with_manifest(
                url,
                dest,
                source_id="cvm",
                dataset_id=GROUP,
                producer="docs-benchmark",
                force=True,
            )
            return dest.stat().st_size

        t0 = time.perf_counter()
        with ThreadPoolExecutor(workers) as ex:
            total = sum(ex.map(one, urls))
        return time.perf_counter() - t0, total
    finally:
        for c in clients:
            c.close()
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--modes", type=int, nargs="*", default=[1, 4, 8])
    args = ap.parse_args()

    entries = fetcher.list_datasets(GROUP)[-N_FILES - 1 : -1]  # sem o mês corrente, incompleto
    urls = [e["url"] for e in entries]
    times: dict[int, list[float]] = {w: [] for w in args.modes}
    nbytes = 0
    for r in range(args.runs):
        for w in args.modes:
            t, nbytes = run(urls, w)
            times[w].append(t)
            print(
                f"rodada {r + 1} | {w} thread(s): {t:.1f}s ({nbytes / 2**20:.0f} MiB)",
                flush=True,
            )
    med = {w: statistics.median(v) for w, v in times.items()}
    base = med[args.modes[0]]
    result = {
        "date": dt.date.today().isoformat(),
        "what": f"{len(urls)} ZIPs mensais de {GROUP} (CVM), ~{nbytes / 2**20:.0f} MiB no total",
        "files": [u.rsplit("/", 1)[1] for u in urls],
        "bytes": nbytes,
        "runs": args.runs,
        "seconds": {str(w): v for w, v in times.items()},
        "median_s": {str(w): m for w, m in med.items()},
        "speedup_vs_first": {str(w): base / m for w, m in med.items()},
    }
    args.out.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    print({w: f"{base / m:.1f}x" for w, m in med.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
