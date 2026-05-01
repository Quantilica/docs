# sidra-fetcher

Advanced SDK for programmatic extraction from IBGE's SIDRA API.

## What It Is

**`sidra-fetcher`** is a production-grade Python SDK (Software Development Kit) engineered for robust, scalable extraction of data from the Sistema IBGE de Recuperação Automática (SIDRA). 

It serves as the network infrastructure layer between IBGE servers and data science applications, replacing manual URL construction and error handling with a strongly-typed, object-oriented, and resilient interface.

## Problem It Solves

SIDRA is one of Brazil's richest data sources—housing everything from IPCA inflation to Census demographics. However, consuming this data at scale encounters **two severe engineering bottlenecks**:

### 1. Network Instability
Government servers frequently suffer overload, resulting in:
- Connection drops and timeouts
- Transient errors (HTTP 429 rate limiting, 500+ server errors)
- Scripts that fail and interrupt entire pipelines

### 2. Parametric Complexity
The SIDRA API uses cryptic positional URL structures:
```
/t/1737/n1/all/n3/all/v/2265/p/all/d/m
```

Manual URL construction via string concatenation is error-prone and difficult to maintain.

**`sidra-fetcher` was architected specifically to mitigate both bottlenecks:**

```python
# Instead of managing retries, pagination, and format conversion
data = client.fetch(table="1620", variable=116)
# You get a clean DataFrame with normalized dates and types
```

## Architecture & Key Features

### Dual Client Model (Sync + Async)
The library does not enforce a single concurrency paradigm. It exposes two main classes based on `httpx`:

- **`SidraClient`**: Synchronous client for point extractions, notebook exploration, or ThreadPoolExecutor-based workflows
- **`AsyncSidraClient`**: 100% asynchronous using `asyncio`. Fetch metadata, locations, and periods concurrently via `asyncio.gather()`, drastically reducing I/O-bound wait times

### Industrial-Grade Resilience (Smart Retries)
Implements tolerance policies using `tenacity`:
- ✅ Exponential backoff: Failed requests retry with increasing delays (5s → 10s → 20s...)
- ✅ Handles transient failures: `httpx.ReadTimeout`, `httpx.NetworkError`, HTTP 429/500+
- ✅ Respects infrastructure: Automatic throttling for government servers

### URL Abstraction Engine (`Parametro`)
The `sidra.py` module eliminates magic strings:
- ✅ Transforms Python dicts/lists → valid SIDRA URLs transparently
- ✅ Native enums for Formats (`Formato.A`, `Formato.C`) and Precision (`Precisao.M`, `Precisao.D2`)
- ✅ Reverse engineering: Parse URLs directly from SIDRA website → Python configuration objects

### Strict Domain Modeling (Strong Typing)
Abandons generic dictionaries for rich dataclasses:
- ✅ Query metadata → deeply nested `Agregado` objects
- ✅ Contains: `Variavel`, `Classificacao`, `Categoria`, `Periodo`, `Localidade`
- ✅ IDE autocompletion and linter integration
- ✅ Type safety at development time

### Additional Features
- ✅ Multiple output formats (Parquet, CSV, PostgreSQL, DataFrame)
- ✅ Transparent pagination (handled internally)
- ✅ Date normalization (ISO 8601)
- ✅ Status code tracking (suppressed values)
- ✅ Logging and debugging support

## Installation

=== "pip"

    ```bash
    pip install sidra-fetcher
    ```

=== "uv"

    ```bash
    uv pip install sidra-fetcher
    ```

=== "poetry"

    ```bash
    poetry add sidra-fetcher
    ```

## Async/Await: High-Throughput Data Extraction

For large-scale extractions, use the **`AsyncSidraClient`** to fetch multiple tables concurrently. This dramatically reduces total execution time when network I/O is the bottleneck.

### Sync vs Async Performance

**Sync approach** (sequential):
```
Fetch table 1620: 10 seconds
Fetch table 1612: 10 seconds
Fetch table 1637: 10 seconds
Total: 30 seconds
```

**Async approach** (concurrent):
```
Fetch tables 1620, 1612, 1637 in parallel
Total: ~10 seconds (3x faster!)
```

### Async Example

