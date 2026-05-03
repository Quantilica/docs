# Storage & Formats

Choosing the right storage for your data.

## Storage Options

### Parquet (Recommended for Analysis)

**What**: Columnar storage format, compressed

**Pros**:

- ✅ Highly compressed (80%+ savings vs CSV)
- ✅ Fast reads (columnar: only read needed columns)
- ✅ No database needed (just files)
- ✅ Language-agnostic (Python, R, Rust, etc.)
- ✅ Schema preserved
- ✅ Cloud-native (works with S3, GCS, Azure)

**Cons**:

- ❌ Not human-readable
- ❌ No concurrent writes
- ❌ No transactions

**Best for**:

- Historical data (archive)
- Analytical queries (dashboards, reports)
- Data exchange between systems
- Large datasets

**Example**:

```python
import polars as pl

df = pl.read_csv("large_file.csv")  # 850 MB
df.write_parquet("data.parquet")     # 100 MB (12% of original)

# Later, read only what you need
df = pl.read_parquet(
    "data.parquet",
    columns=["date", "salary"],  # Skip other columns
    filters=[("state", "==", "SP")]  # Filter on read
)
```

### PostgreSQL (Recommended for Operations)

**What**: Relational database, SQL interface

**Pros**:

- ✅ ACID transactions (consistency)
- ✅ Concurrent access (multiple users)
- ✅ Real-time updates
- ✅ SQL interface (powerful queries)
- ✅ Backups & replication built-in
- ✅ Foreign keys & referential integrity

**Cons**:

- ❌ Requires infrastructure (server, maintenance)
- ❌ Slower for very large analytical queries
- ❌ Row-oriented (not columnar)

**Best for**:

- Live data (constantly updated)
- Applications (need consistency)
- Multi-user environments
- Complex queries (SQL joins, aggregations)

**Example**:

```python
import polars as pl

# Write data via Polars (uses ConnectorX / SQLAlchemy under the hood)
df = pl.read_parquet("gdp.parquet")
db_uri = "postgresql://user:pass@localhost/db"
df.write_database("gdp", connection=db_uri, if_table_exists="replace")

# Read with SQL — Polars
result = pl.read_database_uri(
    """
    SELECT
        date,
        value,
        LAG(value) OVER (ORDER BY date) AS prev_value,
        (value - LAG(value) OVER (ORDER BY date)) / LAG(value) AS growth
    FROM gdp
    WHERE date >= '2020-01-01'
    ORDER BY date
    """,
    uri=db_uri,
)
```

### CSV (Simple, Human-Readable)

**What**: Plain text, comma-separated values

**Pros**:

- ✅ Human-readable
- ✅ Works everywhere
- ✅ No special tools needed

**Cons**:

- ❌ Slow to read large files (must parse text)
- ❌ Large file size (no compression)
- ❌ No type information (everything is string)
- ❌ Type ambiguity (is "1.5" a number or string?)

**Best for**:

- Small datasets (<100 MB)
- Data exchange with non-technical users
- One-time analysis

**Example**:

```python
import polars as pl

# Write
df.write_csv("data.csv")

# Read
df = pl.read_csv("data.csv")

# Without an explicit schema, Polars infers types per column —
# rows that disagree with the inferred type become null silently.
# For trustworthy CSV ingestion, always pass `schema=` or `dtypes=`.
```

### SQLite (Local, File-Based Database)

**What**: Lightweight SQL database in a single file

**Pros**:

- ✅ SQL interface
- ✅ No server needed (just a file)
- ✅ ACID transactions
- ✅ Good for small teams

**Cons**:

- ❌ Limited concurrent writes
- ❌ Not suitable for web-scale

**Best for**:

- Small projects (< 100 GB)
- Desktop applications
- Single-server deployments
- Learning SQL

**Example**:

```python
import polars as pl

# Polars `write_database` / `read_database_uri` accept a SQLAlchemy URI;
# SQLite uses sqlite:///<path>
db_uri = "sqlite:///data.db"

df = pl.read_parquet("data.parquet")
df.write_database("gdp", connection=db_uri, if_table_exists="replace")

result = pl.read_database_uri(
    "SELECT * FROM gdp WHERE year >= 2020",
    uri=db_uri,
)
```

## Format Comparison

| Format | Size | Speed | Schema | Type Safety | Concurrent |
|--------|------|-------|--------|-------------|------------|
| CSV | ⭐⭐⭐ (large) | ⭐ (slow) | ❌ | ❌ | ✅ (read-only) |
| Parquet | ⭐ (tiny) | ⭐⭐⭐ (fast) | ✅ | ✅ | ❌ (read-only) |
| PostgreSQL | ⭐⭐ (medium) | ⭐⭐ (fast) | ✅ | ✅ | ✅ |
| SQLite | ⭐⭐ (medium) | ⭐⭐ (fast) | ✅ | ✅ | ⚠️ (limited) |

## Choosing Storage: Decision Tree

```
Do you need to update data in place?
├─ Yes → PostgreSQL or SQLite
└─ No → Parquet

Need SQL interface?
├─ Yes → PostgreSQL or SQLite
└─ No → Parquet

Large analytical queries?
├─ Yes → Parquet
└─ No → PostgreSQL fine

File-based (no server)?
├─ Yes → Parquet or SQLite
└─ No → PostgreSQL

Multiple concurrent writers?
├─ Yes → PostgreSQL
└─ No → Parquet or SQLite

Need history/version control?
├─ Yes → Parquet (keep versions as separate files)
└─ No → Any format fine
```

