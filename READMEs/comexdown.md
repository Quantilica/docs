# comexdown: Brazil's foreign trade data downloader

![GitHub](https://img.shields.io/github/license/Quantilica/comexdown?style=flat-square) ![PyPI](https://img.shields.io/pypi/v/comexdown?style=flat-square)

Python package and CLI to download Brazilian foreign trade microdata published by [Ministério da Economia / Secretaria de Comércio Exterior (SECEX/COMEX)][1].

## Installation

```shell
pip install comexdown
```

## Python usage

```python
from pathlib import Path
import comexdown

data_dir = Path("./DATA")

# Auxiliary code table (NCM)
comexdown.get_table(data_dir, table="ncm")

# Trade transactions for 2023 (exports + imports, NCM-based)
comexdown.get_year(data_dir, year=2023)

# Imports only, 2023, with municipality breakdown
comexdown.get_year(data_dir, year=2023, imp=True, mun=True)

# Everything (long-running, multi-GB)
comexdown.download_all(data_dir)
```

Other entrypoints: `get_year_nbm(data_dir, year)` for legacy NBM data (1989–1996) and `get_complete(data_dir, exp=..., imp=..., mun=...)` for the bundled all-years files.

## Command line tool

```text
comexdown <command> [args]

Commands:
  trade YEARS [-exp] [-imp] [-mun] [-o PATH]
        Download trade transactions for one year, a range (2018:2023), or 'complete'.
  table [TABLES...] [-o PATH]
        Download auxiliary code tables; 'all' downloads every table.
        Run with no arguments to list available tables.
  all   [-y] [-o PATH]
        Download EVERYTHING (years, tables, complete files, REPETRO, validacao).
```

`PATH` defaults to `data/secex-comex`.

```shell
comexdown trade 2008:2019 -o ./DATA
comexdown trade 2023 -exp -mun -o ./DATA
comexdown trade complete -o ./DATA

comexdown table all       # download all tables
comexdown table ncm pais  # specific tables
comexdown table           # list available tables

comexdown all -y -o ./DATA
```

## Datasets

- Trade data: `exp`, `imp`, `exp-mun`, `imp-mun`, `exp-nbm`, `imp-nbm`
- Bundled history: `exp-completa`, `imp-completa`, `exp-mun-completa`, `imp-mun-completa`
- Validation totals: `exp-validacao`, `imp-validacao`, `exp-mun-validacao`, `imp-mun-validacao`
- REPETRO (oil & gas regime): `exp-repetro`, `imp-repetro`
- Auxiliary tables: `ncm`, `sh`, `cuci`, `cgce`, `isic`, `siit`, `fat-agreg`, `unidade`, `ppi`, `ppe`, `grupo`, `pais`, `pais-bloco`, `uf`, `uf-mun`, `via`, `urf`, `isic-cuci`, `nbm`, `ncm-nbm`

Data source: [Ministério da Economia / Secretaria de Comércio Exterior][1].

## Behavior

- **HEAD + Last-Modified** check on every URL — files already up to date are skipped.
- **Streaming** in 8 KiB chunks via `urllib`; constant memory regardless of file size.
- **Atomic writes** to `*.tmp` then rename; partial files never appear in the output tree.
- **Retries**: up to 3 attempts with exponential backoff (1 s → 2 s → 4 s).
- **SSL**: uses an unverified context for SECEX servers with expired/misconfigured certs.
- **No third-party dependencies** — pure standard library.

## Development

```shell
git clone https://github.com/Quantilica/comexdown.git
cd comexdown
pip install -e .[dev]
```

### Run tests

```shell
pip install -e .[dev]
pytest tests/
```

[1]: https://www.gov.br/produtividade-e-comercio-exterior/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta
