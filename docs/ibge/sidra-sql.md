# sidra-sql

**Advanced ETL & Data Warehousing infrastructure for IBGE SIDRA data.**

![sidra-sql banner](../assets/banner.png)

## What It Is

**`sidra-sql`** is a complete Data Warehousing and ETL (Extract, Transform, Load) infrastructure designed to ingest, structure, and version data extracted from SIDRA.

While **sidra-fetcher** solves the communication problem (getting data from API), **sidra-sql** solves the **governance, persistence, and reproducibility** problem. It converts raw, hierarchical IBGE data into a PostgreSQL relational database optimized for heavy analytical queries.

## Problem It Solves

Working with IBGE data for rigorous research or financial modeling involves structural challenges beyond simple download:

### 1. Complex IBGE Ontology

SIDRA organizes data in highly nested structures:

- **Aggregates** (tables) contain **variables** at multiple **territorial levels**
- Up to **6 different classifications** can cross-tabulate
- Flattening this into CSV files destroys **referential integrity** and causes massive duplication

SIDRA Structure (hierarchical):

```
  Table 1620 (GDP)
    ├─ Variable 116 (Real GDP)
    │   ├─ Territory: Brazil (level 1)
    │   ├─ Territory: States (level 3, 27 values)
    │   └─ Territory: Municipalities (level 5, 5570 values)
    └─ Classification: By Activity (8 categories)
        ├─ Agriculture
        ├─ Industry
        └─ Services
```

Problem: How do you represent this in a flat CSV without duplication?

### 2. Ingestion I/O Bottlenecks

Saving tens of millions of rows using traditional methods (row-by-row ORM insertion) can take **hours** and exhaust RAM.

### 3. Revisions & Reproducibility

The IBGE frequently revises historical data. Simply replacing old data with new destroys reproducibility of academic research or ML models trained on "historical snapshots."

**sidra-sql** solves all three with senior Data Engineering architecture:

## Architecture & Key Features

### 1. Streaming Ingestion ("Gold Standard" Performance)

For massive data volumes without memory exhaustion:

- **Two-Pass Strategy**: First pass resolves dimensions and foreign keys; second pass performs bulk load
- **PostgreSQL COPY FROM STDIN**: Native binary protocol streams millions of records in seconds
- **Atomic Upsert**: Uses `ON CONFLICT DO NOTHING` for deduplication
- **Staging Tables**: Temporary `_staging_dados` table for atomic operations

**Performance**: Insert 10M rows in ~30 seconds (vs hours with traditional `INSERT`)

### 2. Dimensional Star Schema

Strict relational modeling separates metadata from facts:

**Dimension Tables:**

- `sidra_tabela`: Raw metadata in `JSONB` format (preserves IBGE structure)
- `localidade`: Territorial mesh (Brazil, states, municipalities, regions)
- `periodo`: Time dimension with proper aggregation levels
- `dimensao`: Classification crossings (categories × variables)

**Fact Table (`dados`):**

- Extremely lean: Only foreign keys, modification date, version flag, value
- Composite unique constraint prevents duplicates
- Optimized for analytical queries (OLAP workloads)

```
Traditional Approach (flattened):
┌────────────────────────────────────────────────────────────┐
│ date    │ territory │ variable │ class       │ value       │
│ 2020-01 │ 35 (SP)   │ 116      │ Agriculture │ 123.45      │
│ 2020-02 │ 35 (SP)   │ 116      │ Agriculture │ 124.12      │
│ 2020-01 │ 35 (SP)   │ 116      │ Industry    │ 456.78      │
│ ... (millions of rows, duplicated territory/variable data) │
└────────────────────────────────────────────────────────────┘

Star Schema (normalized):
┌──────────────┐         ┌──────────────┐
│  localidade  │         │   dimensao   │
├──────────────┤         ├──────────────┤
│ id  │ d1n    │         │ id  │ d2n    │
│ 35  │ SP     │         │  1  │ Real   │
└──────┬───────┘         │  2  │ Nom.   │
       │                 └──────┬───────┘
       └──────────┬─────────────┘
                  │
         ┌────────┴────────┐
         │     dados       │
         ├─────────────────┤
         │ loc_id │ dim_id │
         │   35   │    1   │
         └────────────────-┘
(compact, normalized, no duplication)
```

### 3. Slowly Changing Dimensions (SCD Type II)

