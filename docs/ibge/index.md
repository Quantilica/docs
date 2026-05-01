# IBGE: Macroeconomic Data

Brazilian Institute of Geography and Statistics (IBGE) is the official source for macroeconomic statistics. Its **SIDRA** system contains thousands of time series on GDP, inflation, employment, trade, and demographics.

## The SIDRA Challenge

SIDRA is Brazil's richest data source, but consuming it at scale encounters critical engineering challenges:

### Network Instability

- Government servers suffer from overload and rate limiting
- Transient errors (HTTP 429, 500+) interrupt pipelines
- Timeouts are frequent; retries require backoff strategies

### Parametric Complexity

- API uses cryptic positional URL structures: `/t/1620/n1/all/v/116/p/all/d/m`
- Manual URL construction is error-prone and difficult to maintain
- Missing a single parameter breaks the entire request

### Data Scale

- **Massive catalog**: 30,000+ tables across dozens of themes
- **Large files**: Some historical series span 50+ years with monthly/daily granularity
- **Complex structure**: Tables contain nested classifications, categories, and dimensions
- **Fragmented documentation**: Spread across multiple Portuguese-language websites

---

## The IBGE Data Tools Ecosystem

We provide **two complementary stacks** for different use cases:

### Stack 1: Flexible SDK (For Exploration & Custom Workflows)

**Tool:** `sidra-fetcher`

For data scientists and analysts who need:

- Quick notebook exploration
- Custom extraction logic
- On-demand data fetching
- Flexible output formats (Parquet, CSV, DataFrames)

```
IBGE SIDRA API
    ↓
sidra-fetcher (extraction + URL abstraction + retries)
    ↓
Your analysis (Python/Jupyter, Polars, pandas)
```

### Stack 2: Enterprise ETL (For Production Pipelines)

**Tools:** `sidra-sql` + `sidra-pipelines`

For data engineers building:

- Automated, reproducible pipelines
- Normalized relational databases
- Multi-user data warehouses
- Declarative (no-code) definitions

```
IBGE SIDRA API
    ↓
sidra-sql (motor: download + normalize + load)
    ↓
PostgreSQL (fully normalized schema)
    ↓
SQL transformations → Analytics tables
    ↓
Power BI, Metabase, SQL queries
```

---

## Tool Reference

### 🔍 Stack 1: Exploration & Notebooks

**[sidra-fetcher](sidra-fetcher.md) — Industrial-Grade SDK**

An advanced Python SDK for robust extraction:
- **Dual clients:** `SidraClient` (sync) vs `AsyncSidraClient` (async, 3x faster)
- **Smart resilience:** Exponential backoff, automatic retries
- **URL abstraction:** No magic strings; `Parametro` class
- **Strong typing:** Metadata as dataclasses, not dicts
- **Multiple formats:** Parquet, CSV, PostgreSQL, Polars DataFrames

**Best for:**
- Jupyter notebooks & quick exploration
- One-off analysis
- Small datasets (<100 MB)
- When you need custom transformation logic
- Academic research workflows

---

### 🏭 Stack 2: Production ETL

**[sidra-sql](sidra-sql.md) — ETL Motor**

Industrial-strength pipeline orchestration:

- **Plugin architecture:** Lightweight motor + separate data definitions
- **Full normalization:** 5-table relational schema (`sidra_tabela`, `localidade`, `periodo`, `dimensao`, `dados`)
- **Bulk loading:** PostgreSQL COPY protocol (400k+ rows/sec)
- **Idempotent operations:** Safe re-execution
- **SQL transformations:** Generate analytics tables automatically
- **SCD Type II audit trail:** `ativo` + `modificacao` columns preserve revision history

**[sidra-pipelines](sidra-pipelines.md) — Standard Library**

Pre-built catalog of production-ready pipelines:

- GDP, inflation, population, agriculture, etc.
- One-command deployment: `sidra-sql run std pib_municipal`
- Ready for Power BI, Metabase, analytics
- Extensible for custom datasets

**Best for:**

- Production data pipelines (hourly/daily)
- Enterprise data warehouses
- Multi-user access via PostgreSQL
- Reproducible, auditable datasets
- Academic/regulatory compliance
- Complex multi-table workflows

---

## When to Use Each Stack

| Dimension | Exploration (Stack 1) | Production (Stack 2) |
|-----------|---|---|
| **Setup time** | Minutes (pip install) | ~30 minutes (config + PostgreSQL) |
| **Maintenance** | None (ad-hoc) | Scheduled pipeline runs |
| **Data freshness** | On-demand | Hourly/daily/weekly |
| **Scalability** | Notebooks, personal use | Multi-user, enterprise |
| **Dependencies** | Python only | Python + PostgreSQL |
| **Data validation** | Manual | Automated (constraints, uniqueness) |
| **Audit trail** | Basic logging | Full SCD Type II versioning |
| **Transformation** | Python (Polars, pandas) | SQL (declarative) |
| **Sharing results** | CSV/Parquet exports | SQL queries + BI tools |