```python
import asyncio
import polars as pl
from sidra_fetcher import AsyncSidraClient

async def fetch_macroeconomic_suite():
    """
    Fetch GDP, GVA, and Investment data concurrently.
    Demonstrates the power of AsyncSidraClient.
    """
    client = AsyncSidraClient(timeout=60, max_retries=5)
    
    try:
        # Define extraction tasks
        tasks = [
            client.fetch(
                table="1620",      # GDP at constant prices
                variable=116,
                frequency="quarterly",
                initial_date="2015-01-01"
            ),
            client.fetch(
                table="1612",      # GVA by activity
                variable=117,
                frequency="quarterly"
            ),
            client.fetch(
                table="1637",      # Gross capital formation
                variable=119,
                frequency="quarterly"
            )
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        gdp, gva, investment = results
        
        # Combine and analyze
        combined = gdp.join(
            gva, on="date", how="inner", suffix="_gva"
        ).join(
            investment, on="date", how="inner", suffix="_inv"
        )
        
        # Save
        combined.write_parquet("macro_data.parquet")
        
        print(f"✓ Fetched {len(combined)} rows in ~10 seconds")
        return combined
        
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        await client.aclose()

# Run the async pipeline
if __name__ == "__main__":
    result = asyncio.run(fetch_macroeconomic_suite())
    print(result.head())
```

## Quick Example (Synchronous)

```python
from sidra_fetcher import SidraClient
import polars as pl

client = SidraClient()

# Fetch quarterly GDP (Table 1620, variable 116)
gdp = client.fetch(
    table="1620",
    variable=116,
    frequency="quarterly",
    initial_date="2015-01-01"
)

# Data is returned as Polars DataFrame
print(gdp.head())
# Output:
# shape: (24, 3)
# date       | value      | status_code
# 2015-01-01 | 1234.567   | null
# 2015-04-01 | 1245.890   | null
# 2015-07-01 | 1256.234   | null
# ...

# Calculate quarter-over-quarter growth
gdp_with_growth = gdp.with_columns([
    pl.col("value").pct_change().alias("qoq_growth")
])

# Save to Parquet (80%+ compression vs CSV)
gdp_with_growth.to_parquet("gdp_quarterly.parquet")
print(f"✓ Saved {len(gdp_with_growth)} observations")
```

## How It Works

### Architecture

```
High-level API call:
  client.fetch(table="1620", variable=116, ...)
    ↓
URL Abstraction Engine (Parametro):
  Converts Python args → SIDRA URL
  /t/1620/n1/all/v/116/p/all/d/m
    ↓
HTTP Client (with Resilience):
  Exponential backoff + smart retries
  Handles timeouts, rate limiting, transient errors
    ↓
Paginated responses:
  SIDRA returns data in pages (~2000 rows/page)
  Transparently reassembles full dataset
    ↓
Type normalization:
  Parses JSON → strongly-typed Polars DataFrame
  ISO 8601 dates, proper numeric types
    ↓
Return to user:
  Clean, validated Polars DataFrame
```

### URL Abstraction: No More Magic Strings

Instead of hand-crafting SIDRA URLs:

```python
# ❌ Error-prone (manual URL construction)
url = f"/t/1620/n1/all/v/116/p/all/d/m?lang=en"
# Easy to make mistakes with positional args

# ✅ Type-safe (Parametro abstraction)
from sidra_fetcher import Parametro

param = Parametro(
    tabela=1620,
    variavel=116,
    formato=Formato.C,  # Column-based
    precisao=Precisao.M  # Monthly precision
)
# IDE autocompletion + validation
```

### Reverse Engineering: URL to Python

Copied a URL from the SIDRA website? Paste it directly:

```python
from sidra_fetcher import parameter_from_url

url = "https://sidra.ibge.gov.br/api/values/table/1737/classifications/58/category/all/periods/all/..."

# Automatically parse to Parametro object
param = parameter_from_url(url)
print(param.tabela)  # 1737
print(param.variavel)  # 2265
```

### Authentication

SIDRA API is public—no authentication required. But rate limiting applies:

- Default: 1 request per second
- Can be adjusted with `rate_limit` parameter

```python
# More aggressive rate limit (5 requests/sec)
# Use with caution - may trigger API throttling
client = SidraClient(rate_limit=0.2)
```

### Retry Logic

Built-in exponential backoff:

```python
client = SidraClient(
    max_retries=5,        # Try up to 5 times
    backoff_factor=2,     # Wait 1s, 2s, 4s, 8s, 16s
    timeout=60            # 60-second timeout per request
)

# Fetch with automatic retries
data = client.fetch(table="1620", variable=116)
```

On repeated failures, raises `SidraClientError` with details.

## API Reference

### `SidraClient()` - Synchronous Client

Initialize the synchronous client for point extractions or thread-based parallelism:

```python
from sidra_fetcher import SidraClient

client = SidraClient(
    timeout=60,
    max_retries=5,
    backoff_factor=2,
    rate_limit=1.0,    # Seconds between requests (respects IBGE infrastructure)
    debug=False        # Enable debug logging
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `timeout` | int | 60 | Request timeout in seconds |
| `max_retries` | int | 5 | Max retry attempts before giving up |
| `backoff_factor` | float | 2 | Exponential backoff multiplier (1s → 2s → 4s...) |
| `rate_limit` | float | 1.0 | Minimum seconds between requests (prevents overwhelming IBGE) |
| `debug` | bool | False | Enable debug logging to stderr |

### `AsyncSidraClient()` - Asynchronous Client

Initialize the async client for concurrent, high-throughput extractions:

```python
from sidra_fetcher import AsyncSidraClient
import asyncio