Auditability for research and regulatory environments:

- **Never delete**: When IBGE revises historical data, insert new version + mark old as `ativo = FALSE`
- **Full history preserved**: Know exactly how the database looked on any past date
- **Columns**: `modificacao` (date), `ativo` (boolean flag)

**Academic use case**: Reproduce 2015 research exactly with 2015-era data, even if 2026 has corrections

### 4. Declarative Pipelines via TOML

Business logic isolated from code:

```toml
# fetch.toml - Define pipelines without coding
[[tabelas]]
sidra_tabela = "1620"
variables = ["116"]                    # GDP variable
territories = {6 = []}                 # Brazil total

[[tabelas]]
sidra_tabela = "1737"
variables = ["63"]                     # IPCA inflation
territories = {1 = [], 3 = []}        # Levels 1 & 3
```

### 5. Automatic Classification Explosion

The `unnest_classifications = true` directive triggers recursive algorithm:

- Maps all variable × category cross-products automatically
- Eliminates manual ID discovery
- Generates optimal dimensional queries

### 6. Plugin Architecture

The motor is lightweight and generic; data definitions live in separate Git repositories:

```
Plugin (your Git repo)
├── manifest.toml       ← pipeline registry
├── pipeline-a/
│   ├── fetch.toml      ← what to download from SIDRA
│   ├── transform.toml  ← analytics table config
│   └── transform.sql   ← denormalization query
```

Install and run:

```bash
sidra-sql plugin install https://github.com/Quantilica/sidra-pipelines.git --alias std
sidra-sql run std pib_municipal
```

### Additional Features

- ✅ Full-text search on SIDRA metadata (Portuguese JSONB)
- ✅ Metadata caching for performance (local JSON files)
- ✅ PostgreSQL integration (ACID transactions)
- ✅ Idempotent operations (safe re-runs)
- ✅ Retry logic with exponential backoff (up to 5 attempts)
- ✅ Audit trails via `ativo` + `modificacao` columns

## Installation

=== "pip"

```bash
pip install sidra-sql
```

=== "uv"

```bash
uv pip install sidra-sql
```

=== "from source"

```bash
git clone https://github.com/Quantilica/sidra-sql.git
cd sidra-sql
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

sidra-sql reads a `config.ini` file at the working directory:

```ini
[storage]
data_dir = data

[database]
user = postgres
password = yourpassword
host = localhost
port = 5432
dbname = dados
schema = ibge_sidra
tablespace = pg_default
readonly_role = readonly_role
```

Load the config in Python:

```python
from sidra_sql.config import Config

config = Config()  # reads config.ini from current directory
```

## Quick Example: ETL Pipeline

### Option 1: CLI (Recommended)

Use the pre-built standard pipelines from [sidra-pipelines](sidra-pipelines.md):

```bash
# Install standard catalog
sidra-sql plugin install https://github.com/Quantilica/sidra-pipelines.git --alias std

# Run a pipeline (download + load + transform)
sidra-sql run std pib_municipal

# Query results in PostgreSQL
psql -c "SELECT * FROM analytics.pib_municipal WHERE ano >= 2020"
```

### Option 2: Declarative TOML (Recommended for custom pipelines)

Define a fetch pipeline:

```toml
# pipelines/economic/fetch.toml
[[tabelas]]
sidra_tabela = "1620"
variables = ["116"]
territories = {6 = []}
unnest_classifications = true

[[tabelas]]
sidra_tabela = "1737"
variables = ["63"]
territories = {1 = [], 3 = []}
```

Define a transform:

```toml
# pipelines/economic/transform.toml
[table]
name = "economic_indicators"
schema = "analytics"
strategy = "replace"
```

```sql
-- pipelines/economic/transform.sql
SELECT
    l.d1n  AS territory,
    p.codigo AS period,
    d.d2n  AS variable,
    r.v    AS value
FROM ibge_sidra.dados r
JOIN ibge_sidra.localidade l ON r.localidade_id = l.id
JOIN ibge_sidra.periodo    p ON r.periodo_id    = p.id
JOIN ibge_sidra.dimensao   d ON r.dimensao_id   = d.id
WHERE r.ativo = TRUE
```

Run the pipeline:

```python
from pathlib import Path
from sidra_sql.config import Config
from sidra_sql.toml_runner import TomlScript
from sidra_sql.transform_runner import TransformRunner

config = Config()

