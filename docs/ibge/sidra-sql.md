# sidra-sql

Advanced ETL & Data Warehousing infrastructure for IBGE SIDRA data.

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

```
SIDRA Structure (hierarchical):
  Table 1620 (GDP)
    ├─ Variable 116 (Real GDP)
    │   ├─ Territory: Brazil (level 1)
    │   ├─ Territory: States (level 3, 27 values)
    │   └─ Territory: Municipalities (level 5, 5570 values)
    └─ Classification: By Activity (8 categories)
        ├─ Agriculture
        ├─ Industry
        └─ Services

Problem: How do you represent this in a flat CSV without duplication?
```

### 2. Ingestion I/O Bottlenecks
Saving tens of millions of rows using traditional methods (row-by-row ORM insertion) can take **days** and exhaust RAM.

### 3. Revisions & Reproducibility
The IBGE frequently revises historical data. Simply replacing old data with new destroys reproducibility of academic research or ML models trained on "historical snapshots."

**sidra-sql** solves all three with senior Data Engineering architecture:

```python
# Instead of browsing IBGE website
browser = SidraTableBrowser()

# Search in code
inflation_tables = browser.search("inflation")
# or
inflacao_tables = browser.search("inflação")

# Get table details
table = browser.get("1620")
print(table.variables)
```

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
- Extremely lean: Only foreign keys, time reference (`d3c`), version flag, value
- Composite indexes and unique constraints prevent duplicates
- Optimized for analytical queries (OLAP workloads)

```
Traditional Approach (flattened):
┌─────────────────────────────────────────┐
│ date | territory | variable | class1 | value |
│ 2020-01 | 35 (SP) | 116 | Agr | 123.45 |
│ 2020-02 | 35 (SP) | 116 | Agr | 124.12 |
│ 2020-01 | 35 (SP) | 116 | Ind | 456.78 |
│ ... (millions of rows, duplicated strings)
└─────────────────────────────────────────┘

Star Schema (normalized):
┌──────────┐         ┌──────────┐
│ localidade│         │ dimensao │
│ id | name│         │ id | cat │
│ 35 | SP  │         │ 1  | Agr │
└──────────┘         │ 2  | Ind │
    ↑                └──────────┘
    │                    ↑
    └─── ┌──────────┐ ───┘
         │  dados   │
         │ loc_fk | dim_fk | value |
         │ 35 | 1 | 123.45 |
         └──────────┘
(Compact, normalized, no duplication)
```

### 3. Slowly Changing Dimensions (SCD Type II)
Auditability for research and regulatory environments:
- **Never delete**: When IBGE revises historical data, insert new version + mark old as `ativo = FALSE`
- **Full history preserved**: Know exactly how the database looked on any past date
- **Columns**: `modificacao` (timestamp), `ativo` (boolean flag)

**Academic use case**: Reproduce 2015 research exactly with 2015-era data, even if 2026 has corrections

### 4. Declarative Pipelines via TOML
Business logic isolated from code:

```toml
# fetch.toml - Define pipelines without coding
[[tabelas]]
sidra_tabela = "1620"
variables = ["116"]                    # GDP variable
territories = {6 = []}                 # Brazil total
unnest_classifications = true          # Expand categories

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
- ✅ Full-text search (English & Portuguese)
- ✅ Metadata caching for performance
- ✅ PostgreSQL integration (ACID transactions)
- ✅ Data validation and quality checks
- ✅ Audit trails (who changed what, when)
- ✅ Idempotent operations (safe re-runs)

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

Define pipelines without code:

```toml
# pipelines/economic.toml
[[tabelas]]
sidra_tabela = "1620"          # GDP
variables = ["116"]             # Real GDP
territories = {6 = []}          # Brazil total only
unnest_classifications = true

[[tabelas]]
sidra_tabela = "1737"          # IPCA inflation
variables = ["63"]
territories = {1 = [], 3 = []} # Levels 1 & 3 (Brazil + states)
```

Run pipeline:

```python
from sidra_sql import run_pipeline

# Load and execute pipeline
run_pipeline("pipelines/economic.toml", db_url="postgresql://user:pass@localhost/ibge")

# Data is now in PostgreSQL with proper dimensional schema
```

### Option 3: Programmatic ETL

Full control over ingestion:

```python
from sidra_sql import SidraWarehouse
from sidra_fetcher import AsyncSidraClient
import asyncio

