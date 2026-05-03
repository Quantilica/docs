# Architecture Overview

How the Brazilian Public Data Suite is organized and how pieces connect.

## System Architecture

```mermaid
graph TD
    Sources["Government Data Sources<br/>(IBGE, Treasury, Labor, Trade, Health)"]
    
    Sources -->|IBGE SIDRA| SF["sidra-fetcher"]
    Sources -->|IBGE SIDRA| SQL["sidra-sql"]
    Sources -->|Treasury| TD["tddata"]
    Sources -->|RAIS/CAGED| PD["pdet-data"]
    Sources -->|Siscomex| CX["comexdown"]
    Sources -->|DATASUS| DS["datasus-fetcher"]
    
    SF --> Processing["Processing & Transformation<br/>(Polars Vectorial Processing)"]
    SQL --> Processing
    TD --> Processing
    PD --> Processing
    CX --> Processing
    DS --> Processing
    
    Processing --> Storage["Structured Storage"]
    
    Storage --> PQ["Parquet Files<br/>(Analytical)"]
    Storage --> PG["PostgreSQL<br/>(Operational)"]
    
    PQ --> Analytics["Analytics & BI<br/>(Dashboards, ML, Reports)"]
    PG --> Analytics
```

## Design Principles

### 1. Modularity

Each tool is **independent and reusable**:

- **sidra-fetcher**: `httpx` + `tenacity` only (no DataFrame deps; you bring Polars/Pandas)
- **tddata**: Async `httpx` + `tqdm`; optional `polars` + `altair` via `[analysis]` extra
- **pdet-data**: stdlib FTP + `polars` + `tqdm` (`7z` binary on PATH for extraction)
- **comexdown**: pure standard library — no third-party deps
- **datasus-fetcher**: pure standard library FTP client
- **inmet-bdmep-data**: `httpx` + `pandas` + `pyarrow` (+ optional `polars`)

No tool depends on another tool. Mix and match based on your needs.

### 2. Resilience

Government data sources are **unreliable**:

```
Problem: IBGE API times out randomly
Solution: Auto-retries with exponential backoff
         Timeout handling
         Partial failure tolerance

Problem: Rate limiting on API access
Solution: Built-in throttling
         Respect HTTP 429 responses
         Adaptive request pacing

Problem: Malformed responses
Solution: Validation on data shape/schema
         Type checking and casting
         Missing value handling
```

### 3. Performance

Brazilian datasets are **large**:

```
RAIS 2023:        ~60M records, ~850 MB CSV → ~100 MB Parquet
CAGED monthly:    ~500k-1M records
Treasury bonds:   ~1000 instruments × 20+ years
Siscomex:         ~10M transactions/month

Solution:
  - Columnar storage (Parquet): 80%+ compression
  - Lazy evaluation (Polars): Only compute what's needed
  - Streaming: Process in batches, not all-at-once
  - Aggregation: Reduce on-server before download
```

### 4. Reproducibility

All transformations are **deterministic and logged**:

- Same input → same output (deterministic hashing)
- Pipeline steps are recorded (lineage tracking)
- Data versions are tracked (timestamps, checksums)
- Transformations are idempotent (safe to re-run)

### 5. No Magic

**Explicit > Implicit**:

- You choose output format (Parquet, CSV, PostgreSQL)
- You see what data is being fetched and transformed
- Error messages are actionable
- No silent data loss or truncation

## Data Flow Example: Economic Analysis Pipeline