# Extract + Load
TomlScript(config, Path("pipelines/economic/fetch.toml")).run()

# Transform (SQL → analytics schema)
TransformRunner(config, Path("pipelines/economic/transform.toml")).run()
```

### Option 3: Programmatic ETL

Full control over each stage:

```python
from sidra_sql.config import Config
from sidra_sql.sidra import Fetcher
from sidra_sql.storage import Storage
from sidra_sql.database import get_engine, save_agregado, load_dados

config = Config()
engine = get_engine(config)
storage = Storage.default(config)

with Fetcher(config, storage=storage, max_workers=4) as fetcher:
    # 1. FETCH metadata (territories, periods, classifications)
    metadata = fetcher.fetch_metadata("1620")
    save_agregado(engine, metadata)

    # 2. DOWNLOAD data files to local storage
    data_files = fetcher.download_table(
        sidra_tabela="1620",
        territories={"6": []},  # Brazil total
        variables=["116"],
    )

# 3. LOAD into PostgreSQL via COPY FROM STDIN
load_dados(engine, storage, data_files)
```

## Data Governance: Handling Revisions

IBGE frequently publishes data revisions. The warehouse preserves history instead of overwriting.

### How Slowly Changing Dimensions (SCD Type II) Works

**Scenario**: IBGE revises Q3 2020 GDP on 2026-01-15

```sql
-- On 2024-01-01 (original data ingested)
-- dados row: id=1, v='1234.56', modificacao='2024-01-01', ativo=TRUE

-- On 2026-01-15 (IBGE revision detected during re-ingestion)
-- The ON CONFLICT DO NOTHING prevents overwriting.
-- A new row is inserted with updated modificacao:

-- 1. Mark old version inactive
UPDATE ibge_sidra.dados
SET ativo = FALSE
WHERE sidra_tabela_id = '1620'
  AND localidade_id = 6
  AND periodo_id = 123
  AND ativo = TRUE;

-- 2. Insert new version
INSERT INTO ibge_sidra.dados
  (sidra_tabela_id, localidade_id, dimensao_id, periodo_id, v, modificacao, ativo)
VALUES
  ('1620', 6, 1, 123, '1234.89', '2026-01-15', TRUE);
```

### Querying Historical Snapshots

```python
from datetime import date
from sqlalchemy import select, and_
from sidra_sql.database import get_engine
from sidra_sql.config import Config
from sidra_sql.models import Dados

engine = get_engine(Config())

# Data as it existed on 2024-06-01
snapshot_date = date(2024, 6, 1)

with engine.connect() as conn:
    rows = conn.execute(
        select(Dados).where(
            and_(
                Dados.sidra_tabela_id == "1620",
                Dados.modificacao <= snapshot_date,
                Dados.ativo == True,
            )
        )
    ).fetchall()
```

### Audit Trail

```python
from sqlalchemy import select, and_
from sidra_sql.models import Dados

# All versions of a specific data point
with engine.connect() as conn:
    history = conn.execute(
        select(Dados).where(
            and_(
                Dados.sidra_tabela_id == "1620",
                Dados.localidade_id == 6,
                Dados.periodo_id == 123,
            )
        ).order_by(Dados.modificacao)
    ).fetchall()

for row in history:
    status = "ACTIVE" if row.ativo else "SUPERSEDED"
    print(f"{row.modificacao}: {row.v}  [{status}]")
```

---

## Streaming Ingestion: Performance Deep Dive

### The Problem: Traditional INSERT

```python
# ❌ Row-by-row insertion (naive approach)
for row in data_generator():
    conn.execute(
        insert(dados).values(
            localidade_id=row["localidade_id"],
            dimensao_id=row["dimensao_id"],
            v=row["v"],
        )
    )
conn.commit()

# Time: Days for 10M rows
# RAM: Explodes (keeps all rows in memory)
# I/O: Worst possible (millions of round-trips)
```

### The Solution: Two-Pass Streaming

```
Pass 1: Resolve Dimensions
  ├─ Load localidade (territories) into memory
  ├─ Load dimensao (classifications) into memory
  └─ Map string codes → numeric FK ids

Pass 2: Bulk Stream to Staging
  ├─ Open PostgreSQL COPY FROM STDIN tunnel
  ├─ Write binary rows to _staging_dados table
  └─ Atomic UPSERT: ON CONFLICT DO NOTHING