## Storage Strategies

### Strategy 1: Parquet Archive + PostgreSQL Live

```
Parquet (long-term storage)
    ↓ [yearly archive]
    gdp_2015.parquet
    gdp_2016.parquet
    ...
    gdp_2024.parquet

PostgreSQL (live data)
    ↓ [latest months only]
    Last 12 months of data
    Updated daily
    
Benefits:
  - Efficient archival (cheap storage)
  - Fast live queries (current data in DB)
  - Recovery from archives if needed
```

### Strategy 2: Parquet Lake + Data Mart

```
Bronze Layer (raw)
    gdp_raw_2024_01_15.parquet
    
Silver Layer (validated)
    gdp_validated_2024_01_15.parquet
    
Gold Layer (processed)
    gdp_monthly_aggregates_2024.parquet
    gdp_sector_analysis_2024.parquet
    
Mart (optimized for specific use case)
    PostgreSQL tables (for dashboards)
    Materialized views (pre-computed results)
    
Benefits:
  - Full lineage (raw → processed)
  - Flexibility (can re-process from silver/bronze)
  - Performance (gold layer pre-computed)
```

### Strategy 3: Single PostgreSQL Database

```
PostgreSQL Database
    ├─ Tables (raw data)
    ├─ Views (common queries)
    ├─ Materialized views (pre-computed)
    └─ Indexes (fast lookups)

Backups
    └─ Daily dumps to Parquet (archive)

Benefits:
  - Simple (one system)
  - Powerful (SQL queries)
  - Safe (transactions, backups)
  
Drawbacks:
  - Server infrastructure needed
  - Not ideal for very large analytical workloads
```

## Compression Ratios

Real data from Brazilian sources:

| Data | Format | Size | Ratio |
|------|--------|------|-------|
| RAIS 2023 (60M rows) | CSV | 850 MB | 100% |
|  | Parquet | 100 MB | 12% |
| Treasury (20 years) | CSV | 5 MB | 100% |
|  | Parquet | 1 MB | 20% |
| CAGED monthly | CSV | 50 MB | 100% |
|  | Parquet | 6 MB | 12% |

**Typical Parquet compression: 80-90%**

## Performance Benchmarks

### Read Performance

```
File: RAIS 2023 (850 MB CSV, 100 MB Parquet)

CSV read (full):          12 seconds
Parquet read (full):      0.3 seconds
Parquet read (columns):   0.1 seconds
Parquet read (filtered):  0.05 seconds
  (filter: state == "SP")
```

### Query Performance

```
PostgreSQL query: "SELECT AVG(salary) FROM rais WHERE sector = 'agriculture'"

Without index: 50 ms
With index:    2 ms
```

## Best Practices

### 1. Use Appropriate Formats

```python
# Development: CSV (human-readable)
df.write_csv("output.csv")

# Storage: Parquet (efficient)
df.write_parquet("archive.parquet")

# Operations: PostgreSQL (live access)
df.write_database(
    "live_table",
    connection="postgresql://user:pass@host/db",
    if_table_exists="replace",
)
```

### 2. Version Your Data

```
data/
├── gdp_2024_01_10.parquet
├── gdp_2024_01_15.parquet  ← Corrected version
├── gdp_2024_01_20.parquet
└── gdp_latest.parquet      ← Symlink to latest
```

### 3. Compress Appropriately

```python
# Parquet with snappy compression (good balance)
df.write_parquet("data.parquet", compression="snappy")

# Or gzip (better compression, slower)
df.write_parquet("data.parquet", compression="gzip")

# Or uncompressed (fastest, largest)
df.write_parquet("data.parquet", compression="uncompressed")
```

### 4. Index Critical Columns

```sql
-- Speed up common queries
CREATE INDEX idx_gdp_date ON gdp(date);
CREATE INDEX idx_employment_state_sector ON employment(state, sector);
CREATE INDEX idx_bonds_maturity ON bonds(maturity_date);
```

### 5. Archive Old Data

```python
import polars as pl
from datetime import datetime, timedelta

df = pl.read_parquet("data.parquet")

# Keep last 2 years in PostgreSQL
cutoff = datetime.now() - timedelta(days=730)

current = df.filter(pl.col("date") >= cutoff)
current.write_database(
    "data_live",
    connection="postgresql://user:pass@host/db",
    if_table_exists="replace",
)

# Archive everything
df.write_parquet(f"archive_{datetime.now():%Y_%m_%d}.parquet")
```

## Migration Path

For projects growing over time:

```
Phase 1: CSV files
    └─ Development, exploration
    
Phase 2: Parquet files
    └─ Growing data, faster queries
    
Phase 3: SQLite database
    └─ Multiple tables, some concurrency
    
Phase 4: PostgreSQL
    └─ Production operations, multiple users
    
Phase 5: Data warehouse
    └─ Enterprise scale, multiple teams
```

## See Also

- [Data Engineering](data-engineering.md)
- [Pipelines](pipelines.md)
- [Architecture Overview](../architecture/overview.md)