async def build_warehouse():
    # Initialize warehouse
    warehouse = SidraWarehouse(db_url="postgresql://...")
    
    # Define tables to ingest
    tables_config = [
        {
            "sidra_tabela": "1620",
            "variables": ["116"],
            "territories": {6: []},  # Brazil
            "unnest_classifications": True
        },
        {
            "sidra_tabela": "1737",
            "variables": ["63"],
            "territories": {1: [], 3: []}  # Brazil + states
        }
    ]
    
    # Fetch with AsyncSidraClient (parallel)
    client = AsyncSidraClient()
    
    for config in tables_config:
        # 1. EXTRACT: Fetch from IBGE
        data = await client.fetch(
            table=config["sidra_tabela"],
            variable=config["variables"][0]
        )
        
        # 2. TRANSFORM: Apply business logic
        transformed = warehouse.transform(
            data,
            sidra_tabela=config["sidra_tabela"],
            unnest_classifications=config["unnest_classifications"]
        )
        
        # 3. LOAD: Stream to PostgreSQL
        warehouse.load(
            transformed,
            sidra_tabela=config["sidra_tabela"],
            streaming=True  # Uses COPY FROM STDIN for speed
        )
    
    await client.aclose()

# Execute ETL
asyncio.run(build_warehouse())
```

### Option 4: Table Browser (Discovery Only)

Find the right table before building pipelines:

```python
from sidra_sql import SidraTableBrowser

browser = SidraTableBrowser()

# Search for tables
inflation_tables = browser.search("inflation")

for table in inflation_tables:
    print(f"{table.id}: {table.name}")
    print(f"  Variables: {list(table.variables.keys())}")

# Get detailed metadata
table = browser.get("1737")  # IPCA
print(f"Description: {table.description}")
print(f"Update frequency: {table.frequency}")
print(f"Classifications: {[c.name for c in table.classifications]}")
```

## Data Governance: Handling Revisions

IBGE frequently publishes data revisions. The warehouse preserves history instead of overwriting:

### How Slowly Changing Dimensions (SCD Type II) Works

**Scenario**: IBGE revises Q3 2020 GDP on 2026-01-15

```python
# On 2024-01-01 (original data)
INSERT INTO dados VALUES
  (id=1, territorio=6, variable=116, value=1234.56, 
   modificacao='2024-01-01', ativo=TRUE)

# On 2026-01-15 (IBGE revision published)
# Instead of UPDATE/DELETE:

# 1. Mark old version inactive
UPDATE dados SET ativo=FALSE 
WHERE id=1 AND ativo=TRUE

# 2. Insert new version
INSERT INTO dados VALUES
  (id=2, territorio=6, variable=116, value=1234.89,
   modificacao='2026-01-15', ativo=TRUE)
```

### Reproducing Historical Research

```python
from datetime import datetime
from sqlalchemy import and_

# Query data as it was on 2024-06-01
snapshot_date = datetime(2024, 6, 1)

historical = warehouse.query_snapshot(
    fecha=snapshot_date,
    table="1620",
    variable=116
)
# Returns EXACTLY the data that existed on that date
# Even if IBGE has since revised it

# Current data (latest revisions)
current = warehouse.query_current(
    table="1620",
    variable=116
)
```

### Audit Trail

Every change is tracked:

```python
audit_trail = warehouse.audit_trail(
    table="1620",
    variable=116,
    territorio=6
)

for record in audit_trail:
    print(f"{record.modificacao}: {record.value} (ativo={record.ativo})")
```

---

## Streaming Ingestion: Performance Deep Dive

### The Problem: Traditional INSERT

```python
# ❌ Row-by-row insertion (naive approach)
for row in data_generator():
    db.session.execute(
        insert(dados).values(
            territorio=row['territorio'],
            variable=row['variable'],
            value=row['value']
        )
    )
db.session.commit()

# Time: Days for 10M rows
# RAM: Explodes (keeps all rows in memory)
# I/O: Worst possible (millions of round-trips)
```

### The Solution: Two-Pass Streaming

```
Pass 1: Resolve Dimensions
  ├─ Load localidade (territories) into memory
  ├─ Load dimensao (classifications) into memory
  └─ Map string IDs → numeric FK

Pass 2: Bulk Stream to Staging
  ├─ Open PostgreSQL COPY FROM STDIN tunnel
  ├─ Write binary protocol (fast)
  ├─ Write to _staging_dados table
  └─ Atomic UPSERT: ON CONFLICT DO NOTHING

Pass 3: Verify & Promote
  ├─ Data integrity checks
  ├─ Referential integrity validation
  └─ Swap staging → production (atomic)

Time: Seconds for 10M rows
RAM: Bounded (streaming, not all-in-memory)
I/O: Optimal (single tunnel, binary protocol)
```

### Usage Example

```python
warehouse = SidraWarehouse(db_url="postgresql://...")