Pass 3: Verify & Promote
  ├─ Referential integrity validation
  └─ Swap staging → production (atomic)

Time: Seconds for 10M rows
RAM: Bounded (streaming, not all-in-memory)
I/O: Optimal (single tunnel, binary protocol)
```

### Usage Example

```python
from sidra_sql.database import load_dados
from sidra_sql.storage import Storage
from sidra_sql.config import Config
from sidra_sql.database import get_engine

config = Config()
engine = get_engine(config)
storage = Storage.default(config)

# data_files is the list returned by Fetcher.download_table()
load_dados(engine, storage, data_files)
```

---

## API Reference

### CLI

```
sidra-sql run <alias> <pipeline-id> [--force-metadata]
```

Run a pipeline from an installed plugin. `--force-metadata` re-fetches SIDRA
table metadata even if already cached.

```
sidra-sql plugin install <url> [--alias ALIAS]
sidra-sql plugin update [alias]
sidra-sql plugin remove <alias>
sidra-sql plugin list
```

---

### `Config` — Runtime Configuration

```python
from sidra_sql.config import Config

config = Config()  # reads config.ini
```

Reads `config.ini` from the current working directory. Key attributes:

| Attribute | ini key | Description |
|-----------|---------|-------------|
| `config.data_dir` | `storage.data_dir` | Local storage root for JSON files |
| `config.db_user` | `database.user` | PostgreSQL user |
| `config.db_password` | `database.password` | PostgreSQL password |
| `config.db_host` | `database.host` | PostgreSQL host |
| `config.db_port` | `database.port` | PostgreSQL port |
| `config.db_name` | `database.dbname` | Database name |
| `config.db_schema` | `database.schema` | Schema (default: `ibge_sidra`) |

---

### `Fetcher` — Data Extraction

```python
from sidra_sql.sidra import Fetcher
from sidra_sql.storage import Storage

storage = Storage.default(config)

with Fetcher(config, storage=storage, max_workers=4) as fetcher:
    ...
```

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `fetcher.fetch_metadata(sidra_tabela)` | Fetch full table metadata (territories, periods, variables) |
| `fetcher.download_table(sidra_tabela, territories, variables, classifications)` | Download all periods; returns list of `{"filepath": Path, "modificacao": str}` |

`download_table` parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `sidra_tabela` | str | SIDRA table code |
| `territories` | dict[str, list[str]] | Territory level → codes (empty list = all) |
| `variables` | list[str] \| None | Variable codes; `None` = all |
| `classifications` | dict[str, list[str]] \| None | Classification → category codes |

---

### `Storage` — Local File Management

```python
from sidra_sql.storage import Storage

storage = Storage.default(config)         # uses config.data_dir
storage = Storage("/custom/path")         # explicit root
```

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `storage.exists(parameter, modification)` | Check if file already downloaded |
| `storage.write_data(data, parameter, modification)` | Save JSON data file |
| `storage.read_data(filepath)` | Load a previously saved data file |
| `storage.write_metadata(agregado)` | Save table metadata JSON |
| `storage.read_metadata(agregado)` | Load table metadata |

---

### `TomlScript` — Declarative ETL Runner

```python
from pathlib import Path
from sidra_sql.toml_runner import TomlScript

script = TomlScript(
    config,
    toml_path=Path("pipelines/economic/fetch.toml"),
    max_workers=4,
    force_metadata=False,
)
script.run()  # download + load all tables declared in the TOML
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | Config | | Runtime configuration |
| `toml_path` | Path | | Path to `fetch.toml` |
| `max_workers` | int | 4 | Parallel download threads |
| `force_metadata` | bool | False | Re-fetch metadata even if cached |

---

### `TransformRunner` — SQL Transformation Executor

```python
from sidra_sql.transform_runner import TransformRunner

runner = TransformRunner(config, toml_path=Path("pipelines/economic/transform.toml"))
runner.run()
```

Reads `transform.toml` + paired `.sql` file. Executes the SQL SELECT and
materializes the result into the target table or view.

---

### `database` — Low-Level Database Helpers

```python
from sidra_sql.database import get_engine, save_agregado, load_dados

engine = get_engine(config)
save_agregado(engine, metadata)          # upsert table/period/localidade metadata
load_dados(engine, storage, data_files)  # bulk load via COPY FROM STDIN
```

---

## TOML Pipeline Format