```python
# 1. EXTRACT: each tool uses its own access pattern
import polars as pl
from sidra_fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao

# SIDRA: build a Parametro and request the URL
gdp_param = Parametro(
    agregado="1620",
    territorios={"1": ["all"]},
    variaveis=["116"],
    periodos=[],
    classificacoes={},
    formato=Formato.A,
    decimais={"": Precisao.M},
)
with SidraClient(timeout=60) as client:
    gdp = pl.DataFrame(client.get(gdp_param.url()))

# Treasury Direct: convert raw CSVs to Parquet
from tddata.converter import convert_to_parquet
convert_to_parquet(src_dir="raw/tesouro", dest_dir="data/tesouro", dataset_type="precos")
bonds = pl.read_parquet("data/tesouro/precos.parquet")

# 2. TRANSFORM: Polars
combined = gdp.join(bonds, on="date", how="inner")
combined = combined.with_columns([
    pl.col("V").cast(pl.Float64, strict=False).pct_change().alias("gdp_growth"),
    pl.col("yield").pct_change().alias("yield_change"),
])

# 3. LOAD
combined.write_parquet("gdp_bonds_analysis.parquet")
combined.write_database(
    "gdp_bonds",
    connection="postgresql://user:pass@host/db",
    if_table_exists="replace",
)

# 4. ANALYZE
data = pl.read_parquet("gdp_bonds_analysis.parquet")
print(data.select(pl.corr("gdp_growth", "yield_change")))
```

## Tool Responsibilities

### Extractors (sidra-fetcher, tddata, pdet-data, comexdown, datasus-fetcher)

**Responsibility**: Reliably get data from government APIs

**Do**:

- Handle API quirks (pagination, rate limits, retries)
- Normalize date formats
- Validate schema
- Export to standard formats (Parquet, DataFrame)

**Don't**:

- Transform data (that's the user's job)
- Make analytic assumptions
- Hide failures silently

### Storage (Parquet / PostgreSQL)

**Responsibility**: Efficient, reliable data storage

**Parquet** (recommended for analysis):

- Columnar format (fast analytical queries)
- Highly compressed (80%+ space savings)
- Schema preserved
- No database infrastructure needed

**PostgreSQL** (recommended for operations):

- ACID transactions (consistency)
- Real-time data access
- Backups and replication
- Multi-user concurrency

### Processing (Polars, Pandas)

**Responsibility**: Fast, flexible data transformation

Use Polars for:

- Large files (Parquet, CSV)
- Complex transformations
- Lazy evaluation (optimization)

Use Pandas for:

- Integration with statistical libraries
- Complex custom functions
- Smaller datasets

## Deployment Patterns

### 1. Local Development

```mermaid
graph TD
    A["Your laptop"] --> B["Extract"]
    B --> C["Transform"]
    C --> D["Parquet files"]
    D --> E["Jupyter notebook<br/>Python script"]
```

**Best for**: Exploratory analysis, prototyping

### 2. Daily Batch Pipeline

```mermaid
graph TD
    A["Scheduled job<br/>(cron / orchestrator)"] --> B["Extract latest data"]
    B --> C["Validate"]
    C --> D["Transform"]
    D --> E["Append to storage"]
    E --> F["PostgreSQL<br/>(for applications)"]
    E --> G["Parquet<br/>(for analysis)"]
```

**Best for**: Operational data, reporting dashboards

### 3. Real-Time Streaming

```mermaid
graph TD
    A["Government API"] --> B["Monitor new data"]
    B --> C["Validate"]
    C --> D["Transform"]
    D --> E["Stream to database"]
    E --> F["Real-time dashboard<br/>alerts"]
```

**Best for**: Surveillance (epidemiology, trade monitoring)

### 4. Multi-Source Integration

```mermaid
graph TD
    A["Multiple APIs<br/>(IBGE, Treasury, Labor, Trade, Health)"] --> B["Extract in parallel"]
    B --> C["Join on common keys"]
    C --> D["Unified dataset"]
    D --> E["Data warehouse<br/>(PostgreSQL / Data lake)"]
    E --> F["Analytics, ML models, reports"]
```

**Best for**: Macroeconomic analysis, econometric modeling

## Performance Characteristics

### Extraction Time

| Tool | Typical Time | Data Volume |
|------|--------------|-------------|
| sidra-fetcher (single series) | 5-10s | 100-1000 rows |
| sidra-fetcher (all data) | 30-60s | 10k-100k rows |
| tddata (all bonds) | 5-10s | 1000 bonds |
| pdet-data (RAIS year) | 30-60s | 60M records |
| pdet-data (aggregated) | 5-10s | 10k-100k rows |
| comexdown (annual) | 10-20s | 1M-10M transactions |
| datasus-fetcher (disease) | 5-15s | 100k-1M records |