# Automatically uses streaming ingestion
warehouse.load(
    data_frame,
    sidra_tabela="1620",
    streaming=True,
    batch_size=50000  # Tune based on RAM
)

# Monitor ingestion
stats = warehouse.ingestion_stats()
print(f"Inserted: {stats.rows_inserted}")
print(f"Skipped (duplicates): {stats.rows_skipped}")
print(f"Duration: {stats.duration_seconds:.1f}s")
```

---

## API Reference

### `SidraWarehouse()` - Data Warehousing & ETL

Initialize the warehouse for ingestion and analytics:

```python
from sidra_sql import SidraWarehouse
import sqlalchemy as sa

# Connect to PostgreSQL
db_url = "postgresql://user:pass@localhost/ibge_warehouse"
warehouse = SidraWarehouse(db_url=db_url)

# Or with SQLAlchemy engine
engine = sa.create_engine(db_url)
warehouse = SidraWarehouse(engine=engine)
```

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `warehouse.load(df, sidra_tabela, streaming=True)` | Ingest data with streaming (COPY FROM STDIN) |
| `warehouse.transform(df, sidra_tabela, unnest_classifications=True)` | Apply dimensional transformations |
| `warehouse.query_snapshot(fecha, table, variable)` | Query data as it was on a specific date (SCD) |
| `warehouse.query_current(table, variable)` | Query latest data (active records only) |
| `warehouse.audit_trail(table, variable, territorio)` | View all versions of a record |
| `warehouse.ingestion_stats()` | Get performance metrics |

### `SidraTableBrowser()` - Discovery & Metadata

Browse the SIDRA catalog:

```python
from sidra_sql import SidraTableBrowser

# Initialize
browser = SidraTableBrowser(
    refresh=False,              # Use cached catalog
    cache_dir="~/.sidra_cache"  # Custom cache location
)
```

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `browser.search(query)` | Full-text search (English & Portuguese) |
| `browser.get(table_id)` | Get detailed table metadata |
| `browser.list_themes()` | List available themes |
| `browser.list_by_theme(theme)` | Get all tables in theme |

### `run_pipeline()` - Declarative ETL

Execute a pipeline defined in TOML:

```python
from sidra_sql import run_pipeline

