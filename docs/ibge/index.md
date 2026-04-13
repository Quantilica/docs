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

## Our Solution: Advanced SDK + Table Browser

### **sidra-fetcher** — Industrial-Grade SDK

An advanced Python SDK engineered to solve both engineering bottlenecks:

**Architecture:**
- **Dual Client Model**: 
  - `SidraClient`: Synchronous, ideal for point extractions
  - `AsyncSidraClient`: Fully asynchronous (3x faster for multi-table extraction)
- **Smart Resilience**: Exponential backoff with automatic retries; handles timeouts, rate limiting, transient errors
- **URL Abstraction**: Eliminates magic strings via `Parametro` class; reverse engineering support
- **Strong Typing**: Metadata returned as dataclasses (`Agregado`, `Variavel`, `Classificacao`), not dicts
- **Multiple Formats**: Parquet, CSV, PostgreSQL, Polars DataFrames

**Example Performance:**
- Sync: Fetch 3 tables = 30 seconds
- Async: Fetch 3 tables in parallel = 10 seconds (3x faster)

### **ibge-sidra-tabelas** — Table Browser

Programmatic catalog navigation:
- Full-text search (English & Portuguese)
- Filter by theme
- Browse structure without leaving Python
- Find the right table programmatically

## Common Use Cases

### Economic Monitoring
Track Brazil's real-time economic performance:
- GDP growth (quarterly and annual)
- Industrial production
- Retail sales
- Investment flows

### Macroeconomic Analysis
Build macro models and economic indicators:
- Inflation (multiple measures: IPCA, IGP-M, IPC)
- Employment and unemployment
- Wage growth by sector
- Trade balance and exchange rates

### Demographics & Social Research
Population, household composition, labor force participation.

## Architecture: How sidra-fetcher & ibge-sidra-tabelas Work Together

```
┌─────────────────────────────────────────────────────┐
│     IBGE SIDRA API (Unreliable, Complex)            │
└─────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│  sidra-fetcher (Communication Layer)                 │
│  ────────────────────────────────────────────────    │
│  ✓ Smart retries & exponential backoff              │
│  ✓ Async for high throughput                        │
│  ✓ URL abstraction (no magic strings)               │
│  ✓ Returns: Clean Polars DataFrames                 │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│  ibge-sidra-tabelas (Data Warehousing Layer)        │
│  ────────────────────────────────────────────────    │
│  ✓ Streaming ingestion (COPY FROM STDIN)            │
│  ✓ Dimensional schema (Star model)                  │
│  ✓ Slowly Changing Dimensions (history)            │
│  ✓ Audit trails & reproducibility                  │
│  ✓ Declarative pipelines (TOML)                    │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│     PostgreSQL Data Warehouse (Optimized)           │
│     (Ready for BI, analytics, machine learning)     │
└──────────────────────────────────────────────────────┘
```

### When to Use Each Tool

**Use sidra-fetcher alone when:**
- Quick data exploration (notebook)
- One-off analysis
- Small datasets (<100 MB)
- You don't need historical audit trails

**Use ibge-sidra-tabelas when:**
- Building production data pipelines
- Need reproducibility (academic/regulatory)
- Handling large volumes (millions of rows)
- Multi-user access (share via PostgreSQL)
- Require historical data governance

**Use both together (recommended) when:**
- Enterprise data platform
- Long-term analytics infrastructure
- Team collaboration
- Need to track data revisions

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

## Getting Started

### Workflow: Discover → Extract → Analyze

#### Step 1: Discover the Right Table

```python
from ibge_sidra_tabelas import SidraTableBrowser

browser = SidraTableBrowser()

# Search (English or Portuguese)
gdp_tables = browser.search("GDP")
# or
tabelas_pib = browser.search("PIB")

for table in gdp_tables:
    print(f"{table.id}: {table.name}")
    print(f"  Theme: {table.theme}")
    print(f"  Available variables: {len(table.variables)}")
```

#### Step 2: Extract Data (Choose Sync or Async)

**Option A: Synchronous (single table or sequential)**

```python
from sidra_fetcher import SidraClient

client = SidraClient()

gdp = client.fetch(
    table="1620",
    variable=116,
    frequency="quarterly",
    initial_date="2015-01-01"
)

print(f"✓ Fetched {len(gdp)} quarterly observations")
```

**Option B: Asynchronous (multiple tables concurrently — 3x faster)**

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
print(f"✓ Fetched 3 tables in ~10 seconds (async vs 30s sync)")
```

#### Step 3: Store and Analyze

```python
import polars as pl

