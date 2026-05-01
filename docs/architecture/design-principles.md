# Design Principles

Core principles guiding the Brazilian Public Data Suite.

## 1. Modularity

Each tool is **independent**, **self-contained**, and **reusable**.

### Why Modularity?

- **Pick what you need**: Use only the tools relevant to your analysis
- **Avoid dependency hell**: No cascading updates breaking everything
- **Easy to test**: Each tool can be tested independently
- **Easy to replace**: Can swap one tool for another without rewriting pipelines

### How We Achieve It

```
sidra-fetcher     tddata         pdet-data      comexdown
├─ Depends: 3 pkgs ├─ Depends: 3 pkgs ├─ Depends: 3 pkgs ├─ Depends: 3 pkgs
└─ No deps on others

You can use ONLY sidra-fetcher without touching tddata or comexdown.
```

### Example: Two Analysts, Same Platform, Different Tools

```python
# Economist A: Only needs SIDRA metadata
from sidra_fetcher import SidraClient
with SidraClient() as client:
    agregado = client.get_agregado_metadados(1620)

# Economist B: Only needs labor market data
from pdet_data.fetch import connect, fetch_rais
ftp = connect()
fetch_rais(ftp, dest_dir="raw/rais")

# Economist C: Needs both + trade data
from sidra_fetcher import SidraClient
import comexdown
# (each tool uses its own access pattern; no shared abstraction required)
```

## 2. Resilience

Government infrastructure is **imperfect**. We handle failures gracefully.

### Problems We Address

```
PROBLEM                    SOLUTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
API timeout                Automatic retries with backoff
Network failure            Configurable timeout + error recovery
Rate limiting (429)        Built-in throttling + delay
Malformed response         Validation + schema checking
Slow API                   Pagination batching + async option
Partial failure            Continue with partial data (logged)
```

### Retry Logic Example

```python
from sidra_fetcher import SidraClient

# SidraClient retries metadata methods automatically via tenacity
# (3 attempts; exponential backoff on get_agregado_periodos)
with SidraClient(timeout=60) as client:
    agregado = client.get_agregado_metadados(1620)
    # Attempt 1: timeout
    # Attempt 2: timeout
    # Attempt 3: success ✓
```

### Error Handling Philosophy

```python
# DON'T: Silently drop data
try:
    data = fetch_data()
except Exception:
    return pd.DataFrame()  # Empty result = silent failure ❌

# DO: Log the failure, let user decide
try:
    data = fetch_data()
except TemporaryFailure as e:
    logger.warning(f"Temporary failure: {e}, retrying...")
    # Auto-retry happens here
except PermanentFailure as e:
    logger.error(f"Cannot recover: {e}")
    raise  # User handles it ✓
```

## 3. Performance

Brazilian datasets are **large**. We optimize for speed and memory.

### Storage: Parquet vs CSV

```
CSV: 850 MB
Parquet: 100 MB (12% of CSV size)
↓
Fast loading + low disk usage

Also: Columnar structure = fast analytical queries
```

### Query Optimization: Lazy Evaluation

```python
# Eager (traditional): Load everything, then filter
df = pd.read_csv("huge_file.csv")  # 10 seconds
result = df[df["state"] == "SP"]   # 5 more seconds

# Lazy (Polars): Optimize query plan first
df = pl.scan_csv("huge_file.csv")
result = df.filter(pl.col("state") == "SP").collect()
# Polars: Push filter down → read only matching rows
# ↓ 1 second total
```

### Streaming for Large Files

```python
# Process large files in batches, not all-at-once

import polars as pl

reader = pl.read_parquet("rais_2023.parquet")

batch_size = 100_000
for i in range(0, len(reader), batch_size):
    batch = reader[i:i+batch_size]
    # Process this batch
    result = batch.group_by("sector").agg(...)
    # Save intermediate result
```

## 4. Reproducibility

All transformations are **deterministic**. Same input = same output, always.

### Why Reproducibility Matters

```
Scenario: Build a model on 2023 GDP data
↓
Deploy model to production
↓
Later: Run model again on same data
↓
Result: Different output (because data changed)
↓
Problem: Can't debug (is code broken? Did data change?)

Solution: Version everything
```

### Best Practices

```python
from datetime import datetime

# 1. Version your data
gdp_file = f"data/gdp_{datetime.now():%Y_%m_%d}.parquet"

# 2. Log source and time
data_metadata = {
    "source": "IBGE SIDRA table 1620, variable 116",
    "fetch_date": "2024-01-15T14:32:00Z",
    "rows": 348,
    "date_range": ["2000-01-01", "2024-10-01"],
    "crc32": "0x1a2b3c4d"  # Checksum
}

# 3. Document transformations
"""
Pipeline:
1. Fetch from IBGE SIDRA
2. Normalize dates to ISO format
3. Type cast (string → float)
4. Remove missing values (status="." → None)
5. Save to Parquet
"""

# 4. Make operations idempotent
# (Safe to re-run without side effects)
df.write_parquet("output.parquet")  # Overwrites OK
# vs
df.write_parquet("output_append.parquet", append=True)  # Risk: duplicates
```