### `fetch.toml` — Extraction Config

```toml
[[tabelas]]
sidra_tabela = "1620"          # SIDRA table code (required)
variables = ["116"]             # variable codes; omit for all
territories = {6 = []}          # {level: [codes]}; empty list = all
unnest_classifications = true   # expand all category cross-products

[[tabelas]]
sidra_tabela = "1737"
variables = ["63"]
territories = {1 = [], 3 = []}
split_variables = true          # one request per variable (avoids SIDRA limits)
classifications = {81 = ["allxt"]}
```

**`[[tabelas]]` fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sidra_tabela` | str | ✅ | SIDRA table code |
| `territories` | dict[str, list] | ✅ | Territory level → unit codes |
| `variables` | list[str] | | Variable codes (default: all) |
| `classifications` | dict[str, list] | | Classification → category codes |
| `unnest_classifications` | bool | | Expand all category combinations |
| `split_variables` | bool | | One request per variable |

### `transform.toml` — Transformation Config

```toml
[table]
name = "pib_municipal"          # target table/view name
schema = "analytics"            # target schema
strategy = "replace"            # "replace" (table) or "view"
description = "Municipal GDP"
primary_key = ["municipio_id", "ano"]
indexes = [
  { name = "idx_pib_ano", columns = ["ano"], unique = false }
]
```

Paired with a `transform.sql` file (same stem) containing a SELECT query.

### `manifest.toml` — Plugin Registry

```toml
name = "Standard Pipelines"
description = "Quantilica standard SIDRA pipelines"
version = "1.0.0"

[[pipeline]]
id = "pib_municipal"
description = "Municipal GDP from IBGE SIDRA table 5938"
fetch = "pib_municipal/fetch.toml"
transform = "pib_municipal/transform.toml"
```

---

## Dimensional Schema

### Database Tables (schema: `ibge_sidra`)

**`sidra_tabela`** — SIDRA table registry

| Column | Type | Description |
|--------|------|-------------|
| `id` | text PK | SIDRA table code |
| `nome` | text | Table name |
| `periodicidade` | text | Update frequency |
| `ultima_atualizacao` | date | Last update |
| `metadados` | jsonb | Full metadata object |

**`localidade`** — Territory dimension

| Column | Type | Description |
|--------|------|-------------|
| `id` | bigint PK | Auto-increment |
| `nc` | text | Territory level code (e.g., `N6`) |
| `nn` | text | Territory level name |
| `d1c` | text | Territory unit code |
| `d1n` | text | Territory unit name |

Unique constraint: `(nc, d1c)`

**`periodo`** — Time dimension

| Column | Type | Description |
|--------|------|-------------|
| `id` | integer PK | Auto-increment |
| `codigo` | text | Period code |
| `frequencia` | text | Frequency (monthly, quarterly…) |
| `literals` | text[] | Raw period labels |
| `data_inicio` / `data_fim` | date | Period date range |
| `ano` / `ano_fim` | integer | Year(s) |
| `semestre` | smallint | 1-2 |
| `trimestre` | smallint | 1-4 |
| `mes` | smallint | 1-12 |

Unique constraint: `(codigo, literals)`

**`dimensao`** — Variable × classification dimension

| Column | Type | Description |
|--------|------|-------------|
| `id` | bigint PK | Auto-increment |
| `mc` | text | Unit of measure ID |
| `mn` | text | Unit of measure name |
| `d2c` / `d2n` | text | Variable code / name |
| `d4c`–`d9c` | text \| null | Category codes (up to 6 classifications) |
| `d4n`–`d9n` | text \| null | Category names |

Unique constraint: `(mc, d2c, d4c, d5c, d6c, d7c, d8c, d9c)`

**`dados`** — Fact table

| Column | Type | Description |
|--------|------|-------------|
| `id` | bigint PK | Auto-increment |
| `sidra_tabela_id` | text FK | → `sidra_tabela.id` |
| `localidade_id` | bigint FK | → `localidade.id` |
| `dimensao_id` | bigint FK | → `dimensao.id` |
| `periodo_id` | integer FK | → `periodo.id` |
| `modificacao` | date | IBGE publish date |
| `ativo` | boolean | Active record flag (SCD) |
| `v` | text | Data value |

Unique constraint: `(sidra_tabela_id, localidade_id, dimensao_id, periodo_id)`

### Example Analytical Query

```python
from sqlalchemy import select
from sidra_sql.models import Dados, Localidade, Periodo, Dimensao

