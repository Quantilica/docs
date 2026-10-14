"""Mede SidraClient (sync) × AsyncSidraClient na busca de metadados de vários agregados.

Usa a API pública do IBGE. Resultado: mediana de N rodadas por modo, em segundos.

    uv run python docs/benchmarks/measure_sidra_async.py --out docs/benchmarks/sidra-async.json
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import statistics
import time
from pathlib import Path

from sidra_fetcher.fetcher import AsyncSidraClient, SidraClient

IDS = [1737, 1620, 5938, 4099, 6381, 1705, 1612, 200]


def run_sync() -> float:
    t0 = time.perf_counter()
    with SidraClient() as client:
        for agregado_id in IDS:
            client.get_agregado_metadados(agregado_id)
    return time.perf_counter() - t0


async def _gather() -> None:
    client = AsyncSidraClient()
    try:
        await asyncio.gather(*(client.get_agregado_metadados(i) for i in IDS))
    finally:
        await client.aclose()


def run_async() -> float:
    t0 = time.perf_counter()
    asyncio.run(_gather())
    return time.perf_counter() - t0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--runs", type=int, default=5)
    args = ap.parse_args()
    run_sync(), run_async()  # aquecimento
    sync_t, async_t = [], []
    for _ in range(args.runs):  # alterna os modos para diluir variações da rede
        sync_t.append(run_sync())
        async_t.append(run_async())
    result = {
        "date": dt.date.today().isoformat(),
        "what": "get_agregado_metadados de 8 agregados (API de agregados do IBGE)",
        "agregados": IDS,
        "runs": args.runs,
        "sync_s": sync_t,
        "async_s": async_t,
        "sync_median_s": statistics.median(sync_t),
        "async_median_s": statistics.median(async_t),
        "speedup": statistics.median(sync_t) / statistics.median(async_t),
    }
    args.out.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    print(
        f"sync {result['sync_median_s']:.2f}s | async {result['async_median_s']:.2f}s | "
        f"{result['speedup']:.1f}x"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
