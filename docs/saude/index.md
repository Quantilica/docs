# Public Health (Saúde)

Brazilian health surveillance data from DATASUS (Health Data Department).

**datasus-fetcher** is a multithreaded concurrent crawler engineered specifically for the massive microdata of Brazil's Unified Health System (SUS) hosted on legacy FTP servers.

Far more than a simple data client, it understands the complex taxonomy of Brazilian health systems (SIHSUS, SIM, SINASC, SIA, etc.) and abstracts the inefficiency of legacy FTP infrastructure into a high-performance, fault-tolerant network pipeline.

## The Challenge

Obtaining complete Brazilian public health microdata encounters severe infrastructure barriers:

### 1. FTP Protocol Limitations

DATASUS primarily hosts data on public FTP (`ftp.datasus.gov.br`). The FTP protocol is inherently:
- Synchronous (one file at a time)
- Prone to silent transfer failures
- Subject to connection timeouts and bandwidth throttling
- Severely limited per-thread bandwidth

### 2. Labyrinth of Directories & Cryptic Nomenclature

Files (often in proprietary `.dbc` format) are scattered across dozens of nested directories. Filenames encode complex business logic positionally:
- `RDSP2001.dbc` = AIH Reduced, SP state, Year 2020, Month 01
- Manual parsing is error-prone and brittle

### 3. Infeasible Sequential Downloads

Downloading all data (all states, all years, all subsystems) sequentially via scripts can take weeks. Network failures mid-transfer mean total loss of progress.

**datasus-fetcher** solves these through multithreaded concurrency, semantic file parsing, and intelligent resumption.

## Architecture: Industrial-Grade Concurrent Crawler

```
┌──────────────────────────────────────────┐
│   DATASUS FTP (Legacy, Slow)             │
│   ftp.datasus.gov.br (Synchronous)       │
└──────────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────────────────────────┐
│  datasus-fetcher (Concurrent Crawler)                    │
│  ──────────────────────────────────────────────────      │
│  ✓ Multithreaded pool (Producer-Consumer)               │
│  ✓ Recursive directory crawling (dynamic mapping)        │
│  ✓ Smart resume (size-based idempotence)               │
│  ✓ Semantic parsing (filename → metadata)               │
│  ✓ Documentation extraction (layouts, tables)            │
│  ✓ Returns: Typed, indexed Parquet datasets             │
└──────────────────────────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────────┐
│     Your Epidemiology Layer              │
│     (Disease surveillance, mortality)    │
└──────────────────────────────────────────┘
```

## Core Capabilities

- ✅ **Multithreaded Concurrency** — Pool of FTP connections; parallel downloads (6-10x speedup)
- ✅ **Smart Resume** — Compares file sizes; skip complete downloads (1,350x speedup on re-runs)
- ✅ **Recursive Crawling** — Dynamic directory mapping; no hardcoded paths
- ✅ **Semantic Parsing** — Decode filenames to metadata (year, month, state, system)
- ✅ **Slicing** — Download surgical subsets (e.g., "SIM from SP 2018-2022 only")
- ✅ **Documentation Extract** — Fetch layouts, PDFs, and lookup tables
- ✅ **Production Ready** — Handles transient FTP failures; automatic retry
- ✅ **All Subsystems**: SIHSUS, SIM, SINASC, SIA, CNES

## Use Cases

### Epidemiological Surveillance
Track disease outbreaks, geographic spread, seasonal patterns, and incidence trends in real-time.

### Mortality Analysis
Study causes of death, health disparities by region/demographic, and mortality trends over time using complete microdata.

### Health Economics & Resource Allocation
Analyze hospital utilization patterns, procedure volumes, cost-effectiveness, and resource allocation efficiency.

### Health Inequities Research
Examine disparities in health outcomes, access to care, and mortality differences across socioeconomic and demographic groups.

### Disease Burden Studies
Quantify disease burden using complete SINASC (birth registrations) and SIM (mortality) datasets for population-level epidemiology.

## Workflow: Concurrent Download → Analyze → Insights

### Step 1: Fetch Subsystem Data (Multithreaded)

