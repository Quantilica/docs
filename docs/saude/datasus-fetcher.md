# datasus-fetcher

**datasus-fetcher** is a Python package and command-line tool to bulk-download raw microdata files (`.dbc`) from [DATASUS](https://datasus.saude.gov.br)'s public FTP server (`ftp.datasus.gov.br`). It's a pure, reliable downloader that gives you organized local copies of Brazil's largest public health database.

## Key Features

- **113 datasets** across all major Brazilian health information systems
- **320+ GB** of historical microdata, some series going back to 1979
- **Multi-threaded downloads** — configurable parallel connections for faster retrieval
- **Smart filtering** — slice by date range and/or Brazilian state (UF) before downloading
- **File integrity checks** — skips already-downloaded files by comparing sizes
- **Automatic retries** — up to 3 retries on transient FTP errors
- **File versioning** — stores every downloaded version with a date-stamped filename; archive old ones automatically
- **Documentation & auxiliary tables** — download codebooks and reference tables alongside data
- **No external dependencies** — pure Python 3.10+

## Installation

```bash
pip install datasus-fetcher
```

For isolated global installation (recommended for CLI-only use):

```bash
pipx install datasus-fetcher
```

## Quick Start

Download SIH-RD (Hospital Admissions) for São Paulo, Rio de Janeiro, and Minas Gerais from 2020 to 2023:

```bash
datasus-fetcher data --data-dir /path/to/data sih-rd \
    --start 2020-01 \
    --end 2023-12 \
    --regions sp rj mg
```

Download all datasets (warning: 320+ GB total):

```bash
datasus-fetcher data --data-dir /path/to/data
```

## Command Reference

datasus-fetcher exposes five subcommands:

### `data` — Download microdata files

```bash
datasus-fetcher data --data-dir <DIR> [DATASETS...] [OPTIONS]
```

| Argument | Description |
|---|---|
| `DATASETS` | One or more dataset codes (e.g. `sih-rd cnes-st`). Omit to download all datasets. |
| `--data-dir DIR` | **Required.** Local directory where files will be stored. |
| `--start PERIOD` | Start of the date filter. Format: `YYYY` or `YYYY-MM`. |
| `--end PERIOD` | End of the date filter. Format: `YYYY` or `YYYY-MM`. |
| `--regions UF ...` | One or more state codes in lowercase (e.g. `sp rj mg ba`). |
| `-t, --threads N` | Number of concurrent download threads (default: `2`). |

**Examples:**

```bash
# Dengue notifications from SINAN — all years, all states
datasus-fetcher data --data-dir ./data sinan-deng

# CNES establishments for the entire Northeast, from 2015 onwards
datasus-fetcher data --data-dir ./data cnes-st \
    --start 2015-01 \
    --regions al ba ce ma pb pe pi rn se

# SIM death records (ICD-10) from 2000 to 2023
datasus-fetcher data --data-dir ./data sim-do-cid10 \
    --start 2000 --end 2023

# Speed up downloads with more parallel threads
datasus-fetcher data --data-dir ./data sih-rd --threads 4
```

### `list-datasets` — Inspect available datasets

Connects to the DATASUS FTP server and prints file counts, sizes, and date ranges for each dataset:

```bash
datasus-fetcher list-datasets

# Inspect specific datasets only
datasus-fetcher list-datasets sih-rd sia-pa cnes-pf
```

### `docs` — Download documentation files

Downloads the official documentation files (data dictionaries, codebooks) for each system:

```bash
# Download docs for specific systems
datasus-fetcher docs --data-dir ./docs sih cnes sia sim sinan

# Download docs for all systems
datasus-fetcher docs --data-dir ./docs
```

### `aux` — Download auxiliary reference tables

Downloads lookup/reference tables (ICD codes, municipality codes, procedure tables, occupation codes, etc.):

```bash
# Download auxiliary tables for specific systems
datasus-fetcher aux --data-dir ./aux sih cnes

# Download auxiliary tables for all systems
datasus-fetcher aux --data-dir ./aux
```

### `archive` — Move old file versions to an archive

DATASUS periodically updates its files. datasus-fetcher stores every downloaded version with a date-stamped filename. Use `archive` to move non-latest versions to a separate directory:

```bash
datasus-fetcher archive \
    --data-dir ./data \
    --archive-data-dir ./data-archive
```

## File Storage Structure

Downloaded files are organized into a structured directory tree:

```
data/
└── sih-rd/
    ├── 199201/                              ← YYYYMM partition directory
    │   └── sih-rd_sp_199201_20250218.dbc   ← dataset_uf_period_downloaddate.dbc
    ├── 202001/
    │   ├── sih-rd_sp_202001_20250218.dbc
    │   └── sih-rd_rj_202001_20250218.dbc
    └── 202312/
        └── sih-rd_mg_202312_20250218.dbc
```

For year-only datasets (e.g. SIM, SINASC):

```
data/
└── sim-do-cid10/
    └── 2023/
        ├── sim-do-cid10_sp_2023_20250218.dbc
        └── sim-do-cid10_rj_2023_20250218.dbc
```

Each filename encodes: **dataset** + **state (UF)** + **period** + **download date**.

## Logging Configuration

datasus-fetcher logs download progress to the console by default. You can override this by placing a `logging.ini` file in your working directory.

## Available Datasets

datasus-fetcher supports **113 datasets** across these systems:

- **SIHSUS** — Hospital admissions
- **SIM** — Mortality records (ICD-9 and ICD-10)
- **SINASC** — Birth registrations
- **SIA** — Ambulatory procedures and outpatient production
- **CNES** — Health facilities registry (establishments, professionals, equipment, services)
- **SINAN** — Notifiable diseases (dengue, tuberculosis, HIV, and 60+ others)
- **And more** — SISCOLO, SISMAMA, SISPRENATAL, population bases, territorial data

For a complete list with file counts and date ranges, use:

```bash
datasus-fetcher list-datasets
```

## Brazilian State Codes

Use lowercase two-letter codes with `--regions`. Common codes:

| Code | State | Code | State |
|------|-------|------|-------|
| `sp` | São Paulo | `ba` | Bahia |
| `rj` | Rio de Janeiro | `mg` | Minas Gerais |
| `rs` | Rio Grande do Sul | `sc` | Santa Catarina |
| `ce` | Ceará | `pe` | Pernambuco |

See the full list in the [README](https://github.com/Quantilica/datasus-fetcher).

## Reading DBC Files

datasus-fetcher downloads `.dbc` files, which is a compressed format used by DATASUS. To read these files in Python, you can use packages such as:

- [PySUS](https://github.com/AlertaDengue/PySUS)
- [read.dbc](https://github.com/Quantilica/read.dbc) (R)
- [dbf2dbc](https://github.com/AlertaDengue/dbf2dbc) (conversion tool)

## Learn More

- **[Public Health Overview](index.md)** — All health data tools
- **[IBGE Labor Statistics](../ibge/index.md)** — Employment and demographics
- **[Architecture](../architecture/overview.md)** — System design
- **[DATASUS Official (Portuguese)](https://datasus.saude.gov.br/)** — Government source
