# Parquet + Polars Guide

Working with large labor datasets efficiently.

## Why Parquet?

Brazilian labor datasets are large:

- **RAIS 2023**: ~60 million employment records (~1 GB raw CSV)
- **CAGED monthly**: ~500k-1M job flows per month
- **Historical**: 30-40 years of data = multi-GB files

**CSV is slow**:
- Load entire file into memory
- Parse all data types
- Filtering requires full table scan

**Parquet is fast**:
- Columnar storage (only read needed columns)
- Compressed (~80% reduction)
- Predicate pushdown (filter before loading)
- Schema preserved (no type guessing)

## Quick Start

### Convert CSV to Parquet

```python
import polars as pl

# Read CSV
df = pl.read_csv("rais_2023.csv")

# Write Parquet
df.write_parquet("rais_2023.parquet")

# File size comparison:
# CSV: 850 MB
# Parquet: 120 MB (14% of original)
```

### Read Parquet

```python
import polars as pl

# Full read
df = pl.read_parquet("rais_2023.parquet")

# Selective columns (faster)
df = pl.read_parquet(
    "rais_2023.parquet",
    columns=["employee_id", "salary", "sector"]
)

# With filter
df = pl.read_parquet(
    "rais_2023.parquet",
    filters=[("state", "==", "SP")]
)
```

## Memory-Efficient Workflows

### Streaming Large Files

Don't load the entire file—process in batches:

```python
import polars as pl

# Stream mode: load in chunks
reader = pl.read_parquet(
    "rais_2023.parquet"
)

# Process in batches
batch_size = 100000
for i in range(0, len(reader), batch_size):
    batch = reader[i:i+batch_size]
    
    # Process batch
    result = batch.group_by("sector").agg(
        pl.col("salary").mean()
    )
    
    # Append to file
    result.write_parquet(f"output_{i}.parquet", append=True)
```

### Lazy Evaluation

Use lazy evaluation to optimize queries:

```python
import polars as pl

# Lazy (not evaluated yet)
query = (
    pl.scan_parquet("rais_2023.parquet")
    .filter(pl.col("state") == "SP")
    .select(["employee_id", "salary", "sector"])
    .group_by("sector")
    .agg(pl.col("salary").mean())
)

# Collect when ready
result = query.collect()

# Polars optimizes the query before execution:
# 1. Push filter down (state == "SP")
# 2. Select columns early (drop unused data)
# 3. Aggregate efficiently
```

## Common Tasks

### Filter by Multiple Criteria

```python
import polars as pl

# Read with filters
df = pl.read_parquet(
    "rais_2023.parquet",
    filters=[
        ("state", "in", ["SP", "RJ", "MG"]),
        ("salary", ">", 2000)
    ]
)

# Result: Only matching rows loaded
```

### Group and Aggregate

```python
import polars as pl

df = pl.read_parquet("rais_2023.parquet")

# Employment by state and sector
summary = (
    df.group_by(["state", "sector"])
    .agg([
        pl.col("employee_id").count().alias("num_employees"),
        pl.col("salary").mean().alias("avg_salary"),
        pl.col("salary").median().alias("median_salary"),
        pl.col("salary").std().alias("salary_std")
    ])
    .sort("state", "sector")
)

print(summary)
summary.write_parquet("employment_summary.parquet")
```

### Time Series Analysis

RAIS is annual (December 31 snapshot). For trends:

```python
import polars as pl

# Combine multiple years
data_2021 = pl.read_parquet("rais_2021.parquet")
data_2022 = pl.read_parquet("rais_2022.parquet")
data_2023 = pl.read_parquet("rais_2023.parquet")

combined = pl.concat([data_2021, data_2022, data_2023])

# Aggregate by year
by_year = (
    combined
    .with_columns(pl.lit(2021, 2022, 2023).alias("year"))  # Add year if not present
    .group_by(["year", "sector"])
    .agg([
        pl.col("employee_id").count().alias("employment"),
        pl.col("salary").mean().alias("avg_wage")
    ])
)

# Calculate growth
by_year = by_year.sort("year")
by_year = by_year.with_columns([
    pl.col("employment").pct_change().alias("employment_growth"),
    pl.col("avg_wage").pct_change().alias("wage_growth")
])

print(by_year)
```

### Top-N Queries

Find top sectors by employment:

```python
import polars as pl

df = pl.read_parquet("rais_2023.parquet")

# Top 10 sectors by employment
top_sectors = (
    df.group_by("sector")
    .agg(pl.col("employee_id").count().alias("employment"))
    .sort("employment", descending=True)
    .head(10)
)

print(top_sectors)
```

### Join Multiple Files

Combine RAIS with external data:

```python
import polars as pl

# RAIS employment
rais = pl.read_parquet("rais_2023.parquet")

# External data (sector metadata)
sector_info = pl.read_csv("sectors.csv")

# Join
enriched = rais.join(
    sector_info,
    left_on="sector",
    right_on="sector_code",
    how="left"
)

# Now have sector names, classifications, etc.
print(enriched.select(["sector", "sector_name", "salary"]).head())
```

