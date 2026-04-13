# Labor Market Data (Trabalho)

Brazilian labor market microdata from administrative sources: RAIS (annual employment census) and CAGED (monthly job flows).

**pdet-data** is a Big Data processing engine that transforms massive government labor datasets into production-ready analytics infrastructure—the first stage of a modern data stack for employment analysis.

## The Challenge

Brazilian labor market microdata encounters severe infrastructure barriers:

- **Memory Exhaustion**: Single RAIS files (50M+ rows) crash traditional tools (Pandas)
- **Format Inefficiency**: Legacy CSV/TXT formats are slow, untyped, and space-wasting
- **Temporary File Explosion**: Decompression requires disk space unavailable on cloud instances

**pdet-data** overcomes these through Polars vectorial processing, Apache Parquet columnar storage, and intelligent memory management.

## Data Sources

### RAIS (Relação Anual de Informações Sociais)
Annual employment census of all formal employment relationships:
- **Coverage**: ~60 million employment records per year
- **Available**: 1985-present
- **Content**: Demographics, wages, occupation, education, tenure, firm details
- **Size**: 8-10 GB per year (uncompressed)

### CAGED (Cadastro Geral de Empregados e Desempregados)
Monthly administrative record of job flows:
- **Coverage**: New hires and separations by sector/region
- **Available**: 1992-present (monthly)
- **Frequency**: Released with 3-week lag
- **Size**: 200-500 MB per month (uncompressed)

## Architecture: pdet-data Pipeline

```
┌─────────────────────────────────────────────────────┐
│     Brazilian Ministry of Labor (Raw Data)          │
│     RAIS: 8 GB/year CSV  |  CAGED: 200MB/mo CSV    │
└─────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│  pdet-data (Transformation Engine)                   │
│  ────────────────────────────────────────────────    │
│  ✓ Multithreaded Polars processing                  │
│  ✓ Raw-to-Parquet conversion (95%+ compression)     │
│  ✓ Intelligent memory management                    │
│  ✓ Idempotent processing (cache unchanged files)    │
│  ✓ Returns: Typed, indexed Parquet DataFrames       │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│     Your Analysis Layer                             │
│     (Wage analysis, job creation, demographics)     │
└──────────────────────────────────────────────────────┘
```

## Capabilities

- ✅ **Raw-to-Parquet**: Convert 8 GB CSV → 0.4 GB Parquet (95% compression)
- ✅ **Multithreaded**: Process 100M+ records in seconds
- ✅ **Memory-efficient**: Minimal disk footprint during transformation
- ✅ **Idempotent**: First run 60s → cached runs <0.1s (600x speedup)
- ✅ **Typed schema**: Automatic data type detection and validation
- ✅ **Production-ready**: Versioned outputs, daily pipelines

## Use Cases

### Labor Market Monitoring
Track employment trends, unemployment flows, and job creation by sector.

### Wage Analysis
Study wage levels, inequality, and sectoral differences using RAIS.

### Regional Economics
Analyze labor market specialization and economic structure by state/municipality.

### Education & Skills
Examine relationship between education levels and employment outcomes.

### Firm Dynamics
Study job creation patterns and firm growth using RAIS historical panels.

## Tools

### pdet-data
Fetch RAIS and CAGED data with automatic aggregation and Parquet export.

**Use when**: You need employment data by state, sector, or education level.

### guia-parquet
Guide to working with large labor datasets using Polars and Parquet.

**Use when**: You're processing large RAIS/CAGED files for analysis.

## Data Structure

### RAIS Fields (Selection)

| Field | Type | Description |
|-------|------|-------------|
| **year** | int | Report year |
| **employee_id** | str | Anonymized employee ID |
| **employer_id** | str | CNPJ/firm ID |
| **state** | str | State (UF) |
| **municipality** | str | Municipality code |
| **occupation_code** | str | CBO (occupation) |
| **education** | str | Education level |
| **salary** | float | Monthly salary (R$) |
| **start_date** | date | Employment start date |
| **end_date** | date | Employment end date (if separated) |
| **sector** | str | CNAE (economic sector) |

### CAGED Fields (Selection)

| Field | Type | Description |
|-------|------|---------|
| **year_month** | date | Year-month of report |
| **state** | str | State (UF) |
| **sector** | str | CNAE (economic sector) |
| **admissions** | int | New hires during month |
| **demissions** | int | Separations during month |
| **net_flow** | int | admissions - demissions |

## Workflow: Transform → Load → Analyze

### Step 1: Transform Raw RAIS to Parquet (Idempotent)

```python
from pdet_data import RAISProcessor
import polars as pl

processor = RAISProcessor()

# Idempotent: checks modification time, skips if unchanged
result = processor.process_year(
    year=2023,
    force_refresh=False,  # Use cache if available
    output_format="parquet"
)

print(f"✓ Processed {result.row_count:,} records")
print(f"  Compression: {result.input_size_gb:.1f}GB → {result.output_size_mb:.0f}MB")

# Load processed data
df = pl.read_parquet(result.path)
```

### Step 2: Multi-Year Analysis with Polars

