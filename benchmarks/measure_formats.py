"""Mede CSV × Parquet em dados reais do ecossistema Quantilica.

Para cada dataset: tamanho do CSV, tamanho do Parquet (compressão padrão do
Polars e `snappy`), tempo de leitura do CSV (parse puro e leitor tipado do
fetcher), do Parquet inteiro e do Parquet com filtro preguiçoso, e o tempo do
pandas no mesmo CSV. Os leitores tipados são os do próprio ecossistema:
`tesouro_direto_fetcher.reader.read_prices`, `pdet_fetcher.reader.read_caged` e
`pdet_fetcher.reader.read_rais`.

Rode a partir da raiz do workspace, onde os fetchers estão instalados::

    uv run --with pandas --with pyarrow python docs/benchmarks/measure_formats.py \\
        --data-dir <pasta> --out docs/benchmarks/results.json

A pasta de dados tem o layout descrito em `README.md`. Os tempos são a mediana
de execuções com o arquivo já no cache de página do sistema operacional; valem
para a máquina registrada em `environment`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import platform
import statistics
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import polars as pl


def _tesouro(data_dir: Path) -> dict[str, Any]:
    from tesouro_direto_fetcher.reader import read_prices

    path = Path(
        glob.glob(str(data_dir / "td" / "taxas-dos-titulos-*" / "*.csv"))[0]
    )
    return {
        "name": "tesouro-precos",
        "label": "Tesouro Direto\npreços e taxas",
        "source": "tesouro-direto-fetcher (taxas dos títulos ofertados), histórico completo",
        "csv": path,
        "separator": ";",
        "encoding": "utf8",
        "typed": lambda: read_prices(path),
        "filter": ("bond_type", "Tesouro Selic"),
    }


def _caged(data_dir: Path) -> dict[str, Any]:
    from pdet_fetcher.reader import read_caged

    path = data_dir / "caged" / "CAGEDMOV202608.txt"
    return {
        "name": "caged-2026-08",
        "label": "Novo CAGED\nmovimentações, ago/2026",
        "source": "pdet-fetcher, grupo caged-2020-mov, CAGEDMOV202608",
        "csv": path,
        "separator": ";",
        "encoding": "utf8",
        "typed": lambda: read_caged(path, 202608, "caged-2020-mov"),
        "filter": ("id_uf", "35"),
    }


def _rais(data_dir: Path, region: str, label: str) -> dict[str, Any]:
    from pdet_fetcher.reader import read_rais

    path = next((data_dir / "rais").glob(f"RAIS_VINC_PUB_{region}.*"))
    return {
        "name": f"rais-2024-{region.lower().replace('_', '-')}",
        "label": label,
        "source": f"pdet-fetcher, grupo rais-vinculos, RAIS_VINC_PUB_{region} de 2024",
        "csv": path,
        "separator": ";",
        "encoding": "latin1",
        "typed": lambda: read_rais(path, 2024, "vinculos"),
        "filter": ("sexo", "2"),
    }


def _median(fn: Callable[[], Any], runs: int) -> float:
    """Mediana de `runs` execuções, depois de uma de aquecimento."""
    fn()
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return statistics.median(times)


def _environment() -> dict[str, Any]:
    cpu = "?"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    mem = "?"
    try:
        kb = int(Path("/proc/meminfo").read_text().split()[1])
        mem = f"{kb / 2**20:.0f} GiB"
    except (OSError, ValueError):
        pass
    env: dict[str, Any] = {
        "date": dt.date.today().isoformat(),
        "cpu": cpu,
        "cores": os.cpu_count(),
        "memory": mem,
        "python": platform.python_version(),
        "polars": pl.__version__,
        "os": platform.platform(),
    }
    try:
        import pandas as pd

        env["pandas"] = pd.__version__
    except ImportError:
        pass
    return env


def measure(spec: dict[str, Any], runs: int, with_pandas: bool) -> dict[str, Any]:
    csv: Path = spec["csv"]
    sep, enc = spec["separator"], spec["encoding"]
    out: dict[str, Any] = {
        k: spec[k] for k in ("name", "label", "source", "separator", "encoding")
    }
    out["csv_file"] = csv.name
    out["csv_bytes"] = csv.stat().st_size

    def raw() -> pl.DataFrame:
        return pl.read_csv(
            csv, separator=sep, encoding=enc, infer_schema_length=0, has_header=True
        )

    out["rows"], out["columns"] = raw().shape
    out["read_csv_strings_s"] = _median(raw, runs)

    t0 = time.perf_counter()
    df = spec["typed"]()
    out["read_typed_first_s"] = time.perf_counter() - t0
    out["read_typed_s"] = _median(spec["typed"], max(1, runs - 1))

    with tempfile.TemporaryDirectory() as tmp:
        default_pq = Path(tmp) / "default.parquet"
        t0 = time.perf_counter()
        df.write_parquet(default_pq)
        out["write_parquet_s"] = time.perf_counter() - t0
        out["parquet_bytes"] = default_pq.stat().st_size
        snappy = Path(tmp) / "snappy.parquet"
        df.write_parquet(snappy, compression="snappy")
        out["parquet_snappy_bytes"] = snappy.stat().st_size
        zstd = Path(tmp) / "zstd.parquet"
        df.write_parquet(zstd, compression="zstd")
        out["parquet_zstd_bytes"] = zstd.stat().st_size

        out["read_parquet_s"] = _median(lambda: pl.read_parquet(default_pq), runs)
        col, val = spec["filter"]
        if col in df.columns:
            keep = df.columns[:3]
            lazy = lambda: (  # noqa: E731
                pl.scan_parquet(default_pq)
                .filter(pl.col(col).cast(pl.Utf8) == val)
                .select(keep)
                .collect()
            )
            out["scan_filter_s"] = _median(lazy, runs)
            out["scan_filter_rows"] = lazy().height
            out["scan_filter"] = f"{col} == {val!r}, {len(keep)} colunas"
        else:
            out["scan_filter_error"] = f"coluna {col!r} ausente: {df.columns[:8]}"

    if with_pandas:
        import pandas as pd

        pd_kw = {"sep": sep, "encoding": "latin1" if enc == "latin1" else "utf-8"}
        out["pandas_read_csv_strings_s"] = _median(
            lambda: pd.read_csv(csv, dtype=str, **pd_kw), max(1, runs - 1)
        )
    out["schema"] = {k: str(v) for k, v in list(df.schema.items())[:60]}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument(
        "--only", nargs="*", help="nomes dos datasets (padrão: todos os disponíveis)"
    )
    ap.add_argument(
        "--pandas-max-mb",
        type=int,
        default=600,
        help="só mede o pandas em CSV de até este tamanho",
    )
    args = ap.parse_args()

    builders = {
        "tesouro-precos": lambda: _tesouro(args.data_dir),
        "caged-2026-08": lambda: _caged(args.data_dir),
        "rais-2024-norte": lambda: _rais(args.data_dir, "NORTE", "RAIS 2024\nregião Norte"),
        "rais-2024-centro-oeste": lambda: _rais(
            args.data_dir, "CENTRO_OESTE", "RAIS 2024\nCentro-Oeste"
        ),
    }
    results = []
    for name, build in builders.items():
        if args.only and name not in args.only:
            continue
        try:
            spec = build()
        except (IndexError, StopIteration, FileNotFoundError) as exc:
            print(f"pulando {name}: arquivo ausente ({exc})", file=sys.stderr)
            continue
        size_mb = spec["csv"].stat().st_size / 2**20
        print(f"medindo {name} ({size_mb:.0f} MiB)...", flush=True)
        runs = args.runs if size_mb < 300 else max(2, args.runs // 2)
        res = measure(spec, runs, with_pandas=size_mb <= args.pandas_max_mb)
        res["runs"] = runs
        results.append(res)
        print(
            f"  csv {res['csv_bytes'] / 2**20:.1f} MiB -> parquet "
            f"{res['parquet_bytes'] / 2**20:.1f} MiB | csv(str) {res['read_csv_strings_s']:.2f}s "
            f"typed {res['read_typed_s']:.2f}s parquet {res['read_parquet_s']:.3f}s "
            f"scan {res.get('scan_filter_s', float('nan')):.3f}s",
            flush=True,
        )
        args.out.write_text(
            json.dumps(
                {"environment": _environment(), "datasets": results},
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