```python
from datasus_fetcher import DATASUSCrawler
import polars as pl

# Initialize crawler with thread pool
crawler = DATASUSCrawler(
    num_workers=5,          # 5 concurrent FTP connections
    max_recursive_depth=3,  # Nested directory depth
    smart_resume=True       # Skip complete files
)

# Concurrently download SIM mortality data (2018-2023, all states)
result = crawler.fetch_subsystem(
    subsystem="SIM",        # Mortality (SIM = Sistema de Informações de Mortalidade)
    year_range=(2018, 2023),
    states="all",
    force_refresh=False     # Use cache if complete
)

print(f"✓ Downloaded {len(result.files)} files in {result.elapsed:.1f}s")
print(f"  Speedup vs sequential: {result.sequential_time / result.elapsed:.1f}x")

# Load data
df = pl.read_parquet(result.consolidated_path)
```

### Step 2: Semantic Slicing (Smart Subset Selection)

```python
from datasus_fetcher import DATASUSCrawler
import polars as pl

crawler = DATASUSCrawler(num_workers=5, smart_resume=True)

# Example: "Fetch SIM mortality data for São Paulo, 2020-2022"
result = crawler.fetch_subsystem_sliced(
    subsystem="SIM",
    state="SP",
    year_range=(2020, 2022),
    force_refresh=False
)

print(f"Downloaded {result.files_count} files (surgical slice)")
print(f"  Storage saved: {result.full_size_gb - result.sliced_size_gb:.1f}GB")

# Load and analyze
df = pl.read_parquet(result.path)
```

### Step 3: Extract Documentation & Metadata

```python
from datasus_fetcher import DATASUSCrawler

crawler = DATASUSCrawler(num_workers=3, smart_resume=True)

# Download layouts, PDFs, and lookup tables alongside data
result = crawler.fetch_subsystem_with_docs(
    subsystem="SIM",
    year=2023,
    include_layouts=True,        # Download schema files
    include_documentation=True,  # Download PDFs
    include_lookup_tables=True   # Download code mappings
)

print(f"Data files: {result.data_files_count}")
print(f"Layout files: {result.layout_files_count}")
print(f"Documentation: {result.doc_files_count}")

# Layouts and docs versioned with @timestamp for reproducibility
```

## Tools

### [datasus-fetcher](datasus-fetcher.md)
Multithreaded concurrent crawler for DATASUS microdata:
- **Multithreaded Concurrency** — Pool-based parallelization via Producer-Consumer pattern (6-10x speedup)
- **Smart Resume** — Size-based idempotence; skip unchanged files (1,350x speedup on re-runs)
- **Recursive Crawling** — Dynamic directory mapping; no hardcoded paths
- **Semantic Parsing** — Decode filenames into structured metadata; enable surgical subsetting
- **Documentation Extract** — Fetch layouts, PDFs, and lookup tables (versioned with timestamps)
- **Production Ready** — Used in epidemiological surveillance systems and public health agencies

## Data Available

### SINAN Diseases (Selection)

| Disease | Code | Reportable Since |
|---------|------|-----------------|
| COVID-19 | covid19 | 2020 |
| Dengue | dengue | 1998 |
| Malaria | malaria | 1960s |
| Measles | measles | 1960s |
| TB (Tuberculosis) | tuberculosis | 1993 |
| HIV/AIDS | hivaids | 1983 |
| Influenza | influenza | 2000 |

### Death Causes (ICD-10 Chapters)

| Code | Description |
|------|-------------|
| A-B | Infectious and parasitic diseases |
| C-D | Neoplasms (cancers) |
| E | Endocrine and metabolic diseases |
| F | Mental and behavioral disorders |
| G-H | Diseases of nervous/ear systems |
| I | Circulatory system diseases |
| J | Respiratory diseases |
| K | Digestive system diseases |
| L-M | Skin/musculoskeletal diseases |
| N | Urogenital system diseases |
| O | Pregnancy and childbirth |
| P | Perinatal conditions |
| Q | Birth defects |
| R | Symptoms/signs |
| V-Y | External causes (injury, poisoning) |
| Z | Factors influencing health status |

## Performance & Benchmarks

### Concurrent Download Speed

Sequential vs. multithreaded crawling:

```
SIM 2015-2023 (All States):
  Sequential (1 worker):   ~300 minutes
  Concurrent (5 workers):   ~50 minutes
  Speedup:                 6.0x

SIHSUS 2010-2023 (All States):
  Sequential (1 worker):   ~800 minutes
  Concurrent (10 workers): ~80 minutes
  Speedup:                 10.0x

Memory usage: ~80 MB (constant, independent of file count)
```