# Run pipeline
run_pipeline(
    config_file="pipelines/economic.toml",
    db_url="postgresql://user:pass@localhost/ibge",
    parallel=True,              # Use AsyncSidraClient
    batch_size=50000,           # Tune ingestion batch
    verbose=True                # Log progress
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config_file` | str | | TOML file with pipeline definitions |
| `db_url` | str | | PostgreSQL connection string |
| `parallel` | bool | True | Use async client for faster I/O |
| `batch_size` | int | 50000 | Rows per streaming batch |
| `verbose` | bool | False | Log detailed progress |

### `browser.search()`

Search for tables by keyword:

```python
# Search in English
gdp_tables = browser.search("GDP")

# Search in Portuguese
pib_tables = browser.search("PIB")

# Case-insensitive, searches title and description
employment = browser.search("employment")
```

**Returns:** List of table metadata objects

### `browser.get()`

Get a specific table by ID:

```python
table = browser.get("1620")  # GDP table

# Table object has attributes:
print(table.id)          # "1620"
print(table.name)        # Full table name
print(table.description) # Long description
print(table.theme)       # Theme/category
print(table.frequency)   # "monthly", "quarterly", etc.
print(table.variables)   # Dict of {id: name}
print(table.dimensions)  # List of dimensions
print(table.updated)     # Last update date
```

### `browser.list_by_theme()`

Browse tables by theme:

```python
# List all available themes
themes = browser.list_themes()
print(themes)
# Output: ['Economics', 'Demographics', 'Finance', 'Trade', ...]

# Get all tables in a theme
economic_tables = browser.list_by_theme("Economics")

for table in economic_tables:
    print(f"{table.id}: {table.name}")
```

## Dimensional Schema & Analytical Queries

Once data is loaded into PostgreSQL, you can run sophisticated analytical queries:

### Example 1: GDP by State (Latest Data Only)

```python
from sidra_sql import SidraWarehouse
import sqlalchemy as sa
from sqlalchemy import select

warehouse = SidraWarehouse(db_url="postgresql://...")

# Query the dimensional schema
from sidra_sql.models import Dados, Localidade, Periodo

query = (
    select(
        Localidade.nome,
        Periodo.periodo,
        sa.func.sum(Dados.valor).label("gdp_total")
    )
    .join(Localidade, Dados.localidade_fk == Localidade.id)
    .join(Periodo, Dados.periodo_fk == Periodo.id)
    .where(
        (Dados.ativo == True) &  # Only active records
        (Localidade.nivel == 3)   # States only
    )
    .group_by(Localidade.nome, Periodo.periodo)
    .order_by(Periodo.periodo.desc())
)

results = warehouse.execute(query)
for row in results:
    print(f"{row.nome}: R${row.gdp_total:.2f}B ({row.periodo})")
```

### Example 2: Historical Snapshot Query (Data Governance)

```python
from datetime import datetime

# Get data as it existed on 2024-06-01
# Even if IBGE has since published revisions

snapshot = warehouse.query_snapshot(
    fecha=datetime(2024, 6, 1),
    table="1620",
    variable=116,
    territorio=6  # Brazil total
)

print("GDP data from 2024-06-01 snapshot:")
for record in snapshot:
    print(f"Period: {record.periodo}, Value: {record.valor}")
```

### Example 3: Audit Trail (Who Changed What)

```python
# View all revisions of a specific data point
audit = warehouse.audit_trail(
    table="1620",
    variable=116,
    territorio=6,
    periodo="2020-01"
)

print("Revision history for Q1 2020 GDP:")
for version in audit:
    status = "✓ ACTIVE" if version.ativo else "✗ SUPERSEDED"
    print(f"{version.modificacao}: R${version.valor:.2f}B [{status}]")
```

### Example 4: Time Series Analysis

```python
# OLAP: Monthly GDP from 2015 onwards
timeseries = (
    select(
        Periodo.periodo,
        sa.func.avg(Dados.valor).label("gdp_avg"),
        sa.func.count().label("records")
    )
    .join(Periodo, Dados.periodo_fk == Periodo.id)
    .where(
        (Dados.ativo == True) &
        (Dados.sidra_tabela_fk == 1)  # GDP table
    )
    .group_by(Periodo.periodo)
    .order_by(Periodo.periodo)
)

# Pipe to Polars for analytics
import polars as pl
df = pl.from_arrow(
    warehouse.execute_arrow(timeseries)
)

# Calculate growth rates
df = df.with_columns([
    pl.col("gdp_avg").pct_change().alias("qoq_growth")
])
```

---

## Common Workflows

### Find GDP Data

```python
browser = SidraTableBrowser()

# Search for GDP
tables = browser.search("GDP")

# Display results
for table in tables:
    print(f"\n{table.id}: {table.name}")
    print(f"  Theme: {table.theme}")
    print(f"  Updated: {table.updated}")
    print(f"  Variables:")
    for var_id, var_name in table.variables.items():
        print(f"    {var_id}: {var_name}")
```

### Find Inflation Series

```python
# IPCA (main inflation index)
ipca_tables = browser.search("IPCA")

# IGP-M (wholesale inflation)
igp_tables = browser.search("IGP-M")

# IPC (consumer prices)
ipc_tables = browser.search("IPC")

# Display with variable meanings
for table_id in ["1419", "188", "7060"]:
    table = browser.get(table_id)
    print(f"\n{table.name}")
    for var_id, var_name in table.variables.items():
        print(f"  {var_id}: {var_name}")
```

### Explore Table Structure

```python
# Get a complex table
table = browser.get("6379")  # Employment

# Show all details
print(f"Table: {table.name}")
print(f"Description: {table.description}")
print(f"Frequency: {table.frequency}")
print(f"Theme: {table.theme}")

# Variables available
print(f"\nVariables ({len(table.variables)}):")
for var_id, var_name in sorted(table.variables.items()):
    print(f"  {var_id}: {var_name}")

# Dimensions (filters available)
print(f"\nDimensions ({len(table.dimensions)}):")
for dim in table.dimensions:
    print(f"  {dim['id']}: {dim['name']} ({len(dim['categories'])} categories)")
```

## Understanding SIDRA Structure

### Tables
Top-level identifier. Example: `1620` (GDP)

### Variables
Specific measures within a table. Example:
- Variable `116`: GDP at constant prices (2015 base)
- Variable `117`: GDP at current prices

### Dimensions
Filters available for a table. Example:
- Geography (state, municipality)
- Sector (agriculture, industry, services)
- Time period

### Classifications
Ways to categorize data. Example:
- By CNAE (economic activity)
- By occupation (CBO)

## Performance

### Caching

First call downloads the catalog (10-20 MB), subsequent calls use cache:

```python
# First call: ~5 seconds (downloads from IBGE)
browser = SidraTableBrowser()
tables = browser.search("GDP")

# Subsequent calls: <100ms (from cache)
tables = browser.search("inflation")
```

### Force Refresh

Update cache if IBGE adds new tables:

```python
browser = SidraTableBrowser(refresh=True)  # ~5 seconds
```

### Streaming Ingestion Benchmarks

Real-world performance on standard hardware (8-core, 16GB RAM):

| Dataset | Rows | Time | Throughput |
|---------|------|------|-----------|
| IPCA monthly | 3.2M | 8s | 400k rows/sec |
| GDP quarterly | 50k | <1s | - |
| RAIS annual | 60M | 2.5m | 400k rows/sec |

## Best Practices for Data Governance

### 1. Use Declarative Pipelines (TOML) for Reproducibility

```toml
# pipelines/annual_snapshot.toml
# Define what data you need, not how to fetch it
[[tabelas]]
sidra_tabela = "1620"
variables = ["116"]
territories = {6 = [], 3 = []}  # Brazil + states
unnest_classifications = false

[[tabelas]]
sidra_tabela = "1737"
variables = ["63"]
territories = {1 = []}  # National only
```

Advantages:
- ✅ Non-developers can maintain pipelines
- ✅ Version control (TOML in git)
- ✅ Reproducible across machines
- ✅ Decoupled from code changes

### 2. Leverage Snapshots for Academic Reproducibility

```python
# Document when you built your dataset
import json
from datetime import datetime

metadata = {
    "snapshot_date": datetime.now().isoformat(),
    "pipeline": "pipelines/analysis.toml",
    "warehouse_version": "1.2.0",
    "git_commit": "abc123def..."
}

with open("data/metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)

# Years later: Reproduce exactly
snapshot = warehouse.query_snapshot(
    fecha=datetime.fromisoformat(metadata["snapshot_date"])
)
```

### 3. Monitor Ingestion Performance

```python
warehouse.load(data, streaming=True, batch_size=50000)
stats = warehouse.ingestion_stats()

print(f"Performance Report:")
print(f"  Rows inserted: {stats.rows_inserted:,}")
print(f"  Rows skipped: {stats.rows_skipped:,}")
print(f"  Duration: {stats.duration_seconds:.1f}s")
print(f"  Throughput: {stats.rows_per_second:.0f} rows/sec")

# Tune batch_size if needed for your hardware
```

### 4. Use Star Schema for BI Tools

Connect your PostgreSQL warehouse directly to:
- **Tableau** (ODBC connection to PostgreSQL)
- **Power BI** (native PostgreSQL connector)
- **Looker** (SQL runner)
- **Metabase** (SQL queries on warehouse)

The normalized schema is optimized for BI tools' OLAP workloads.

---

## Troubleshooting

### Search Returns No Results

The catalog may use different terminology. Try:

```python
browser = SidraTableBrowser()

# If English search fails, try Portuguese
tables = browser.search("GDP")      # English
tables = browser.search("PIB")      # Portuguese

# If searching for specific concept, try synonyms
tables = browser.search("unemployment")
tables = browser.search("desemprego")
```

### Table Not Found

Table may have been removed or renamed:

```python
# Search for similar tables
browser = SidraTableBrowser(refresh=True)  # Force update
tables = browser.search("1620")  # Search by ID

# Or search by keyword
tables = browser.search("GDP")
```

### Variable ID Unknown

Use the browser to list all variables:

```python
table = browser.get("1620")

print("Available variables:")
for var_id in sorted(table.variables.keys()):
    print(f"  {var_id}")

# Then use with sidra-fetcher
from sidra_fetcher import SidraClient
client = SidraClient()
data = client.fetch(table="1620", variable=116)
```

## Integration with sidra-fetcher

Use results from **sidra-sql** to discover tables, then power **sidra-fetcher** for extraction:

```python
from sidra_sql import SidraTableBrowser
from sidra_fetcher import SidraClient

# Find inflation tables
browser = SidraTableBrowser()
tables = browser.search("inflation")

# For each table, fetch main variable
client = SidraClient()

for table in tables[:3]:  # First 3 tables
    # Get first variable
    var_id = list(table.variables.keys())[0]
    
    # Fetch data
    data = client.fetch(
        table=table.id,
        variable=var_id
    )
    
    print(f"Downloaded {len(data)} rows from {table.name}")
    
    # Save
    data.to_parquet(f"data/{table.id}.parquet")
```

---

## See Also

- [IBGE Overview](index.md)
- [sidra-fetcher](sidra-fetcher.md) — Data extraction tool
- [sidra-pipelines](sidra-pipelines.md) — Standard pipeline catalog
- [Architecture: Design Principles](../architecture/design-principles.md)
- [SIDRA Database (Portuguese)](https://sidra.ibge.gov.br/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
