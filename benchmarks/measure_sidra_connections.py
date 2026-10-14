"""Mede o custo de não reaproveitar a conexão nos clientes do SIDRA e compara sync × async.

Os clientes HTTP do core só mantêm conexão persistente dentro do gerenciador de contexto
(``with`` / ``async with``). Fora dele, cada requisição abre e fecha o seu próprio cliente, com
novo handshake TLS.

* Fase 1, ``reuso``: 15 requisições pequenas em sequência (``get_agregado_periodos(1737)``) nos
  quatro modos (sync e async, com e sem gerenciador de contexto). Mediana do tempo por requisição.
* Fase 2, ``multi_agregado``: ``get_agregado_metadados`` de 8 agregados, sync em sequência contra
  async com ``gather``, ambos com gerenciador de contexto. Mostra mediana, mínimo e máximo: a API
  do IBGE tem rodadas de 0,5 s e de mais de 60 s, e essa variação domina a diferença entre os modos.

    uv run python docs/benchmarks/measure_sidra_connections.py \
        --out docs/benchmarks/data/sidra-connections.json
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import statistics
import time
from collections.abc import Callable
from pathlib import Path

from sidra_fetcher.fetcher import AsyncSidraClient, SidraClient

N_REQUESTS = 15
IDS = [1737, 1620, 5938, 4099, 6381, 1705, 1612, 200]


def _sync_seq(managed: bool) -> float:
    t0 = time.perf_counter()
    if managed:
        with SidraClient() as client:
            for _ in range(N_REQUESTS):
                client.get_agregado_periodos(1737)
    else:
        client = SidraClient()
        for _ in range(N_REQUESTS):
            client.get_agregado_periodos(1737)
    return (time.perf_counter() - t0) / N_REQUESTS


async def _async_seq(managed: bool) -> float:
    t0 = time.perf_counter()
    if managed:
        async with AsyncSidraClient() as client:
            for _ in range(N_REQUESTS):
                await client.get_agregado_periodos(1737)
    else:
        client = AsyncSidraClient()
        try:
            for _ in range(N_REQUESTS):
                await client.get_agregado_periodos(1737)
        finally:
            await client.aclose()
    return (time.perf_counter() - t0) / N_REQUESTS


def _multi_sync() -> float:
    t0 = time.perf_counter()
    with SidraClient() as client:
        for agregado_id in IDS:
            client.get_agregado_metadados(agregado_id)
    return time.perf_counter() - t0


async def _multi_async_inner() -> None:
    async with AsyncSidraClient() as client:
        await asyncio.gather(*(client.get_agregado_metadados(i) for i in IDS))


def _multi_async() -> float:
    t0 = time.perf_counter()
    asyncio.run(_multi_async_inner())
    return time.perf_counter() - t0


def _rounds(modes: dict[str, Callable[[], float]], runs: int) -> dict[str, list[float]]:
    for fn in modes.values():  # aquecimento
        fn()
    out: dict[str, list[float]] = {m: [] for m in modes}
    for _ in range(runs):  # alterna os modos para diluir variações da rede
        for name, fn in modes.items():
            out[name].append(fn())
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--runs", type=int, default=4)
    args = ap.parse_args()

    reuso = _rounds(
        {
            "sync_com_with": lambda: _sync_seq(True),
            "sync_sem_with": lambda: _sync_seq(False),
            "async_com_async_with": lambda: asyncio.run(_async_seq(True)),
            "async_sem_async_with": lambda: asyncio.run(_async_seq(False)),
        },
        args.runs,
    )
    multi = _rounds({"sync": _multi_sync, "async": _multi_async}, args.runs + 1)

    result = {
        "date": dt.date.today().isoformat(),
        "reuso": {
            "what": (
                f"{N_REQUESTS} requisições seguidas de get_agregado_periodos(1737); "
                "segundos por requisição"
            ),
            "runs": args.runs,
            "seconds_per_request": reuso,
            "median_s": {m: statistics.median(v) for m, v in reuso.items()},
        },
        "multi_agregado": {
            "what": "get_agregado_metadados de 8 agregados; segundos por rodada",
            "agregados": IDS,
            "runs": args.runs + 1,
            "seconds": multi,
            "median_s": {m: statistics.median(v) for m, v in multi.items()},
            "min_s": {m: min(v) for m, v in multi.items()},
            "max_s": {m: max(v) for m, v in multi.items()},
        },
    }
    args.out.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    print({m: f"{v * 1000:.0f} ms" for m, v in result["reuso"]["median_s"].items()})
    print(
        {
            m: f"{v:.1f} s (min {multi_min:.1f}, max {multi_max:.1f})"
            for m, v, multi_min, multi_max in (
                (
                    m,
                    result["multi_agregado"]["median_s"][m],
                    result["multi_agregado"]["min_s"][m],
                    result["multi_agregado"]["max_s"][m],
                )
                for m in multi
            )
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