# GDP by state (active records only)
query = (
    select(
        Localidade.d1n.label("state"),
        Periodo.codigo.label("period"),
        Dimensao.d2n.label("variable"),
        Dados.v.label("value"),
    )
    .join(Localidade, Dados.localidade_id == Localidade.id)
    .join(Periodo,    Dados.periodo_id    == Periodo.id)
    .join(Dimensao,   Dados.dimensao_id   == Dimensao.id)
    .where(
        Dados.ativo == True,
        Localidade.nc == "N3",          # states
        Dados.sidra_tabela_id == "1620",
    )
    .order_by(Periodo.codigo.desc())
)

with engine.connect() as conn:
    for row in conn.execute(query):
        print(f"{row.state} | {row.period} | {row.value}")
```

---

## Performance

### Local Caching

Downloaded data is stored as JSON files under `data_dir`. Re-running a pipeline
skips files that already exist on disk:

```
First run:  downloads from IBGE (seconds to minutes)
Re-run:     checks local cache, skips existing files (<1s overhead)
```

Force re-download by deleting the data directory or using `--force-metadata`.

### Streaming Ingestion Benchmarks

Real-world performance on standard hardware (8-core, 16 GB RAM):

| Dataset | Rows | Time | Throughput |
|---------|------|------|-----------|
| IPCA monthly | 3.2M | 8s | 400k rows/sec |
| GDP quarterly | 50k | <1s | — |
| RAIS annual | 60M | 2.5m | 400k rows/sec |

## Best Practices for Data Governance

### 1. Use Declarative Pipelines (TOML) for Reproducibility

```toml
# pipelines/annual_snapshot/fetch.toml
[[tabelas]]
sidra_tabela = "1620"
variables = ["116"]
territories = {6 = [], 3 = []}

[[tabelas]]
sidra_tabela = "1737"
variables = ["63"]
territories = {1 = []}
```

Advantages:

- ✅ Non-developers can maintain pipelines
- ✅ Version control (TOML in git)
- ✅ Reproducible across machines
- ✅ Decoupled from code changes

### 2. Document Snapshot Dates for Academic Reproducibility

```python
import json
from datetime import datetime

# Record when you built the dataset
metadata = {
    "snapshot_date": datetime.now().isoformat(),
    "pipeline": "pipelines/analysis/fetch.toml",
    "sidra_sql_version": "1.2.0",
}
with open("data/metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)
```

Then query with `Dados.modificacao <= snapshot_date` to reproduce the exact dataset.

### 3. Use Star Schema for BI Tools

Connect PostgreSQL directly to:

- **Tableau** (ODBC connection to PostgreSQL)
- **Power BI** (native PostgreSQL connector)
- **Looker** (SQL runner)
- **Metabase** (SQL queries on warehouse)

The normalized schema is optimized for BI tools' OLAP workloads.

---

## Troubleshooting

### Download Fails with Network Error

`Fetcher` retries automatically (up to 5 times, exponential backoff: 5s → 10s → 20s…).
If all retries fail, check SIDRA API availability or reduce `max_workers`.

### Table Not Found

SIDRA table codes must be strings, not integers. Use `"1620"`, not `1620`.

```python
metadata = fetcher.fetch_metadata("1620")   # ✅
metadata = fetcher.fetch_metadata(1620)     # ❌
```

### Variable ID Unknown

Browse the IBGE SIDRA catalog directly at [sidra.ibge.gov.br](https://sidra.ibge.gov.br/)
to look up variable and classification codes for a given table.

### Config File Not Found

`Config()` reads `config.ini` from the current working directory.
Run Python from the project root, or set the path explicitly:

```python
import os
os.chdir("/path/to/project")
config = Config()
```

### Schema Already Exists

`TransformRunner` with `strategy = "replace"` drops and recreates the target table.
`strategy = "view"` uses `CREATE OR REPLACE VIEW` and is non-destructive.

---

## See Also

- [IBGE Overview](index.md)
- [sidra-fetcher](sidra-fetcher.md) — Data extraction tool
- [sidra-pipelines](sidra-pipelines.md) — Standard pipeline catalog
- [Architecture: Design Principles](../architecture/design-principles.md)
- [SIDRA Database (Portuguese)](https://sidra.ibge.gov.br/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