# Calculate economic growth rates
gdp_analysis = gdp.with_columns([
    pl.col("value").pct_change().alias("qoq_growth"),
    pl.col("value").pct_change(4).alias("yoy_growth")
])

# Save to Parquet (80%+ compression vs CSV)
gdp_analysis.to_parquet("gdp_quarterly.parquet")

# Or to PostgreSQL for operational access
gdp_analysis.to_postgres(
    table="gdp_quarterly",
    connection_string="postgresql://user:pass@localhost/db"
)
```

## Tools in This Section

### [sidra-fetcher](sidra-fetcher.md)
Advanced SDK for robust SIDRA extraction. Master:
- **Dual Clients**: `SidraClient` (sync) vs `AsyncSidraClient` (async)
- **Smart Resilience**: Exponential backoff, automatic retries, rate limiting
- **URL Abstraction**: `Parametro` class eliminates magic strings
- **Domain Modeling**: Strongly-typed metadata objects
- **Industrial Error Handling**: Production-grade logging and monitoring
- **Multiple Output Formats**: Parquet, CSV, PostgreSQL, DataFrames

### [ibge-sidra-tabelas](ibge-sidra-tabelas.md)
Complete Data Warehousing & ETL infrastructure. Build enterprise-grade data systems with:
- **Declarative Pipelines (TOML)**: Define what to fetch without coding
- **Streaming Ingestion**: Load 10M+ rows in seconds (COPY FROM STDIN protocol)
- **Star Schema (Dimensional Model)**: Optimized for analytical queries
- **Slowly Changing Dimensions (SCD)**: Preserve history for academic reproducibility
- **Table Discovery**: Full-text search (English & Portuguese)
- **Audit Trails**: Track all data revisions with modification timestamps

## Best Practices

### 1. Choose the Right Client: Sync vs Async

**Use `SidraClient` (Synchronous) when:**
- Fetching a single table
- Working in Jupyter notebooks
- Sequential extraction is acceptable

**Use `AsyncSidraClient` (Asynchronous) when:**
- Fetching multiple tables concurrently
- Building production pipelines
- Minimizing total execution time (network I/O is the bottleneck)

```python
# Sync: Good for single-table workflows
from sidra_fetcher import SidraClient
client = SidraClient()
gdp = client.fetch(table="1620", variable=116)

# Async: 3x faster for multi-table extraction
import asyncio
from sidra_fetcher import AsyncSidraClient

async def pipeline():
    client = AsyncSidraClient()
    results = await asyncio.gather(
        client.fetch(table="1620", variable=116),
        client.fetch(table="1612", variable=117)
    )
    await client.aclose()
    return results

asyncio.run(pipeline())
```

### 2. Know Your Table Structure Before Fetching

Use metadata exploration to avoid errors:

```python
from ibge_sidra_tabelas import SidraTableBrowser

browser = SidraTableBrowser()
table = browser.get("1620")  # GDP table

print(f"Name: {table.name}")
print(f"Description: {table.description}")
print(f"Available variables:")
for var_id, var_name in table.variables.items():
    print(f"  {var_id}: {var_name}")
```

### 3. Use Specific Date Ranges

Fetching all historical data can be slow. Always specify dates:

```python
# ✅ Good: Last 5 years
data = client.fetch(
    table="1620",
    variable=116,
    initial_date="2019-01-01"
)

# ❌ Slow: All historical (can take 30+ seconds)
data = client.fetch(table="1620", variable=116)
```

### 4. Handle Missing Data Properly

SIDRA uses "." for suppressed or unavailable values:

```python
import polars as pl

df = pl.read_parquet("gdp.parquet")

# Check for missing
missing_count = df.filter(pl.col("status_code") == ".").len()
print(f"Suppressed observations: {missing_count}")

# Remove if needed
clean = df.filter(pl.col("status_code") != ".")
```

### 5. Validate Data Quality

Always validate before storing or analyzing:

```python
# Schema validation
expected = {"date", "value", "status_code"}
assert expected.issubset(set(df.columns)), "Missing columns"

# Data completeness
assert len(df) > 100, "Too few observations"

# Date coverage
date_range = df['date'].max() - df['date'].min()
print(f"Data spans {date_range.days} days")
```

### 6. Leverage Async for Production Pipelines

In production, use async to maximize throughput:

```python
import asyncio
from sidra_fetcher import AsyncSidraClient
import logging

logging.basicConfig(level=logging.DEBUG)