### Decision Tree

```
Do you need:
├─ Quick exploration in a notebook?
│  └─ Use sidra-fetcher ✓
├─ One-off data extraction?
│  └─ Use sidra-fetcher ✓
├─ Daily/hourly automated pipeline?
│  └─ Use sidra-sql + sidra-pipelines ✓
├─ Multi-user data warehouse?
│  └─ Use sidra-sql + sidra-pipelines ✓
├─ Fully normalized relational schema?
│  └─ Use sidra-sql ✓
└─ Custom transformation logic in Python?
   └─ Use sidra-fetcher ✓
```

---

## SIDRA Table Categories

| Category | Examples | Use Case |
|----------|----------|----------|
| **National Accounts** | GDP, GVA, investment | Macro analysis |
| **Prices & Inflation** | IPCA, IGP-M, IPC | Inflation tracking |
| **Industrial Production** | Output, capacity utilization | Cyclical analysis |
| **Trade** | Exports, imports, balance | Trade analysis |
| **Employment** | Unemployment, hours worked | Labor market |
| **Demographics** | Population, migration | Social research |
| **Agriculture** | Crops, livestock, forestry | Agricultural analysis |

---

## Common Use Cases

### 📊 Economic Monitoring (→ Stack 2: Production ETL)

Track Brazil's real-time economic performance with automated pipelines:

- GDP growth (quarterly and annual)
- Inflation (IPCA, INPC, IPCA-15)
- Industrial production

**Command:**

```bash
sidra-sql run std pib_municipal
sidra-sql run std ipca
```

### 📈 Macroeconomic Analysis (→ Either stack)

**Ad-hoc analysis:** Use `sidra-fetcher` in Python

```python
from sidra_fetcher import AsyncSidraClient
client = AsyncSidraClient()
gdp = await client.fetch(table="1620", variable=116)
```

**Recurring analysis:** Use `sidra-sql` + PostgreSQL

```sql
SELECT * FROM analytics.pib_municipal
WHERE ano >= 2020;
```

### 👥 Demographics & Social Research (→ Stack 2: Production ETL)

Population, household composition, census data:

```bash
sidra-sql run std censo_populacao
sidra-sql run std estimativa_populacao
```

### 🌾 Agricultural Analysis (→ Stack 2: Production ETL)

Crop production and livestock data:

```bash
sidra-sql run std pam_lavouras_temporarias
sidra-sql run std ppm_rebanhos
sidra-sql run std pevs_producao
```

---

## Example Workflows

### Workflow A: Quick Analysis (Stack 1)

```python
from sidra_fetcher import AsyncSidraClient
import asyncio

async def analyze_gdp():
    client = AsyncSidraClient()
    gdp = await client.fetch(table="1620", variable=116, initial_date="2020-01-01")
    gdp.write_parquet("gdp_recent.parquet")
    return gdp

# Run once, analyze in notebook
data = asyncio.run(analyze_gdp())
```

### Workflow B: Production Dashboard (Stack 2)

```bash
# 1. Install pipelines
sidra-sql plugin install https://github.com/Quantilica/sidra-pipelines.git --alias std

# 2. Run pipeline (creates PostgreSQL tables)
sidra-sql run std ipca

# 3. Connect Power BI to analytics.ipca table
# → Real-time dashboard ready
```

---

## Getting Started

### Quick Exploration (sidra-fetcher)

#### Step 1: Discover the Right Table

