# comexdown: Brazil's Foreign Trade Data Downloader

**comexdown** is a Python package to download and process Brazilian foreign trade data published by the Ministério da Economia (ME) / Secretaria de Comércio Exterior (SCE).

## Features

- **Multi-threaded downloads** — configurable parallel connections for faster retrieval
- **File integrity checks** — skips already-downloaded files by comparing Last-Modified dates
- **Automatic retries** — handles transient network errors with exponential backoff
- **Streaming downloads** — processes large files in chunks without memory exhaustion
- **Code tables** — download NCM, UF, and other reference tables
- **Exports & Imports** — complete Siscomex data from 1997 to present

## Installation

```bash
pip install comexdown
```

## Quick Start

### Download trade data

```python
import comexdown

# Download 2019 exports data to ./DATA directory
comexdown.exp(year=2019, path="./DATA")

# Download 2019 imports data
comexdown.imp(year=2019, path="./DATA")
```

### Download code tables

```python
import comexdown

# Download NCM table (commodity codes)
comexdown.ncm(table="ncm", path="./DATA")

# Download UF table (state codes)
comexdown.ncm(table="uf", path="./DATA")
```

## Command Line Tool

Download trade transactions for a range of years:

```bash
comexdown trade 2008:2019 -o "./DATA"
```

Download code tables:

```bash
# Download all related code files
comexdown table all

# Download only the UF.csv file
comexdown table uf

# Download only the NCM_CGCE.csv file
comexdown table ncm_cgce

# Download only the NBM_NCM.csv file
comexdown table nbm_ncm
```

## Data Format

Downloaded files include:

- **year_month**: Year and month of transaction
- **hs_code**: HS commodity code (2-10 digits)
- **origin_country**: Country code (imports)
- **destination_country**: Country code (exports)
- **value_usd**: Value in USD
- **quantity**: Quantity in units
- **weight_kg**: Weight in kilograms
- **ncm_code**: Brazilian NCM code

## Development

Install for development:

```bash
git clone https://github.com/Quantilica/comexdown.git
cd comexdown
pip install -e .[dev]
```

Run tests:

```bash
pytest tests/
```

## Data Source

Brazilian foreign trade data: https://www.gov.br/produtividade-e-comercio-exterior/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta

## Learn More

- **[Foreign Trade Overview](index.md)** — All trade data tools
- **[IBGE Macro Data](../ibge/index.md)** — Aggregate trade statistics
- **[Architecture](../architecture/overview.md)** — System design