### Storage Size (Compressed Parquet)

| Data | Raw Size | Parquet | Compression |
|------|----------|---------|-------------|
| RAIS 2023 | ~850 MB | ~100 MB | 88% |
| Treasury (20 years) | ~5 MB | ~1 MB | 80% |
| CAGED (monthly) | ~50 MB | ~6 MB | 88% |
| Siscomex (annual) | ~500 MB | ~50 MB | 90% |

## Scalability

**For most use cases** (up to billions of rows):

- **Parquet files** on disk: Scale to TBs easily
- **Polars**: Process files larger than RAM using streaming
- **PostgreSQL**: Handle 100M+ rows with proper indexing

**For extreme scale** (petabytes):

- Consider data lake (S3/cloud object storage)
- Distributed processing (Spark, Dask, DuckDB)
- Cloud data warehouses (BigQuery, Redshift, Snowflake)

## Common Architecture Patterns

### Academic Research

```mermaid
graph TD
    A["Extract"] --> B["Clean & aggregate"]
    B --> C["Statistical analysis"]
    C --> D["Publication"]
```

### Business Intelligence

```mermaid
graph TD
    A["Daily extraction"] --> B["PostgreSQL"]
    B --> C["BI tool<br/>(Tableau, Power BI, Metabase)"]
    C --> D["Dashboard"]
```

### Econometric Forecasting

```mermaid
graph TD
    A["Extract multiple sources"] --> B["Join & aggregate"]
    B --> C["Time series modeling"]
    C --> D["Forecast"]
    D --> E["Real-time API"]
```

### Risk Management

```mermaid
graph TD
    A["Extract daily data"] --> B["Calculate risk metrics"]
    B --> C["PostgreSQL<br/>(real-time)"]
    C --> D["Alert system<br/>(if thresholds exceeded)"]
```

## Integration with External Tools

### Data Integration

- **API Gateway**: Serve processed data via REST API
- **Data Lake**: Parquet files on S3/Azure/GCS
- **Data Warehouse**: Load to Snowflake, BigQuery, Redshift
- **Reverse ETL**: Export insights back to operational systems

### Analytics & BI

- **Tableau / Power BI**: Connect to PostgreSQL
- **Jupyter**: Load Parquet files for ad-hoc analysis
- **R / Python**: Standard data science workflows
- **Spark**: Distributed processing for very large datasets

### ML & Forecasting

- **Scikit-learn**: Classification, regression
- **Prophet**: Time series forecasting
- **XGBoost**: Gradient boosting
- **TensorFlow**: Deep learning on time series

## Best Practices

### 1. Version Your Data

```
data/
├── gdp_2024_01_15.parquet
├── gdp_2024_01_20.parquet  # Re-fetched (data corrected)
└── gdp_latest.parquet      # Symlink to latest
```

### 2. Document Your Pipeline

```python
# Extract: IBGE SIDRA GDP table 1620, variable 116
# Frequency: Quarterly
# Update lag: ~60 days
# Last updated: 2024-01-20
```

### 3. Validate at Each Step

```python
# After extract
assert len(df) > 0, "No data returned"
assert "value" in df.columns, "Missing value column"

# After transform
assert df["date"].is_unique(), "Duplicate dates"
assert df["value"].is_null().sum() < 0.1 * len(df), ">10% missing"
```

### 4. Monitor Data Quality

```python
# Check for unusual changes
new_value = df.tail(1)["value"][0]
old_value = df.tail(2)["value"][0]
change = (new_value - old_value) / old_value

if abs(change) > 0.50:
    alert(f"Unusual change detected: {change*100:.1f}%")
```

## See Also

- [Design Principles](design-principles.md)
- [Concepts - Data Engineering](../concepts/data-engineering.md)
- [Concepts - Pipelines](../concepts/pipelines.md)