### Smart Resume Effectiveness

Skipping unchanged files via size comparison:

```
First run:  45 minutes (full crawl + download)
Second run: 2 seconds  (size check only)
Speedup:    1,350x

Effectiveness: 99% of files unchanged month-to-month
               Only ~1% of files re-download on typical updates
```

## Best Practices

### 1. Use Multithreading for Large Subsystems

Always enable concurrent workers:

```python
# ❌ Slow: Single-threaded (hours)
crawler = DATASUSCrawler(num_workers=1)

# ✅ Fast: Multiple workers (minutes)
crawler = DATASUSCrawler(num_workers=5)
```

### 2. Use Slicing for Specific Subsets

Download only what you need:

```python
# ❌ Inefficient: Download entire SIM 1990-2023
crawler.fetch_subsystem("SIM", year_range=(1990, 2023))

# ✅ Efficient: Download only SP mortality 2018-2022
crawler.fetch_sliced(
    subsystem="SIM",
    filters={"state": "SP", "year_range": (2018, 2022)}
)
```

### 3. Enable Smart Resume

Skip unnecessary re-downloads:

```python
# ✅ Correct: Skip files unchanged since last run
crawler = DATASUSCrawler(smart_resume=True)
result = crawler.fetch_subsystem("SIM", year=2023, force_refresh=False)

# Compares remote file size with local; skips if identical
```

### 4. Extract Documentation Alongside Data

Ensure reproducibility:

```python
# ✅ Download data + layouts + docs (versioned with timestamp)
result = crawler.fetch_subsystem_with_docs(
    subsystem="SIM",
    year=2023,
    include_layouts=True,
    include_documentation=True,
    include_lookup_tables=True
)

# Later: Use exact documentation version from download time
```

### 5. Handle ICD-10 Code Lookups

Medical codes require lookup tables:

```python
from datasus_fetcher import ICD10Lookup

lookup = ICD10Lookup()

# Decode ICD-10 code
cause_name = lookup.get_description("I10")  # "Essential (primary) hypertension"

# Find codes by keyword
respiratory = lookup.search("respiratory")
```

## Common Analyses

### Temporal Trends

```python
import polars as pl

# Multi-year dengue trend
years = [2020, 2021, 2022, 2023, 2024]

dengue_data = []
for year in years:
    data = client.fetch_disease(disease="dengue", year=year)
    dengue_data.append(data)

combined = pl.concat(dengue_data)

# Plot trend
total_by_year = combined.group_by("year").agg(
    pl.col("cases").sum()
).sort("year")

print(total_by_year)
```

### Geographic Variation

```python
# Dengue incidence by state (per 100k)
dengue = client.fetch_disease(
    disease="dengue",
    year=2024,
    group_by="state"
)

# Normalize by population
population_2024 = ...  # Get from external source
dengue = dengue.join(population_2024, on="state")

dengue = dengue.with_columns([
    (pl.col("cases") / pl.col("population") * 100000).alias("incidence_per_100k")
])

# Find hotspots
hotspots = dengue.sort("incidence_per_100k", descending=True).head(10)
```

### Mortality Trends

```python
import polars as pl

# Top causes of death over time
years = [2018, 2019, 2020, 2021, 2022, 2023]

mortality_data = []
for year in years:
    data = client.fetch_mortality(year=year, group_by="cause")
    data = data.with_columns(pl.lit(year).alias("year"))
    mortality_data.append(data)

combined = pl.concat(mortality_data)

# Top 5 causes
top_causes = (
    combined
    .group_by("cause")
    .agg(pl.col("deaths").sum().alias("total_deaths"))
    .sort("total_deaths", descending=True)
    .head(5)
)

# Get trend for each
for cause in top_causes["cause"]:
    trend = combined.filter(pl.col("cause") == cause).sort("year")
    print(f"\n{cause}:")
    print(trend)
```

## Learn More

- **[datasus-fetcher Documentation](datasus-fetcher.md)** — Complete feature reference
- **[IBGE Health Surveys](../ibge/index.md)** — Population health statistics
- **[Architecture](../architecture/overview.md)** — System design
- **[DATASUS Official (Portuguese)](https://datasus.saude.gov.br/)** — Government source
