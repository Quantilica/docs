# rtnpy — Brazilian Treasury Fiscal Results (RTN)

**rtnpy** is a Python package that downloads, extracts, and normalizes the *Resultado do Tesouro Nacional* (RTN) — Brazil's monthly federal fiscal results report. It turns the Treasury's multi-sheet Excel workbooks into clean long-format tables with hierarchical account expansion, ready for analysis or warehouse loading.

## What It Is

The *Resultado do Tesouro Nacional* contains consolidated fiscal data of the Brazilian Federal Government: revenues, expenses, and primary result, in current and constant values, monthly, quarterly, and annual, also as percentages of GDP. The Treasury publishes this as a sprawling Excel workbook with 24+ sheets, each with its own header layout and account hierarchy. `rtnpy` automates the fetch-and-normalize pipeline so you can go from the official URL to a tidy long-format table in a few lines of Python — or one CLI command.

**Source:** [Tesouro Nacional — RTN](https://www.gov.br/tesouronacional/pt-br/estatisticas-fiscais-e-planejamento/resultado-do-tesouro-nacional-rtn)

## The Challenge

- **Multi-sheet Excel** with shifting headers and merged cells across 24 supported sheets — header rows are not at fixed positions, requiring dynamic detection.
- **Wide-format account hierarchy**: codes like `1.2.3` carry implicit parent levels (`1`, `1.2`) that need to be expanded into a separate dimension table.
- **Mixed units and periods**: values appear as R$ millions, R$ constants, or % of GDP; periods mix monthly, quarterly, and annual — each sheet needs the right normalization.

## Features

- Auto-download of the latest RTN workbook with timestamp-based deduplication
- Reads 24 supported sheets covering monthly / quarterly / annual; current / constant; % of GDP
- Long-format output with hierarchical account expansion
- Unit normalization (R$ millions → reais; % of GDP preserved as a fraction)
- Period split into `year` / `month` or `year` / `quarter` columns
- Account hierarchy returned as a separate dimension table
- CLI for fetch and Excel/SQLite export

## Supported Sheets

| Sheets | Description | Period | Unit |
|--------|-------------|--------|------|
| 1.1, 1.2, 1.3, 1.4, 1.5, 1.6 | Monthly series, current values | Monthly | R$ |
| 1.1-A, 1.2-A, 1.3-A, 1.4-A, 1.5-A | Monthly series, constant values | Monthly | R$ |
| 1.2-B | Monthly series, 12-month rolling, IPCA-deflated | Monthly | R$ |
| 2.1, 2.2, 2.3, 2.4, 2.5 | Annual series, current values | Annual | R$ |
| 2.1-A, 2.2-A, 2.3-A, 2.4-A, 2.5-A | Annual series, % of GDP | Annual | Fraction of GDP |
| 4.1, 4.2 | Quarterly series, Central Government Budget | Quarterly | R$ |

Sheets `3.1` and `3.2` use a comparative current-publication layout with multi-level headers and are not yet normalized by the historical-series reader.

## Installation

Requires Python 3.13+.

```bash
pip install rtnpy
# or
uv add rtnpy
```

Dependencies: `httpx`, `openpyxl`, `beautifulsoup4`.

## Command-Line Interface

The package installs an `rtnpy` command with `fetch` and `export` subcommands:

```bash
rtnpy --help

# Fetch operations
rtnpy fetch metadata          # Build metadata.json from the publications page
rtnpy fetch download          # Download files listed in metadata.json
rtnpy fetch latest            # Download the most recent RTN workbook

# Export operations
rtnpy export excel            # Export to a formatted Excel workbook
rtnpy export sqlite           # Export to a SQLite database
```

### Fetch options

```bash
rtnpy fetch metadata --dest data --force
rtnpy fetch download --metadata data/metadata.json --concurrency 8
rtnpy fetch latest   --dest data
```

### Export options

```bash
rtnpy export excel  --data-dir data --output rtn_data.xlsx
rtnpy export sqlite --data-dir data --output rtn_data.db
```

Both `export` commands download the latest workbook and write all supported sheets along with the account-hierarchy dimension.

## Python API

### Download

```python
from pathlib import Path
from rtnpy import download_latest_file

filepath = download_latest_file(Path("data"))
print(f"Downloaded: {filepath}")
```

`download_latest_file` returns the `Path` of the downloaded file, or `None` if a current copy already exists in the destination.

### Read a single sheet

```python
from pathlib import Path
from rtnpy import read_sheet, write_table_to_csv

filepath = Path("data/rtn_202412301200.xlsx")
data, accounts = read_sheet(filepath, "1.2")

print(f"Data:    {data.nrows} rows x {data.ncols} cols")
print(f"Accounts:{accounts.nrows} rows x {accounts.ncols} cols")

write_table_to_csv(data,     Path("output/rtn_1_2_data.csv"))
write_table_to_csv(accounts, Path("output/rtn_1_2_accounts.csv"))
```

`read_sheet(filepath, sheet_name)` returns a `(data, accounts)` tuple of `Tbl` instances — the long-format fact table and the account-hierarchy dimension.

### Read every supported sheet

```python
from rtnpy import read_all_sheets

results = read_all_sheets(filepath)

for sheet_name, (data, accounts) in results.items():
    print(f"{sheet_name}: {data.nrows} data rows")
```

### Publication metadata

```python
from rtnpy import fetch_publications_metadata

publications = fetch_publications_metadata()
print(publications[0])
```

## Data Structure

### Fact table (long format)

| Column  | Type      | Description                                |
|---------|-----------|--------------------------------------------|
| year    | int       | Reference year                             |
| month   | int       | Reference month (monthly sheets)           |
| quarter | int       | Reference quarter (quarterly sheets)       |
| account | str       | Hierarchical account code                  |
| value   | int/float | Reais for currency sheets; fraction for % of GDP |

### Account hierarchy (dimension)

| Column        | Type | Description                              |
|---------------|------|------------------------------------------|
| account_code  | str  | Hierarchical code (e.g., `1.2.3`)        |
| account_name  | str  | Full account name                        |
| account_level | int  | Hierarchy depth                          |
| P_1, P_2, ... | str  | Name at each hierarchy level             |

### Example

```python
# Fact rows
year  month  account  value
2024  1      1.1      1500000000
2024  1      1.2      2300000000
2024  2      1.1      1600000000

# Hierarchy rows
account_code  account_name             account_level  P_1       P_2
1.1           1.1 Receitas Correntes   2              Receitas  Receitas Correntes
1.2           1.2 Receitas de Capital  2              Receitas  Receitas de Capital
```

## The `Tbl` Class

`rtnpy` ships with `Tbl`, a small column-oriented table — data is stored as a list of columns rather than rows. There is no Polars or Pandas dependency; `Tbl` is the only data structure you need to learn.

```python
from rtnpy import Tbl

t = Tbl([
    ["name", "Alice", "Bob"],
    ["age",  25,      30   ],
])

t["name"]                       # ["name", "Alice", "Bob"]
t.select("name")                # subset
t.assign(city=["SP", "RJ"])     # add/overwrite a column
t.melt(id_cols=["name"])        # wide -> long
t.rename(name="full_name")      # rename columns

for row in t.iter_rows():
    print(row)
```

Main methods: `select`, `assign`, `melt`, `transpose`, `insert`, `drop_rows`, `drop_cols`, `rename`, `iter_rows`, `get_header`. Attributes: `data`, `nrows`, `ncols`. All transformations return new tables — operations are non-mutating.

## Learn More

- **[Treasury Overview](index.md)** — All Treasury (Finance) tools
- **[tddata](tddata.md)** — Tesouro Direto microdata and portfolio analytics
- **[Tesouro Nacional — RTN](https://www.gov.br/tesouronacional/pt-br/estatisticas-fiscais-e-planejamento/resultado-do-tesouro-nacional-rtn)** — Official source
- **[Tesouro Nacional API](https://apiapex.tesouro.gov.br/)** — Publications metadata API
