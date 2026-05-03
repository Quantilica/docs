# pdet-data: Brazilian Labor Market Microdata Fetcher

**pdet-data** is a Python package to fetch, read, and convert microdata from PDET (Plataforma de Disseminação de Estatísticas do Trabalho) — Brazil's official labor statistics platform maintained by the Ministry of Labor and Social Security.

It covers RAIS (annual employment census) and CAGED (monthly employment flows), including the legacy CAGED through 2019 and the redesigned CAGED 2020+. Output is Polars DataFrames, with utilities to bulk-convert raw archives to Parquet.

## Key Features

- **FTP fetcher** — downloads everything from `ftp.mtps.gov.br` (RAIS, CAGED, docs)
- **Smart CSV reader** — auto-detects separator, handles `latin-1` and `utf-8`, repairs ragged CSVs
- **Type conversion** — `INT64`, `FLOAT64`, `Boolean`, and `Categorical` based on per-column metadata
- **Bulk Parquet conversion** — `convert_rais` / `convert_caged` orchestrate decompression + read + write
- **Schema introspection** — `extract_columns_for_dataset` dumps every per-file header to CSV
- **Polars-native** — fast columnar processing with minimal dependencies (`polars`, `tqdm`)

## Installation

```bash
pip install pdet-data
```

**Requirements:** Python 3.10+ and the `7z` CLI on `PATH` (used by `convert_*` to extract `.7z` archives).

## CLI

The package installs the `pdet-data` command (also available as `python -m pdet_data`) with four subcommands:

```text
pdet-data <subcommand> [args]

Subcommands:
  fetch    DEST_DIR              Download every RAIS and CAGED file (data + docs) to DEST_DIR
  list     DEST_DIR              List remote files that are not yet present locally
  convert  DATA_DIR DEST_DIR     Decompress the raw archives and write Parquet files
  columns  DATA_DIR DATASET [-o OUT_DIR]
                                 Dump per-file column headers for one dataset to CSV
```

`DATASET` for `columns` accepts: `rais-vinculos`, `rais-estabelecimentos`, `caged`, `caged-ajustes`, `caged-2020`.

## Quick Start

### 1. Download all data

```bash
pdet-data fetch ./data
```

Equivalent Python:

```python
from pathlib import Path
from pdet_data import (
    connect,
    fetch_rais, fetch_rais_docs,
    fetch_caged, fetch_caged_docs,
    fetch_caged_2020, fetch_caged_2020_docs,
)

ftp = connect()
try:
    fetch_rais(ftp=ftp, dest_dir=Path("./data"))
    fetch_rais_docs(ftp=ftp, dest_dir=Path("./data"))
    fetch_caged(ftp=ftp, dest_dir=Path("./data"))
    fetch_caged_docs(ftp=ftp, dest_dir=Path("./data"))
    fetch_caged_2020(ftp=ftp, dest_dir=Path("./data"))
    fetch_caged_2020_docs(ftp=ftp, dest_dir=Path("./data"))
finally:
    ftp.close()
```

### 2. Convert raw archives to Parquet

```bash
pdet-data convert ./data ./parquet
```

```python
from pathlib import Path
from pdet_data import convert_rais, convert_caged

convert_rais(Path("./data"), Path("./parquet"))
convert_caged(Path("./data"), Path("./parquet"))
```

### 3. Read RAIS CSVs

```python
from pathlib import Path
import polars as pl
from pdet_data.reader import read_rais

df = read_rais(
    filepath=Path("data/rais_2023_vinculos.csv"),
    year=2023,
    dataset="vinculos",       # or "estabelecimentos"
)

top_sectors = (
    df.group_by("cnae_setor")
      .agg(pl.col("id_vinculo").count().alias("num_employees"))
      .sort("num_employees", descending=True)
      .head(10)
)
```

### 4. Read CAGED CSVs (legacy or 2020+)

A single `read_caged` covers every variant, dispatched by the `dataset` argument:

| `dataset` | Source | Period |
|---|---|---|
| `caged` | Legacy CAGED | until 2019 |
| `caged-ajustes` | Legacy CAGED — late filings | until 2019 |
| `caged-2020-mov` | New CAGED — on-time movements | 2020+ |
| `caged-2020-for` | New CAGED — late filings | 2020+ |
| `caged-2020-exc` | New CAGED — exclusions | 2020+ |

```python
from pathlib import Path
import polars as pl
from pdet_data.reader import read_caged

df_caged = read_caged(
    Path("data/caged_201812.csv"),
    date=201812,
    dataset="caged",
)

df_mov = read_caged(
    Path("data/cagedmov_202401.csv"),
    date=202401,
    dataset="caged-2020-mov",
)

balance = (
    df_mov.with_columns(saldo=pl.col("admissoes") - pl.col("demissoes"))
          .group_by("uf")
          .agg(pl.col("saldo").sum())
          .sort("saldo", descending=True)
)
```

