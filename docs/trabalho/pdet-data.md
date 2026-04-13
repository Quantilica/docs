# pdet-data: Brazilian Labor Market Microdata Fetcher

**pdet-data** is a Python package to fetch, read, and process microdata from PDET (Plataforma de Disseminação de Estatísticas do Trabalho) — Brazil's official labor statistics platform maintained by the Ministry of Labor and Social Security.

Access programmatic data from RAIS (annual employment census) and CAGED (monthly employment flows) with automatic type conversion, anomaly handling, and modern format export (Parquet, etc.).

## Key Features

- **FTP access** — Direct connection to PDET servers with automatic file downloads
- **Smart reading** — Automatic format detection, encoding handling, and ragged CSV repair
- **Type conversion** — Transforms numbers, booleans, and categorical data from legacy formats
- **RAIS data** — Annual employment census with 1985-present coverage
- **CAGED data** — Monthly employment flows (classic through 2019, and modern 2020+)
- **Polars integration** — Fast processing with Polars DataFrames
- **Minimal dependencies** — Just Polars and tqdm

## Installation

```bash
pip install pdet-data
```

**Requirements:** Python 3.10+

## Quick Start

### Download data

```python
from pathlib import Path
from pdet_data import fetch

# Connect to PDET FTP
ftp = fetch.connect()

# Download RAIS data
fetch.fetch_rais(ftp=ftp, dest_dir=Path("./dados"))

# Download CAGED data (classic and 2020+)
fetch.fetch_caged(ftp=ftp, dest_dir=Path("./dados"))
fetch.fetch_caged_2020(ftp=ftp, dest_dir=Path("./dados"))

ftp.close()
```

Or via CLI:

```bash
python -m pdet_data run --data-dir ./dados
```

### Read RAIS data

```python
from pathlib import Path
import polars as pl
from pdet_data.reader import read_rais

# Read employment bonds for 2023
df = read_rais(
    filepath=Path("dados/rais_2023_vinculos.csv"),
    year=2023,
    dataset="vinculos"
)

# Find top sectors by employee count
top_sectors = df.group_by("cnae_setor").agg(
    pl.col("id_vinculo").count().alias("num_employees")
).sort("num_employees", descending=True).head(10)
```

### Read CAGED data

```python
from pathlib import Path
from pdet_data.reader import read_caged, read_caged_2020

# Classic CAGED (until 2019)
df_caged = read_caged(Path("dados/caged_202012.csv"))

# New CAGED 2020+
df_mov = read_caged_2020(Path("dados/caged_mov_202401.csv"))

# Analyze: employment balance by state
balance = df_mov.with_columns(
    saldo = pl.col("admissoes") - pl.col("demissoes")
).group_by("uf").agg(
    pl.col("saldo").sum()
).sort("saldo", descending=True)
```

### Batch processing

```python
from pathlib import Path
from pdet_data.reader import read_rais
import polars as pl

# Read multiple years of RAIS
years = [2020, 2021, 2022, 2023]
dfs = []

for year in years:
    df = read_rais(
        filepath=Path(f"dados/rais_{year}_vinculos.csv"),
        year=year,
        dataset="vinculos"
    )
    dfs.append(df)

# Analyze temporal evolution
combined = pl.concat(dfs)
evolution = combined.group_by("ano").agg(
    total_employees=pl.col("id_vinculo").count()
).sort("ano")
```

## Available Data

### RAIS (Relação Anual de Informações Sociais)

Annual census of formal employment with records declared by employers.

- **Coverage:** 1985 to present
- **Frequency:** Annual (December)
- **Datasets:** Employment bonds and establishments
- **Use cases:** Income analysis, employment studies, labor inequality research

### CAGED (Cadastro Geral de Empregados e Desempregados)

Monthly employment flows (admissions, separations).

- **Coverage:** 1985 to December 2019 (classic), January 2020+ (modern)
- **Frequency:** Monthly
- **Use cases:** Employment indicators, labor market monitoring, economic trends

## Architecture

The package is organized into focused modules:

```
pdet_data/
├── fetch.py         # FTP connection and download
├── reader.py        # CSV reading and processing
├── storage.py       # File paths and storage management
├── constants.py     # Column names, missing values, types by year
├── meta.py          # Dataset metadata
└── __init__.py
```

Data flows through automatic detection → reading → type conversion → Polars DataFrame.

## Main API Functions

### `fetch.connect()`

Connect to PDET FTP server.

### `fetch.fetch_rais(ftp, dest_dir)`

Download all available RAIS files.

### `fetch.fetch_caged(ftp, dest_dir)`

Download classic CAGED (through December 2019).

### `fetch.fetch_caged_2020(ftp, dest_dir)`

Download modern CAGED (January 2020 onwards).

### `read_rais(filepath, year, dataset, **kwargs)`

Read RAIS CSV file and return Polars DataFrame.

- `dataset`: `"vinculos"` (employment) or `"estabelecimentos"` (establishments)

### `read_caged(filepath, **kwargs)`

Read classic CAGED CSV.

### `read_caged_2020(filepath, **kwargs)`

Read modern CAGED CSV.

## Learn More

- **[Labor Market Overview](index.md)** — All labor data tools
- **[Foreign Trade Data](../comex/index.md)** — Trade statistics
- **[Architecture](../architecture/overview.md)** — System design
- **[PDET Official](https://pdet.mtp.gov.br/)** — Government source
