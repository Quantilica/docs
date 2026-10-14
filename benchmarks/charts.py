"""Gera os gráficos CSV × Parquet do site a partir de `results.json`.

Saída: docs/assets/generated/compression_comparison.svg
       docs/assets/generated/read_performance.svg

Uso::

    uv run --with matplotlib --with numpy python docs/benchmarks/charts.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_RESULTS = HERE / "data" / "results.json"
DEFAULT_OUT = HERE.parent / "docs" / "assets" / "generated"

CSV_COLOR = "#6c8ebf"
PARQUET_COLOR = "#82b366"
READ_COLORS = ["#c0392b", "#e67e22", "#2980b9", "#27ae60"]


def _fmt_size(mib: float) -> str:
    return f"{mib / 1024:.1f} GiB" if mib >= 1024 else f"{mib:.0f} MiB"


def _clean(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def compression_chart(data: dict, out_dir: Path) -> Path:
    rows = data["datasets"]
    labels = [r["label"] for r in rows]
    csv_mib = np.array([r["csv_bytes"] / 2**20 for r in rows])
    pq_mib = np.array([r["parquet_bytes"] / 2**20 for r in rows])
    cut = (1 - pq_mib / csv_mib) * 100

    x = np.arange(len(rows))
    width = 0.36
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.bar(x - width / 2, csv_mib, width, label="CSV", color=CSV_COLOR)
    bars = ax.bar(
        x + width / 2,
        pq_mib,
        width,
        label="Parquet (zstd, padrão do Polars)",
        color=PARQUET_COLOR,
    )
    for bar, c, m in zip(bars, cut, pq_mib, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() * 1.08,
            f"−{c:.0f}%\n{_fmt_size(m)}",
            ha="center",
            va="bottom",
            fontsize=8.5,
            color="#4d6b30",
            fontweight="bold",
        )
    for i, m in enumerate(csv_mib):
        ax.text(
            x[i] - width / 2,
            m * 1.08,
            _fmt_size(m),
            ha="center",
            va="bottom",
            fontsize=8.5,
            color="#3b5a8a",
        )

    ax.set_yscale("log")
    ax.set_ylim(top=csv_mib.max() * 6)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g} MiB"))
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_ylabel("Tamanho em disco (escala log)", fontsize=10)
    ax.set_title("CSV vs. Parquet em dados públicos brasileiros (medido)", fontsize=12)
    ax.legend(fontsize=9.5, loc="upper left")
    _clean(ax)

    env = data["environment"]
    fig.text(
        0.01,
        0.005,
        f"Polars {env['polars']}, medido em {env['date']}. Dados e script: docs/benchmarks/.",
        fontsize=7.5,
        color="#666666",
    )
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "compression_comparison.svg"
    fig.savefig(path, format="svg")
    plt.close(fig)
    return path


def performance_chart(data: dict, out_dir: Path) -> Path:
    rows = data["datasets"]
    series = [
        ("read_csv (texto)", "read_csv_strings_s"),
        ("leitor tipado do fetcher (CSV)", "read_typed_s"),
        ("read_parquet", "read_parquet_s"),
        ("scan_parquet + filtro (3 colunas)", "scan_filter_s"),
    ]
    x = np.arange(len(rows))
    width = 0.2
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    top = 0.0
    for k, (name, key) in enumerate(series):
        vals = np.array([r.get(key, np.nan) for r in rows], dtype=float)
        top = max(top, np.nanmax(vals))
        bars = ax.bar(x + (k - 1.5) * width, vals, width, label=name, color=READ_COLORS[k])
        for bar, v in zip(bars, vals, strict=True):
            if np.isnan(v):
                continue
            label = f"{v:.2f}s" if v >= 0.1 else f"{v * 1000:.0f}ms"
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                v * 1.12,
                label,
                ha="center",
                va="bottom",
                fontsize=7.5,
            )
    ax.set_yscale("log")
    ax.set_ylim(top=top * 8)
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{v:g} s" if v >= 1 else f"{v * 1000:g} ms")
    )
    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{r['label']}\n{r['csv_bytes'] / 2**20:,.0f} MiB de CSV" for r in rows],
        fontsize=9,
    )
    ax.set_ylabel("Tempo de leitura (mediana, escala log)", fontsize=10)
    ax.set_title("Tempo de leitura: CSV vs. Parquet com Polars (medido)", fontsize=12)
    ax.legend(fontsize=8.5, loc="upper left")
    _clean(ax)

    env = data["environment"]
    fig.text(
        0.01,
        0.005,
        f"{env['cores']} núcleos, {env['memory']} de RAM, Polars {env['polars']}, "
        f"{env['date']}; arquivos no cache de página. Dados e script: docs/benchmarks/.",
        fontsize=7.5,
        color="#666666",
    )
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "read_performance.svg"
    fig.savefig(path, format="svg")
    plt.close(fig)
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    data = json.loads(args.results.read_text(encoding="utf-8"))
    for path in (compression_chart(data, args.out), performance_chart(data, args.out)):
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