### 5. Extract per-file schema

```bash
pdet-data columns ./data rais-vinculos -o ./schemas
```

```python
from pathlib import Path
from pdet_data import extract_columns_for_dataset

extract_columns_for_dataset(
    data_dir=Path("./data"),
    glob_pattern="rais-*.*",
    output_file=Path("./schemas/rais-vinculos-columns.csv"),
    encoding="latin-1",
    has_uf=True,
)
```

## Available Data

### RAIS (Relação Anual de Informações Sociais)

Annual census of formal employment. Datasets: `rais-vinculos` (employment bonds) and `rais-estabelecimentos` (establishments). Coverage from 1985 to present.

### CAGED legacy

Monthly employment flows up to December 2019. Datasets: `caged`, `caged-ajustes`.

### New CAGED (2020+)

Monthly employment flows from January 2020 onward, split into three files per competence:

- `caged-2020-mov` — on-time movements
- `caged-2020-for` — late filings
- `caged-2020-exc` — exclusions / retroactive cancellations

## Architecture

```
src/pdet_data/
├── __init__.py        # Re-exports the public API
├── __main__.py        # CLI (fetch / list / convert / columns)
├── fetch.py           # FTP connection, listing, downloads
├── reader.py          # CSV parsing + dtype conversion
├── wrangling.py       # convert_rais, convert_caged, extract_columns_for_dataset
├── storage.py         # Destination path conventions
├── constants.py       # Per-year column schemas, NA values, ragged file list
└── meta.py            # FTP directories and filename patterns
```

Pipeline: FTP → compressed archive (`.7z` / `.zip`) → `7z` extract → CSV → `read_rais` / `read_caged` → typed Polars DataFrame → Parquet.

## Public API

Importable directly from `pdet_data`:

| Function | Purpose |
|---|---|
| `connect()` | Open FTP connection to `ftp.mtps.gov.br`. |
| `list_rais(ftp)`, `list_rais_docs(ftp)` | Iterate RAIS files / docs metadata. |
| `list_caged(ftp)`, `list_caged_docs(ftp)` | Iterate legacy CAGED files / docs. |
| `list_caged_2020(ftp)`, `list_caged_2020_docs(ftp)` | Iterate New CAGED files / docs. |
| `fetch_rais(ftp, dest_dir)`, `fetch_rais_docs(...)` | Download RAIS data / docs. |
| `fetch_caged(ftp, dest_dir)`, `fetch_caged_docs(...)` | Download legacy CAGED data / docs. |
| `fetch_caged_2020(ftp, dest_dir)`, `fetch_caged_2020_docs(...)` | Download New CAGED data / docs. |
| `convert_rais(data_dir, dest_dir)` | Decompress + read + write Parquet for every RAIS archive. |
| `convert_caged(data_dir, dest_dir)` | Same for every CAGED archive (legacy + 2020+). |
| `extract_columns_for_dataset(...)` | Dump per-file headers for one dataset glob. |

Low-level reading helpers in `pdet_data.reader`:

- `read_rais(filepath, year, dataset, **read_csv_args)` — `dataset` ∈ `{"vinculos", "estabelecimentos"}`
- `read_caged(filepath, date, dataset, **read_csv_args)` — `dataset` ∈ `{"caged", "caged-ajustes", "caged-2020-mov", "caged-2020-for", "caged-2020-exc"}`
- `write_parquet(df, filepath)`
- `decompress(file_metadata)` — shells out to the `7z` binary

## Data Quality

`read_rais` / `read_caged` automatically:

- Detect the CSV separator (`;`, `\t`, `,`) on the first line
- Use the right encoding (`latin-1` for RAIS / legacy CAGED, `utf-8` for New CAGED)
- Strip whitespace and thousand separators from `INTEGER_COLUMNS`
- Convert decimal commas to dots for `NUMERIC_COLUMNS`
- Cast `BOOLEAN_COLUMNS` from `0/1` integers to `Boolean`
- Cast everything else to `Categorical` after `strip_chars()`
- Truncate over-long rows in files listed in `constants.RAGGED_CSV_FILES` to header width

## Performance

For one full RAIS year (~10 GB uncompressed):

| Step | Wall time | Peak memory |
|------|-----------|-------------|
| FTP download | 5–15 min | – |
| `7z` extraction | 1–3 min | – |
| `read_rais` (parse + cast) | ~10 s | ~2 GB |
| Simple group-by / agg | <1 s | – |

*Reference: modern CPU, 16 GB RAM, SSD.*

## Learn More

- **[Labor Market Overview](index.md)** — All labor data tools
- **[Foreign Trade Data](../comex/index.md)** — Trade statistics
- **[Architecture](../architecture/overview.md)** — System design
- **[PDET Official](http://pdet.mte.gov.br/microdados-rais-e-caged)** — Government source