async def main():
    client = AsyncSidraClient(
        timeout=60,
        max_retries=5,
        backoff_factor=2,
        rate_limit=0.5  # More aggressive rate limiting (every 0.5s)
    )
    
    try:
        # Fetch multiple tables concurrently
        results = await asyncio.gather(
            client.fetch(table="1620", variable=116),
            client.fetch(table="1612", variable=117),
            client.fetch(table="1637", variable=119)
        )
        return results
    finally:
        await client.aclose()  # Clean up connection pool

# Run
results = asyncio.run(main())
```

**When to use:**
- Fetching **multiple tables** (concurrent I/O)
- Large-scale data pipelines with many extraction tasks
- Minimizing total execution time (network I/O is the bottleneck)

### Domain Model: Strongly-Typed Objects

Instead of generic dictionaries, `sidra-fetcher` returns richly-structured dataclasses:

```python
from sidra_fetcher import SidraClient

client = SidraClient()

# Get metadata for a table
agregado = client.get_agregado(1620)

# Returns Agregado object (not a dict!)
print(f"Nome: {agregado.nome}")
print(f"Descrição: {agregado.descricao}")
print(f"Frequência: {agregado.frequencia}")

# Nested structure: Agregado → Variavel → Classificacao → Categoria
for variavel in agregado.variaveis:
    print(f"\nVariável: {variavel.id} - {variavel.nome}")
    
    for classificacao in variavel.classificacoes:
        print(f"  Classificação: {classificacao.nome}")
        
        for categoria in classificacao.categorias:
            print(f"    → {categoria.nome}")

# Strongly typed = IDE autocomplete + type checking
# No more 'dict' → 'KeyError' surprises
```

### `client.fetch()`

Fetch a single time series:

```python
data = client.fetch(
    table="1620",           # SIDRA table ID
    variable=116,           # Variable ID
    frequency="quarterly",  # Optional: "monthly", "quarterly", "annual", "daily"
    initial_date="2015-01-01",  # Optional: start date
    final_date="2023-12-31",    # Optional: end date
    dimensions=None,        # Optional: filter by dimensions
    classification=None     # Optional: filter by classification
)
```

**Returns:** Polars DataFrame with columns:
- `date`: ISO 8601 date (YYYY-MM-DD)
- `value`: Numeric value (float)
- `status_code`: "." for suppressed, None otherwise

### `client.fetch_multiple()`

Fetch multiple variables from one table efficiently:

```python
data = client.fetch_multiple(
    table="1620",
    variables=[116, 117, 118],
    frequency="quarterly"
)

# Returns DataFrame with columns:
# date, value_116, value_117, value_118
```

### `client.list_tables()`

Search the SIDRA catalog:

```python
# Search by keyword
tables = client.search_tables("GDP")

for table in tables:
    print(f"{table['id']}: {table['name']}")
```

## Output Formats

### Parquet (Recommended)

Columnar format, compressed, ideal for analytics:

```python
data = client.fetch(table="1620", variable=116)
data.to_parquet("gdp.parquet")

# Later, load efficiently
import polars as pl
df = pl.read_parquet("gdp.parquet")
```

### CSV

Human-readable, but less efficient:

```python
data.to_csv("gdp.csv")
```

### PostgreSQL

For operational access and data warehousing:

```python
data.to_postgres(
    table="sidra_gdp",
    connection_string="postgresql://user:pass@localhost/db"
)
```

Or using Polars directly:

```python
data.write_database(
    "sidra_gdp",
    connection_string="postgresql://user:pass@localhost/db",
    if_exists="append"
)
```

## Common Patterns

### Incremental Updates

Add new data without re-fetching everything:

```python
# Load existing data
existing = pl.read_parquet("gdp.parquet")
last_date = existing["date"].max()

# Fetch only new data
new_data = client.fetch(
    table="1620",
    variable=116,
    initial_date=last_date
)

# Combine and deduplicate
combined = pl.concat([existing, new_data]).unique(subset=["date"])
combined.to_parquet("gdp.parquet")
```

### Multi-Variable Pipeline

Fetch multiple variables and combine:

```python
# Option 1: Use fetch_multiple (more efficient)
data = client.fetch_multiple(
    table="1620",
    variables=[116, 117, 118]
)

# Option 2: Manual combination
gdp_nominal = client.fetch(table="1620", variable=116)
gdp_real = client.fetch(table="1620", variable=117)

combined = gdp_nominal.join(
    gdp_real,
    on="date",
    suffix="_real"
)
```

### Parallel Fetching

Fetch from multiple tables in parallel:

```python
from concurrent.futures import ThreadPoolExecutor