async def daily_economic_pipeline():
    """
    Fetch full macro suite daily.
    With AsyncSidraClient: ~10 seconds
    With SidraClient: ~30 seconds
    """
    client = AsyncSidraClient(max_retries=5)
    
    try:
        tables = {
            "gdp": client.fetch(table="1620", variable=116),
            "inflation": client.fetch(table="1737", variable=63),
            "unemployment": client.fetch(table="6381", variable=4099)
        }
        results = await asyncio.gather(*tables.values())
        return dict(zip(tables.keys(), results))
    finally:
        await client.aclose()

# Run daily via cron or scheduler
data = asyncio.run(daily_economic_pipeline())
print("✓ Daily macro data updated")
```

## Performance Tips & Optimization

### 1. Use AsyncSidraClient for Multi-Table Extraction

Concurrent fetching is dramatically faster:

```python
import asyncio
from sidra_fetcher import AsyncSidraClient
import time

# ❌ Sync: Sequential = 30 seconds total
start = time.time()
client = SidraClient()
gdp = client.fetch(table="1620", variable=116)         # 10s
gva = client.fetch(table="1612", variable=117)         # 10s
inv = client.fetch(table="1637", variable=119)         # 10s
print(f"Sync time: {time.time() - start:.1f}s")  # ~30s

# ✅ Async: Concurrent = 10 seconds total
async def fetch_concurrent():
    start = time.time()
    client = AsyncSidraClient()
    try:
        results = await asyncio.gather(
            client.fetch(table="1620", variable=116),
            client.fetch(table="1612", variable=117),
            client.fetch(table="1637", variable=119)
        )
        print(f"Async time: {time.time() - start:.1f}s")  # ~10s
        return results
    finally:
        await client.aclose()

asyncio.run(fetch_concurrent())
```

### 2. Filter Data on Fetch

Reduce data volume before loading:

```python
# Good: Filter by date on fetch
recent = client.fetch(
    table="1620",
    variable=116,
    initial_date="2020-01-01"  # Only recent data
)

# Less good: Fetch all, filter locally
all_data = client.fetch(table="1620", variable=116)
recent = all_data.filter(pl.col("date") >= "2020-01-01")
```

### 3. Store to Parquet, Not CSV

Parquet is 80%+ smaller and faster to read:

```python
import polars as pl

df = pl.read_parquet("gdp.parquet")

# Save to Parquet (1 MB)
df.write_parquet("gdp_processed.parquet")  # ✅

# vs CSV (4.5 MB)
df.write_csv("gdp_processed.csv")  # ❌ Larger, slower
```

### 4. Incremental Updates for Production

Only fetch new data, not the entire history:

```python
import polars as pl
from sidra_fetcher import SidraClient

client = SidraClient()

# Load existing
existing = pl.read_parquet("gdp.parquet")
last_date = existing["date"].max()

# Fetch only new data
new_data = client.fetch(
    table="1620",
    variable=116,
    initial_date=last_date
)

# Combine and save
updated = pl.concat([existing, new_data]).unique(subset=["date"])
updated.to_parquet("gdp.parquet")

print(f"Updated: {len(new_data)} new observations")
```

### 5. Leverage Caching for Repeated Queries

Cache metadata to avoid repeated API calls:

```python
from ibge_sidra_tabelas import SidraTableBrowser

# First call: Downloads catalog (~20 MB, 5 seconds)
browser = SidraTableBrowser()
tables = browser.search("GDP")

# Subsequent calls: Use cache (<100 ms)
tables_2 = browser.search("inflation")  # Fast (cached)
tables_3 = browser.search("employment")  # Fast (cached)

# Force refresh if needed
browser = SidraTableBrowser(refresh=True)  # Re-download catalog
```

## Troubleshooting

### "Table not found"
SIDRA table IDs can change. Verify the table exists:

```python
browser = SidraTableBrowser()
try:
    table = browser.get("1620")
except ValueError:
    # Search for alternatives
    results = browser.search("GDP")
```

### Timeout errors
SIDRA API is slow. Increase timeout and add retries:

```python
client = SidraClient(
    timeout=60,
    max_retries=5,
    backoff_factor=2
)
```

### Inconsistent date formats
Output is normalized to ISO format (YYYY-MM-DD). But raw API may use different formats.

## Learn More

- [sidra-fetcher Documentation](sidra-fetcher.md)
- [ibge-sidra-tabelas Guide](ibge-sidra-tabelas.md)
- [IBGE Official Website (Portuguese)](https://www.ibge.gov.br/)
- [SIDRA Database (Portuguese)](https://sidra.ibge.gov.br/)