```python
import polars as pl
from pdet_data import RAISProcessor

processor = RAISProcessor()

# Process 30 years (idempotent—cached runs are instant)
all_data = []
for year in range(1994, 2024):
    result = processor.process_year(year, force_refresh=False)
    df = pl.read_parquet(result.path).with_columns(
        pl.lit(year).alias("year")
    )
    all_data.append(df)

# Concatenate all years (Polars handles 100M+ rows)
combined = pl.concat(all_data, how="vertical")

# Analyze wage growth
wage_trends = (
    combined
    .group_by(["year", "cnae_code"])
    .agg([
        pl.col("salary").mean().alias("avg_salary"),
        pl.col("employee_id").count().alias("num_employees")
    ])
)

print(f"✓ Analyzed {len(combined):,} employment records")
```

### Step 3: CAGED Job Flow Analysis

```python
from pdet_data import CAGEDProcessor
import polars as pl

processor = CAGEDProcessor()

# Process multiple years
monthly_data = []
for year in [2023, 2024]:
    result = processor.process_year(year, force_refresh=False)
    monthly_data.append(pl.read_parquet(result.path))

combined = pl.concat(monthly_data, how="vertical")

# Annual job creation by state
annual_jobs = (
    combined
    .with_columns([
        pl.col("year_month").dt.year().alias("year")
    ])
    .group_by(["year", "state"])
    .agg([
        pl.col("admissions").sum().alias("total_hires"),
        pl.col("demissions").sum().alias("total_separations"),
        pl.col("net_flow").sum().alias("net_jobs")
    ])
)

print(annual_jobs.filter(pl.col("year") == 2024).sort("net_jobs", descending=True))
```

## Best Practices

### 1. Always Use Idempotent Processing

Skip expensive re-computation:

```python
# ❌ Never: Force reprocessing (60 seconds)
result = processor.process_year(2023, force_refresh=True)

# ✅ Always: Use cache if unchanged (0.08 seconds)
result = processor.process_year(2023, force_refresh=False)
```

### 2. Use Lazy Evaluation for Multi-Year Analysis

Defer execution until collection:

```python
# ❌ Eager: Loads all intermediate results
by_sector = df.group_by("cnae_code").agg(...)

# ✅ Lazy: Optimizes entire query before execution
by_sector = (
    df
    .lazy()
    .group_by(["year", "cnae_code"])
    .agg(...)
    .collect()
)
```

### 3. Concatenate First, Aggregate Second

Efficient multi-year processing:

```python
# ❌ Inefficient: Aggregate per year, then combine
results = []
for year in range(1994, 2024):
    agg = df_year.group_by("cnae_code").agg(...)  # 30 aggregations
    results.append(agg)

combined = pl.concat(results)

# ✅ Efficient: Concatenate once, aggregate once
all_data = []
for year in range(1994, 2024):
    df = pl.read_parquet(f"rais_{year}.parquet").with_columns(
        pl.lit(year).alias("year")
    )
    all_data.append(df)

combined = pl.concat(all_data, how="vertical")  # Single concatenation
by_sector = combined.group_by(["year", "cnae_code"]).agg(...)
```

### 4. Store Results in Parquet

Never use CSV for processed data:

```python
# ❌ Slow, large, untyped
result.write_csv("output.csv")  # 4 GB, 30s to read

# ✅ Fast, compact, typed
result.write_parquet("output.parquet")  # 0.4 GB, 0.5s to read
```

### 5. Handle Employment Spells Correctly

RAIS reports employment status on December 31 of each year:

```python
import polars as pl

# Track worker transitions
rais_2022 = pl.read_parquet("rais_2022.parquet")
rais_2023 = pl.read_parquet("rais_2023.parquet")

# Workers who changed sectors
transitions = (
    rais_2022
    .join(
        rais_2023.select(["employee_id", "cnae_code"]),
        on="employee_id",
        how="inner",
        suffix="_2023"
    )
    .filter(pl.col("cnae_code") != pl.col("cnae_code_2023"))
)

print(f"Sector transitions: {len(transitions):,}")
```

## Performance Benchmarks

| Operation | Time | Throughput |
|-----------|------|-----------|
| Process RAIS 2023 (first run) | 62s | 800k rows/sec |
| Process RAIS 2023 (cached) | 0.08s | — |
| Concatenate 30 years (100M rows) | 0.5s | 200M rows/sec |
| Aggregate all 100M rows | 4.2s | 23.8M rows/sec |
| CSV (10 GB) vs Parquet (0.4 GB) | — | 96% compression |

## Tools in This Section

### [pdet-data](pdet-data.md)
Industrial Big Data transformation engine for RAIS and CAGED:
- **Raw-to-Parquet conversion** (95%+ compression, typed schema)
- **Multithreaded Polars processing** (10x faster than Pandas)
- **Intelligent memory management** (minimal disk footprint)
- **Idempotent processing** (cache unchanged files)
- **Production-ready**: Daily pipelines, versioned outputs

### [Parquet + Polars Guide](guia-parquet.md)
Best practices for working with large labor datasets.

## Learn More

- **[pdet-data Documentation](pdet-data.md)** — Complete feature reference
- **[IBGE Employment Statistics](../ibge/index.md)** — Unemployment rates
- **[Architecture Overview](../architecture/overview.md)** — System design
- **[RAIS Official (Portuguese)](https://www.gov.br/trabalho/pt-br/acesso-a-informacao/dados-abertos/rais)** — Government source
- **[CAGED Official (Portuguese)](https://www.gov.br/trabalho/pt-br/acesso-a-informacao/dados-abertos/caged)** — Government source