## Schema Management

### Inspect Parquet Schema

```python
import polars as pl

# Get schema
df = pl.read_parquet("rais_2023.parquet")
print(df.schema)

# Output:
# {'employee_id': String,
#  'year': Int32,
#  'state': String,
#  'sector': String,
#  'occupation': String,
#  'education': String,
#  'salary': Float64,
#  'tenure_days': Int32}
```

### Cast Types

```python
import polars as pl

df = pl.read_parquet("rais_2023.parquet")

# Convert salary to integer (save space)
df = df.with_columns([
    pl.col("salary").cast(pl.Int32).alias("salary")
])

# Save with new schema
df.write_parquet("rais_2023_int.parquet")
```

### Add Computed Columns

```python
import polars as pl

df = pl.read_parquet("rais_2023.parquet")

# Add tenure groups
df = df.with_columns([
    pl.when(pl.col("tenure_days") < 90)
    .then("< 3 months")
    .when(pl.col("tenure_days") < 365)
    .then("3-12 months")
    .when(pl.col("tenure_days") < 1825)
    .then("1-5 years")
    .otherwise("> 5 years")
    .alias("tenure_group")
])

df.write_parquet("rais_2023_with_tenure_group.parquet")
```

## Performance Optimization

### Query 1: Compare CSV vs Parquet

**CSV read** (1 GB file):
```
Time: 12 seconds
```

**Parquet read** (same data):
```
Time: 0.3 seconds (40x faster)
```

**Parquet with filter**:
```
Time: 0.05 seconds (240x faster)
```

### Profile Your Queries

```python
import polars as pl
import time

df = pl.read_parquet("rais_2023.parquet")

# Time your operations
start = time.time()

result = (
    df
    .filter(pl.col("state") == "SP")
    .group_by("sector")
    .agg(pl.col("salary").mean())
)

elapsed = time.time() - start
print(f"Query took {elapsed:.3f} seconds")
```

### Partition Large Files

Store Parquet files by partition (e.g., by year or state):

```python
import polars as pl
from pathlib import Path

df = pl.read_parquet("rais_combined.parquet")

# Write partitioned by state
(
    df
    .with_columns(pl.col("state").alias("partition_state"))
    .write_parquet(
        "rais_partitioned",
        partition_by="partition_state"
    )
)

# Read only specific partition
sp_data = pl.read_parquet("rais_partitioned/partition_state=SP")
```

## Common Patterns

### Reproducible Analysis

```python
import polars as pl
from pathlib import Path

# Version your parquet files
today = Path.cwd().parent / "data"
today.mkdir(exist_ok=True)

# Save with timestamp
timestamp = "2024_01_15"
filename = today / f"rais_analysis_{timestamp}.parquet"

df = pl.read_parquet("rais_2023.parquet")
result = df.group_by("sector").agg(pl.col("salary").mean())

result.write_parquet(filename)

# Load consistent data later
result = pl.read_parquet(filename)
```

### Incremental Aggregation

Process monthly CAGED data as it arrives:

```python
import polars as pl
from pathlib import Path

data_dir = Path("caged_data")

# Aggregate all months available
dfs = []
for parquet_file in data_dir.glob("caged_2024_*.parquet"):
    df = pl.read_parquet(parquet_file)
    dfs.append(df)

combined = pl.concat(dfs)

# Aggregate once, save
summary = combined.group_by("state").agg(
    [pl.col("net_flow").sum()]
)

summary.write_parquet("caged_2024_summary.parquet")
```

## Troubleshooting

### Out of Memory on Large File

**Problem**: File is too large to load entirely

**Solution**: Use filtering on read:

```python
import polars as pl

# Instead of:
df = pl.read_parquet("huge_file.parquet")  # Crashes

# Use filter:
df = pl.read_parquet(
    "huge_file.parquet",
    filters=[("state", "==", "SP")]
)  # Fast, low memory
```

### Slow Queries on Parquet

**Problem**: Query is slower than expected

**Solution**: Use lazy evaluation:

```python
import polars as pl

# Eager (executes immediately)
df = pl.read_parquet("file.parquet")
result = df.filter(...)

# Lazy (optimizes first)
result = pl.scan_parquet("file.parquet").filter(...).collect()
```

### Type Mismatch on Write

**Problem**: Salary written as string instead of float

**Solution**: Cast before writing:

```python
import polars as pl

df = pl.read_parquet("rais.parquet")

# Fix types
df = df.with_columns([
    pl.col("salary").cast(pl.Float64)
])

df.write_parquet("rais_fixed.parquet")
```

## See Also

- [Labor Market Overview](index.md)
- [pdet-data Tool](pdet-data.md)
- [Polars Documentation](https://pola-rs.github.io/)