Browse the [SIDRA catalog](https://sidra.ibge.gov.br/) directly to find table codes,
variable codes, and classification IDs. Use the search bar (Portuguese) or navigate
by theme. Each table page shows:

- Table code (e.g., `1620` for GDP)
- Available variables and their codes
- Territorial levels supported
- Available classifications

You can also reverse-engineer URLs from the SIDRA website. Example URL:

```
https://sidra.ibge.gov.br/tabela/1620
```

Table code = `1620`. Click into the table to see variables and classifications.

#### Step 2: Extract Data

**Synchronous (single table):**

```python
from sidra_fetcher import SidraClient

client = SidraClient()
gdp = client.fetch(
    table="1620",
    variable=116,
    frequency="quarterly",
    initial_date="2015-01-01"
)
print(f"✓ Fetched {len(gdp)} observations")
```

**Asynchronous (multiple tables, 3x faster):**

```python
import asyncio
from sidra_fetcher import AsyncSidraClient

async def fetch_macro_suite():
    client = AsyncSidraClient()
    try:
        results = await asyncio.gather(
            client.fetch(table="1620", variable=116),  # GDP
            client.fetch(table="1612", variable=117),  # GVA
            client.fetch(table="1637", variable=119)   # Investment
        )
        return results
    finally:
        await client.aclose()

gdp, gva, investment = asyncio.run(fetch_macro_suite())
```

#### Step 3: Store and Analyze

```python
import polars as pl

# Calculate growth rates
gdp_analysis = gdp.with_columns([
    pl.col("value").pct_change().alias("qoq_growth"),
    pl.col("value").pct_change(4).alias("yoy_growth")
])

# Save to Parquet (80%+ compression)
gdp_analysis.write_parquet("gdp_quarterly.parquet")
```

### Production Pipeline (sidra-sql)

```bash
# 1. Install sidra-sql
git clone https://github.com/Quantilica/sidra-sql.git
cd sidra-sql
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Configure database
cat > config.ini << EOF
[storage]
data_dir = data

[database]
user = postgres
password = your_password
host = localhost
port = 5432
dbname = dados
schema = ibge_sidra
tablespace = pg_default
readonly_role = readonly_role
EOF

# 3. Install official pipelines
sidra-sql plugin install https://github.com/Quantilica/sidra-pipelines.git --alias std

# 4. Run a pipeline
sidra-sql run std pib_municipal

# 5. Query results
psql -U postgres -d dados << EOF
SELECT * FROM analytics.pib_municipal
WHERE ano >= 2015
ORDER BY localidade, periodo;
EOF
```

---

## Best Practices

### 1. Choose the Right Tool Early

- Notebook/exploration → sidra-fetcher
- Production pipeline → sidra-sql + sidra-pipelines

### 2. Use Async for Multi-Table Extraction

Concurrent fetching is 3x faster than sequential:

```python
# 30 seconds (sync)
client = SidraClient()
gdp = client.fetch(table="1620", variable=116)
gva = client.fetch(table="1612", variable=117)

# 10 seconds (async)
results = await asyncio.gather(
    client.fetch(table="1620", variable=116),
    client.fetch(table="1612", variable=117)
)
```

### 3. Filter Data on Fetch

Reduce data volume before loading:

```python
# Good: Filter by date on fetch
recent = client.fetch(
    table="1620",
    variable=116,
    initial_date="2020-01-01"
)

# Less efficient: Fetch all, filter locally
all_data = client.fetch(table="1620", variable=116)
recent = all_data.filter(pl.col("date") >= "2020-01-01")
```

### 4. Store to Parquet, Not CSV

Parquet is 80%+ smaller and faster to read:

```python
# Good
df.write_parquet("data.parquet")

# Not efficient
df.write_csv("data.csv")
```

### 5. Leverage Production Features in sidra-sql

Use idempotent operations for safe re-execution:

```bash
# Safe to run multiple times
sidra-sql run std pib_municipal

# Cached files skipped on re-run → near-instant completion
sidra-sql run std pib_municipal
```

---

## Troubleshooting

### "Table not found"

SIDRA table codes must be strings, not integers. Verify the table still exists at
[sidra.ibge.gov.br/tabela/{id}](https://sidra.ibge.gov.br/) — IBGE occasionally
deprecates or replaces tables.

```python
gdp = client.fetch(table="1620", variable=116)   # ✅ string
gdp = client.fetch(table=1620, variable=116)     # ❌ may fail
```

### Timeout errors

Increase timeout and retries:
```python
client = SidraClient(
    timeout=60,
    max_retries=5,
    backoff_factor=2
)
```

### PostgreSQL connection error (sidra-sql)

Verify `config.ini`:

- Database exists: `createdb dados`
- User has permissions: `ALTER USER postgres WITH PASSWORD 'password';`
- Schema exists or user can create it: `CREATE SCHEMA ibge_sidra;`
- Test connection: `psql -U postgres -h localhost -d dados`

### sidra-sql plugin not found

Verify installation:

```bash
sidra-sql plugin list
```

If empty, install the standard catalog:

```bash
sidra-sql plugin install https://github.com/Quantilica/sidra-pipelines.git --alias std
```

---

## Learn More

### Stack 1 (SDK):

- [sidra-fetcher Documentation](sidra-fetcher.md)

### Stack 2 (Production ETL):

- [sidra-sql Documentation](sidra-sql.md)
- [sidra-pipelines Catalog](sidra-pipelines.md)

### External Resources:

- [IBGE Official Website (Portuguese)](https://www.ibge.gov.br/)
- [SIDRA Database (Portuguese)](https://sidra.ibge.gov.br/)