## 5. No Magic

**Explicit is better than implicit.**

### Anti-Pattern: Magic Happens Invisibly

```python
# Bad: Silent assumptions
df = fetch_gdp()  # Where from? Updated when? Cached?
# What if API fails? What if no data?
# User doesn't know.
```

### Pattern: Explicit Everything

```python
import polars as pl
from sidra_fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao

# Good: every parameter is named and visible
param = Parametro(
    agregado="1620",                      # GDP table
    territorios={"1": ["all"]},           # Brazil total
    variaveis=["116"],                    # Real GDP
    periodos=["202001", "202002", "202003", "202004"],
    classificacoes={},
    formato=Formato.A,
    decimais={"": Precisao.M},
)

with SidraClient(timeout=60) as client:
    rows = client.get(param.url())

# Explicit failure handling
if not rows:
    raise ValueError("No data returned from IBGE")

# Explicit output
gdp = pl.DataFrame(rows)
gdp.write_parquet("gdp_data.parquet")
print(f"Saved {len(gdp)} GDP observations to gdp_data.parquet")
```

### Transparency Checklist

- [ ] **What**: What data is being fetched?
- [ ] **Where**: What API/database/file?
- [ ] **When**: What date range?
- [ ] **How much**: How many rows?
- [ ] **Failures**: What happens if API fails?
- [ ] **Output**: Where does result go?
- [ ] **Format**: What format (Parquet/CSV/Database)?

## 6. User Control

Users, not libraries, decide **what to do with data**.

### Anti-Pattern: Library Decides

```python
# Bad: Library makes assumptions
gdp.save()  # Where? What format? Overwrite?

# Bad: Limited options
client.fetch(cache=True)  # Can't control cache location
```

### Pattern: User Decides

```python
# Good: user picks output format and destination
gdp.write_parquet("gdp.parquet")
gdp.write_csv("gdp.csv")
gdp.write_database("gdp_table", connection="postgresql://...")

# Good: client exposes a small, explicit knob set
client = SidraClient(timeout=120)
```

## 7. Data Integrity

**Never silently lose data.**

### Validation Checks

```python
# Check 1: Schema validation
expected_columns = {"date", "value", "status_code"}
actual_columns = set(df.columns)
assert expected_columns.issubset(actual_columns)

# Check 2: No unexpected nulls
null_rate = df["value"].is_null().sum() / len(df)
if null_rate > 0.10:
    logger.warning(f"High null rate: {null_rate*100:.1f}%")

# Check 3: Date coverage
first_date = df["date"].min()
last_date = df["date"].max()
expected_rows = (last_date - first_date).days / 90  # Quarterly

if len(df) < expected_rows * 0.8:
    logger.warning(f"Possible missing data (expected ~{expected_rows}, got {len(df)})")
```

### Idempotency

Operations should be safe to re-run:

```python
# Safe to re-run
df.write_parquet("output.parquet")  # Overwrites ✓

# Dangerous to re-run
df.write_parquet("output.parquet", append=True)
# Second run = duplicates ❌

# Better: With deduplication
combined = pl.concat([existing, new])
combined.unique().write_parquet("output.parquet")
```

## Decision Matrix

### When to Use Each Tool

| Need | Tool |
|------|------|
| IBGE macroeconomic data | sidra-fetcher |
| Brazilian government bonds | tddata |
| Employment & labor market | pdet-data |
| Trade flows (import/export) | comexdown |
| Health surveillance data | datasus-fetcher |
| Large file processing | Polars |
| Statistical analysis | Pandas / NumPy / Statsmodels |
| Dashboarding | PostgreSQL + BI tool |
| Time series forecasting | Prophet / ARIMA / ML |

## Implementation Checklist

When building tools for this suite:

- [ ] **Modularity**: No unnecessary dependencies on other tools
- [ ] **Error handling**: Specific error types, actionable messages
- [ ] **Retries**: Handle transient failures gracefully
- [ ] **Validation**: Check data schema and integrity
- [ ] **Logging**: Debug-friendly output
- [ ] **Performance**: Optimize for large datasets
- [ ] **Testing**: Comprehensive unit + integration tests
- [ ] **Documentation**: Clear examples and API docs
- [ ] **Backwards compatibility**: Don't break existing code
- [ ] **Reproducibility**: Deterministic output

## Philosophy

> **Build for the real world.**
>
> Government data is messy. APIs are unreliable. Networks are slow.
>
> Don't assume perfection. Handle failures. Validate data. Log decisions.
>
> Make users productive, not frustrated.

---

## See Also

- [Architecture Overview](overview.md)
- [Concepts - Data Engineering](../concepts/data-engineering.md)
