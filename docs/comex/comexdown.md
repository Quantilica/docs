# comexdown: Brazil's Foreign Trade Data Downloader

**comexdown** is a Python package and CLI to download Brazilian foreign trade microdata published by SECEX/COMEX (Secretaria de Comércio Exterior, Ministério da Economia).

## Features

- **Temporal idempotency** — HEAD request checks `Last-Modified`; skips files already up to date
- **Streaming downloads** — 8 KiB chunks; constant memory regardless of file size
- **Atomic writes** — downloads to `*.tmp` and renames on success; partial files never appear
- **Auto-retry** — up to 3 attempts with exponential backoff (1 s → 2 s → 4 s)
- **SSL resilience** — uses an unverified SSL context for SECEX servers with expired/misconfigured certs
- **No third-party dependencies** — pure standard library (`urllib`, `ssl`, `http.client`)

## Installation

```bash
pip install comexdown
```

**Requirements:** Python 3.10+

## CLI

```text
comexdown <command> [args]

Commands:
  trade YEARS [-exp] [-imp] [-mun] [-o PATH]
        Download trade transactions for one year, a range (2018:2023), or 'complete'.
        -exp / -imp restrict the direction; default downloads both.
        -mun adds municipality-level files (1997+).
  table [TABLES...] [-o PATH]
        Download auxiliary code tables. 'all' downloads every table.
        Run with no arguments to print the list of available tables.
  all   [-y] [-o PATH]
        Download EVERYTHING (all years, all tables, all datasets). Asks for
        confirmation unless -y is given.
```

`PATH` defaults to `data/secex-comex`.

### Examples

```bash
# Exports + imports for 2023
comexdown trade 2023 -o ./DATA

# Imports only, 2018–2023, with municipality breakdown
comexdown trade 2018:2023 -imp -mun -o ./DATA

# Single complete-history file (all years bundled by SECEX)
comexdown trade complete -o ./DATA

# Auxiliary tables
comexdown table all -o ./DATA          # every table
comexdown table ncm pais uf -o ./DATA  # specific tables
comexdown table                        # list available tables

# Everything (long-running, multi-GB)
comexdown all -y -o ./DATA
```

## Python API

Top-level functions in `comexdown`:

```python
from pathlib import Path
import comexdown

data_dir = Path("./DATA")

# Trade transactions for one year (NCM-based, 1997+)
comexdown.get_year(data_dir, year=2023)                     # exports + imports
comexdown.get_year(data_dir, year=2023, exp=True)           # exports only
comexdown.get_year(data_dir, year=2023, imp=True, mun=True) # imports, municipality

# Older NBM-based trade data (1989–1996)
comexdown.get_year_nbm(data_dir, year=1995)

# Complete historical files (one file per direction, all years)
comexdown.get_complete(data_dir)
comexdown.get_complete(data_dir, exp=True, mun=True)

# Auxiliary code table
comexdown.get_table(data_dir, table="ncm")
comexdown.get_table(data_dir, table="pais")

# Everything
comexdown.download_all(data_dir)
```

Lower-level helpers in `comexdown.download`: `download_file(url, output, retry=3, blocksize=8192)`, `remote_is_more_recent(headers, dest)`, `get_file_metadata(url)`.

## Datasets

### Trade transactions

| Dataset | Coverage | Notes |
|---|---|---|
| `exp`, `imp` | 1997–present | NCM-based, monthly granularity |
| `exp-mun`, `imp-mun` | 1997–present | Same, with municipality of origin/destination |
| `exp-nbm`, `imp-nbm` | 1989–1996 | Pre-NCM, NBM classification |
| `exp-completa`, `imp-completa` | full history | Single bundled file per direction |
| `exp-mun-completa`, `imp-mun-completa` | full history | Same, with municipality |

### Validation totals (cross-check sums)

`exp-validacao`, `imp-validacao`, `exp-mun-validacao`, `imp-mun-validacao`.

### REPETRO (oil & gas special regime)

`exp-repetro`, `imp-repetro`.

### Auxiliary tables

`ncm`, `sh`, `cuci`, `cgce`, `isic`, `siit`, `fat-agreg`, `unidade`, `ppi`, `ppe`, `grupo`, `pais`, `pais-bloco`, `uf`, `uf-mun`, `via`, `urf`, `isic-cuci`, `nbm`, `ncm-nbm`.

Run `comexdown table` (no args) to print the live list with descriptions.

## On-disk layout

`comexdown` writes to a structured tree under the output path:

```
data/secex-comex/
├── exp/2023.csv
├── imp/2023.csv
├── exp-mun/2023.csv
├── exp-nbm/1995.csv
├── exp-completa.csv
├── auxiliary-tables/<table>.csv
├── validacao/<file>
└── repetro/<file>
```

## Idempotence

Every download starts with a HEAD request. `remote_is_more_recent` compares `Last-Modified` against the local file's `mtime`; if the local file is up to date the GET is skipped entirely. After a successful download the file's `mtime` is set from `Last-Modified`, so the next run finds it idempotent without re-fetching.

## Data Source

[Ministério do Desenvolvimento, Indústria, Comércio e Serviços — Estatísticas de Comércio Exterior](https://www.gov.br/produtividade-e-comercio-exterior/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta).

## Learn More

- **[Foreign Trade Overview](index.md)** — All trade data tools
- **[IBGE Macro Data](../ibge/index.md)** — Aggregate trade statistics
- **[Architecture](../architecture/overview.md)** — System design