tables = [
    ("1620", 116),  # GDP
    ("1612", 116),  # GVA
    ("1637", 116),  # Investment
]

with ThreadPoolExecutor(max_workers=3) as executor:
    results = {
        table_id: executor.submit(
            client.fetch, table=table_id, variable=var_id
        )
        for table_id, var_id in tables
    }
    
    data = {k: v.result() for k, v in results.items()}
```

### Time Series Analysis

```python
import polars as pl

data = client.fetch(table="1620", variable=116, frequency="quarterly")

# Calculate growth rate
growth = data.with_columns([
    pl.col("value").pct_change().alias("qoq_growth"),
    pl.col("value").pct_change(4).alias("yoy_growth")
])

# Rolling average (2-year window)
smoothed = data.with_columns([
    pl.col("value").rolling_mean(window_size=8).alias("ma_2yr")
])
```

## Handling Missing Data

SIDRA marks suppressed values with ".":

```python
data = client.fetch(table="1620", variable=116)

# Filter missing values
clean = data.filter(pl.col("status_code") != ".")

# Count missing by year
missing_by_year = (
    data
    .with_columns(pl.col("date").dt.year().alias("year"))
    .filter(pl.col("status_code") == ".")
    .group_by("year")
    .agg(pl.col("status_code").count().alias("count"))
)
```

## Industrial-Grade Error Handling

The library automatically handles transient failures. Manual intervention is only needed for permanent errors.

### Automatic Retry Strategy

```python
from sidra_fetcher import SidraClient

client = SidraClient(
    max_retries=5,
    backoff_factor=2
)

# Automatic behavior on failure:
try:
    data = client.fetch(table="1620", variable=116)
    # Attempt 1: Timeout
    # [Wait 5 seconds]
    # Attempt 2: Timeout
    # [Wait 10 seconds]
    # Attempt 3: Success ✓
except Exception as e:
    print(f"Permanent failure after retries: {e}")
```

### Catching Specific Errors

```python
from sidra_fetcher import SidraClientError, SidraTimeoutError, SidraRateLimitError
import logging

logger = logging.getLogger(__name__)

try:
    data = client.fetch(table="1620", variable=116)
    
except SidraTimeoutError as e:
    logger.warning(f"API timeout (transient): {e}")
    # Retries already attempted. Consider trying again later.
    
except SidraRateLimitError as e:
    logger.warning(f"Rate limited: {e}")
    # IBGE is rejecting requests. Back off for a few minutes.
    
except SidraClientError as e:
    logger.error(f"Unrecoverable error: {e}")
    # Table doesn't exist, invalid variable, etc.
    raise
```

### Monitoring for Production Pipelines

```python
import logging
from sidra_fetcher import SidraClient

logging.basicConfig(level=logging.DEBUG)

client = SidraClient(debug=True)

# Enable detailed logging for debugging
data = client.fetch(table="1620", variable=116)
# Output:
# [DEBUG] SidraClient: Fetching table 1620, variable 116
# [DEBUG] SidraClient: Constructed URL: /t/1620/v/116/p/all/d/m
# [DEBUG] SidraClient: Attempt 1/5 to https://api.sidra.ibge.gov.br/...
# [DEBUG] SidraClient: Got 200 OK, 348 rows
# [DEBUG] SidraClient: Normalization: dates to ISO 8601, types inferred
```

## Performance Tips

### 1. Use Frequency Filter

Specify frequency to reduce data volume:

```python
# Good: Returns ~90 rows (quarterly for 22 years)
data = client.fetch(
    table="1620",
    variable=116,
    frequency="quarterly"
)

# Less good: Returns ~1000+ rows (monthly)
data = client.fetch(table="1620", variable=116, frequency="monthly")
```

### 2. Use Date Range

Limit historical data:

```python
# Fetch only recent 5 years (much faster)
data = client.fetch(
    table="1620",
    variable=116,
    initial_date="2019-01-01"
)
```

### 3. Batch Operations

Don't fetch in a loop:

```python
# Bad: Multiple round trips
for var_id in [116, 117, 118]:
    data = client.fetch(table="1620", variable=var_id)

# Good: One round trip
data = client.fetch_multiple(
    table="1620",
    variables=[116, 117, 118]
)
```

## Debugging

Enable debug logging:

```python
client = SidraClient(debug=True)

data = client.fetch(table="1620", variable=116)
# Output:
# [DEBUG] Fetching SIDRA table 1620, variable 116
# [DEBUG] API request: https://api.sidra.ibge.gov.br/values/table/1620/...
# [DEBUG] Response: 200 OK, 256 rows
```

## See Also

- [IBGE Overview](index.md)
- [sidra-sql](sidra-sql.md) — Table browser and catalog
- [Architecture](../architecture/overview.md)
