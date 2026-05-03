# Best Practices

This guide covers practical patterns used across all tools in the Brazilian Public Data Suite. Following these patterns will make your data pipelines faster, more reliable, and easier to maintain.

## 1. Always Use Idempotent Processing

**Definition**: Idempotent operations produce the same result whether run once or multiple times. They check before downloading/processing, skip unchanged work, and resume interrupted tasks.

### Why It Matters

- **Saves bandwidth**: Don't re-download unchanged datasets
- **Saves time**: 57x speedup on cached runs (comexdown)
- **Fault tolerance**: Resume mid-transfer instead of starting over
- **Safe to retry**: Running twice produces same result as running once

### Pattern: Check Before Downloading

```python
# ✅ Idempotent: comexdown HEAD-checks Last-Modified before every GET
from pathlib import Path
import comexdown

comexdown.get_year(Path("./DATA"), year=2023)
# First run: streams the CSV in 8 KiB chunks
# Re-runs: HEAD shows Last-Modified == local mtime, GET is skipped entirely
```

There is no `force_refresh` flag — to re-fetch, delete the local file first.

### Pattern: Smart Resume

```sh
# ✅ datasus-fetcher always compares remote vs. local size and skips matches
# First attempt: interrupted partway
datasus-fetcher data --data-dir ./data sim-do-cid10 \
    --start 2023 --end 2023 --threads 5

# Second attempt: re-run the same command
# Already-complete files are skipped, only missing/mismatched ones re-download
datasus-fetcher data --data-dir ./data sim-do-cid10 \
    --start 2023 --end 2023 --threads 5
```

### Pattern: Skip Already-Downloaded Archives

```python
# ✅ pdet-data fetchers check if dest_filepath already exists and skip it.
# Re-running `pdet-data fetch ./raw` only downloads new RAIS / CAGED archives.
from pathlib import Path
from pdet_data import connect, fetch_rais

ftp = connect()
try:
    fetch_rais(ftp=ftp, dest_dir=Path("./raw"))  # idempotent
finally:
    ftp.close()
```

### Pattern: Dry-Run Before Bulk Downloads

```sh
# ✅ Preview what `datasus-fetcher` would download before committing
datasus-fetcher data --data-dir ./data sim-do-cid10 \
    --start 2018 --end 2023 --regions sp \
    --dry-run
# Prints filenames + sizes + grand total, no bytes transferred
```

## 2. Use Concurrency for I/O-Bound Operations

**Definition**: Concurrency means doing multiple I/O operations (network requests, file downloads) simultaneously rather than sequentially.

### Why It Matters

- **Network I/O is slow**: A single request might take 1 second. While waiting for one response, you could start 5 others.
- **Massive speedup**: 4-10x faster than sequential approaches
- **Free speedup**: Doesn't require faster hardware; just better resource utilization

### Pattern: Async/Await for REST APIs

```python
import asyncio
from sidra_fetcher import AsyncSidraClient

async def fetch_multiple_metadata():
    async with AsyncSidraClient(timeout=60) as client:
        # ✅ Concurrent: fetch metadata for 3 aggregates simultaneously
        return await asyncio.gather(
            client.get_agregado(1620),  # GDP
            client.get_agregado(1419),  # IPCA inflation
            client.get_agregado(6381),  # Unemployment (PNADC)
        )

# Sequential: ~6 seconds
# Concurrent: ~2 seconds (3x faster)
agregados = asyncio.run(fetch_multiple_metadata())
```

### Pattern: Multithreaded FTP Crawling

```sh
# ✅ Multithreaded: 5 concurrent FTP fetchers
datasus-fetcher data --data-dir ./data sim-do-cid10 \
    --start 2018 --end 2023 \
    --threads 5

# Sequential (--threads 1): 300 minutes
# Concurrent (--threads 5):   50 minutes (~6x faster)
```

Equivalent Python entrypoint:

```python
from pathlib import Path
from datasus_fetcher import fetcher
from datasus_fetcher.slicer import Slicer

fetcher.download_data(
    datasets=["sim-do-cid10"],
    destdir=Path("./data"),
    threads=5,
    slicer=Slicer(start_time="2018", end_time="2023", regions=None),
)
```

### Pattern: Multi-Year Batches with Idempotent Re-runs

`comexdown` is sequential by design — it leans on temporal idempotency instead of parallelism. Pass a year range and let the HEAD/`Last-Modified` check make re-runs cheap:

```bash
# First run downloads everything; later runs only fetch what changed.
comexdown trade 2014:2023 -o ./DATA
```

```python
from pathlib import Path
import comexdown

for year in range(2014, 2024):
    comexdown.get_year(Path("./DATA"), year=year)  # HEAD-cached
```

If you genuinely want to overlap unrelated work (e.g. a SECEX download
alongside a SIDRA fetch), do it at the orchestration layer with `asyncio` or
`concurrent.futures` — but keep concurrency at a single level to avoid thread
explosion.

## 3. Store Results in Parquet, Not CSV

**Definition**: Parquet is a columnar storage format optimized for analytics. CSV is a row-based text format from the 1970s.

### Why It Matters

- **95%+ smaller**: 8 GB CSV → 0.4 GB Parquet
- **100x faster to read**: Columnar format lets you skip irrelevant data
- **Typed**: No guessing whether a column is string or number
- **Compressed**: Built-in compression; no separate gzip files needed

### Pattern: Convert CSV to Parquet

```python
import polars as pl

# ❌ Slow and large
df = pl.read_csv("large_file.csv")  # 8 GB, 30 seconds to read
df.write_csv("output.csv")          # 4 GB, 60 seconds to write

# ✅ Fast and small
df = pl.read_csv("large_file.csv")
df.write_parquet("output.parquet")  # 0.4 GB, 2 seconds to write
df = pl.read_parquet("output.parquet")  # 0.5 seconds to read
```

### Pattern: Parquet with Columns Selection

```python
import polars as pl

# Read only columns you need (100x faster than CSV)
df = pl.read_parquet(
    "large_file.parquet",
    columns=["year", "state", "salary", "employee_id"]
)

# CSV forces you to read entire file, even if you need 2 columns
df = pl.read_csv("large_file.csv")  # Must read all 50 columns
```

### Pattern: Bulk Convert to Parquet

```bash
# pdet-data ships convert_rais / convert_caged behind a CLI subcommand.
# It decompresses each .7z, parses with the per-year schema, and writes Parquet.
pdet-data convert ./raw ./parquet
```

```python
import polars as pl

# Read once, then keep everything in Parquet for analysis
df = pl.read_parquet("parquet/rais-vinculos/2023.parquet")
# CSV is only for sharing with non-technical stakeholders
```

## 4. Use Lazy Evaluation for Multi-Year Analysis

**Definition**: Lazy evaluation defers computation until explicitly requested. Lets the query optimizer simplify your operations before executing them.

### Why It Matters

- **Optimization**: Query optimizer combines multiple operations into single pass
- **Memory efficiency**: Process 100M rows without loading all into RAM
- **Faster execution**: Unnecessary work is eliminated automatically

### Pattern: Lazy Group-By Aggregation

```python
import polars as pl

# ❌ Eager: Loads all data into memory, then aggregates
df = pl.read_parquet("rais_2023.parquet")
result = df.group_by("state").agg(pl.col("salary").mean())
# High memory usage; multiple passes over data

# ✅ Lazy: Defers execution; optimizer combines operations
df = pl.read_parquet("rais_2023.parquet")
result = (
    df
    .lazy()  # Defer execution
    .filter(pl.col("salary") > 0)  # Optional: filter first
    .group_by("state")
    .agg(pl.col("salary").mean())
    .collect()  # Execute now
)
# Low memory usage; single optimized pass
```

### Pattern: Multi-Year Concatenation

```python
import polars as pl

# ❌ Inefficient: Aggregate per year, then combine
years_data = []
for year in range(2010, 2024):
    df = pl.read_parquet(f"rais_{year}.parquet")
    agg = df.group_by("sector").agg(pl.col("salary").mean())  # 14 aggregations
    years_data.append(agg)

combined = pl.concat(years_data)

# ✅ Efficient: Concatenate first, aggregate once
years_data = []
for year in range(2010, 2024):
    df = pl.read_parquet(f"rais_{year}.parquet").with_columns(
        pl.lit(year).alias("year")
    )
    years_data.append(df)

combined = pl.concat(years_data, how="vertical")  # Single concat
by_sector = (
    combined
    .lazy()
    .group_by(["year", "sector"])
    .agg(pl.col("salary").mean())
    .collect()
)
```

## 5. Handle Errors Gracefully with Auto-Retry

**Definition**: Auto-retry means automatically retrying failed operations with exponential backoff. Don't fail on transient errors.

### Why It Matters

- **Network is unreliable**: Timeouts, dropped connections, temporary unavailability are normal
- **Exponential backoff**: Prevents overwhelming the server with retry storms
- **Transparent**: You don't need to manually implement retry logic

### Pattern: Built-in Retries

`datasus-fetcher` retries each FTP transfer up to 3 times on transient errors before giving up on that file — other threads keep going. To make a long-running batch survive intermittent failures, just re-run the command; the size-based idempotence check picks up where it left off.

```sh
datasus-fetcher data --data-dir ./data sim-do-cid10 \
    --start 2023 --end 2023 --threads 5
```

### Pattern: Wrapping Retries in Your Code

```python
import time

def with_retry(func, max_retries=3, backoff_factor=2):
    """Retry a function with exponential backoff."""
    last_exception = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = backoff_factor ** attempt
                print(f"Attempt {attempt + 1} failed: {e}; retrying in {delay}s")
                time.sleep(delay)
    raise last_exception

# Example: wrap a SIDRA call (datasus-fetcher already retries internally)
from sidra_fetcher import SidraClient
client = SidraClient()
result = with_retry(lambda: client.get_agregado(1620), max_retries=5)
```

## 6. Validate Data at the Source

**Definition**: Validate data immediately after fetching, before expensive transformations. Catch data quality issues early.

### Why It Matters

- **Fail fast**: Detect data problems before wasting time on analysis
- **Better error messages**: Know exactly which source file is corrupt
- **Prevent garbage in, garbage out**: Invalid data doesn't contaminate your analysis

### Pattern: Size-Based Validation

```python
import os
from pathlib import Path

# ✅ Validate file size to detect truncation
def validate_downloaded_file(expected_size_bytes: int, path: Path) -> None:
    actual = path.stat().st_size
    if actual < expected_size_bytes * 0.95:
        raise ValueError(
            f"Downloaded file appears truncated:\n"
            f"  Expected: {expected_size_bytes} bytes\n"
            f"  Actual:   {actual} bytes"
        )

# datasus-fetcher already does this for you on every run — re-run to heal a
# truncated download. For your own pipelines, apply the same pattern after fetch.
```

### Pattern: Schema Validation

```python
import polars as pl

# ✅ Validate schema after reading
def validate_rais_schema(df):
    required_columns = {
        "year": pl.Int32,
        "employee_id": pl.Utf8,
        "salary": pl.Float64,
        "state": pl.Utf8,
    }
    
    for col_name, col_type in required_columns.items():
        if col_name not in df.columns:
            raise ValueError(f"Missing column: {col_name}")
        
        if df.schema[col_name] != col_type:
            raise ValueError(
                f"Wrong type for {col_name}: "
                f"expected {col_type}, got {df.schema[col_name]}"
            )
    
    return True

df = pl.read_parquet("rais_2023.parquet")
validate_rais_schema(df)
```

### Pattern: Row Count Validation

```python
import polars as pl

# ✅ Validate row count is reasonable
def validate_rais_row_count(df, year):
    expected_min = 50_000_000  # Should have at least 50M employment records
    expected_max = 80_000_000  # Should have less than 80M
    
    row_count = len(df)
    
    if row_count < expected_min or row_count > expected_max:
        raise ValueError(
            f"Unusual row count for RAIS {year}:\n"
            f"  Expected: {expected_min:,} - {expected_max:,}\n"
            f"  Actual: {row_count:,}\n"
            f"  Please verify data integrity"
        )
    
    return True

df = pl.read_parquet("rais_2023.parquet")
validate_rais_row_count(df, year=2023)
```

## 7. Memory Management for Large Files

**Definition**: Process large files without loading them entirely into RAM. Use streaming/chunking or lazy evaluation.

### Why It Matters

- **RAIS is 50M+ rows**: Can't fit in Pandas on typical machines
- **Siscomex is gigabytes**: Naive approach causes OOM crashes
- **Streaming is free**: No performance penalty for streaming; often faster

### Pattern: Streaming Chunks

```python
# ✅ comexdown streams every download in 8 KiB chunks via urllib —
#    constant memory regardless of file size, atomic *.tmp -> rename on success.
from pathlib import Path
import comexdown

comexdown.get_year(Path("./DATA"), year=2023)
```

### Pattern: Lazy Polars Processing

```python
import polars as pl

# ❌ Eager: Loads entire 8GB file into RAM
df = pl.read_parquet("rais_2023.parquet")  # OOM on low-memory machines
result = df.group_by("state").agg(pl.col("salary").mean())

# ✅ Lazy: Processes in streaming fashion
result = (
    pl.read_parquet("rais_2023.parquet")
    .lazy()
    .group_by("state")
    .agg(pl.col("salary").mean())
    .collect()  # Stream execution; low memory usage
)
```

### Pattern: Chunked CSV Processing

```python
import polars as pl

# ✅ Process CSV in chunks
chunk_size = 1_000_000  # Process 1M rows at a time

all_results = []
for chunk in pl.read_csv_batched("large_file.csv", batch_size=chunk_size):
    # Process chunk
    result = chunk.group_by("state").agg(pl.col("salary").mean())
    all_results.append(result)

combined = pl.concat(all_results)
```

## 8. Documentation & Reproducibility

**Definition**: Document your data: where it comes from, when it was fetched, how it was transformed, and how to reproduce it.

### Why It Matters

- **Audit trail**: Know exactly what data is in your analysis
- **Reproducibility**: Others can verify your results
- **Debugging**: When something breaks, you know what changed

### Pattern: Store Metadata with Parquet

```python
import json
import polars as pl
from datetime import datetime
from pathlib import Path

# ✅ Save metadata alongside data
parquet_path = Path("parquet/rais-vinculos/2023.parquet")
df = pl.read_parquet(parquet_path)

metadata = {
    "source": "RAIS 2023 (vinculos)",
    "download_timestamp": datetime.now().isoformat(),
    "fetch_method": "pdet_data.convert_rais",
    "row_count": df.height,
    "columns": df.columns,
    "transformations": [
        "Decompressed via 7z",
        "Parsed CSV with per-year schema (pdet_data.reader.read_rais)",
        "Cast INTEGER_COLUMNS / NUMERIC_COLUMNS / BOOLEAN_COLUMNS",
        "Wrote Parquet via polars.DataFrame.write_parquet",
    ],
}

parquet_path.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2))
```

### Pattern: Documentation Extraction

```sh
# ✅ Download data + codebooks + auxiliary tables together
datasus-fetcher data --data-dir ./data sim-do-cid10 --start 2023 --end 2023
datasus-fetcher docs --data-dir ./docs sim
datasus-fetcher aux  --data-dir ./aux  sim
```

`.dbc` filenames already encode `dataset_uf_period_YYYYMMDD`, so multiple DATASUS revisions of the same period coexist on disk. Use `datasus-fetcher archive --archive-data-dir ./archive` to rotate non-latest versions out of the active tree without losing them.

### Pattern: Transformation Log

```python
import logging

# ✅ Log every transformation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Processing
df = pl.read_parquet("rais_2023.parquet")
initial_count = len(df)

logger.info(f"Loaded RAIS 2023: {initial_count:,} rows")

# Filter
df = df.filter(pl.col("salary") > 0)
logger.info(f"Filtered to {len(df):,} rows with salary > 0 "
            f"(removed {initial_count - len(df):,} invalid records)")

# Group
result = df.group_by("state").agg(pl.col("salary").mean())
logger.info(f"Aggregated by state: {len(result)} states")

# Save
result.write_parquet("output.parquet")
logger.info("Saved results to output.parquet")
```

## Summary Checklist

When building data pipelines with the Brazilian Public Data Suite:

- [ ] **Idempotent**: Check before downloading/processing (force_refresh=False)
- [ ] **Concurrent**: Use async/multithreaded operations for I/O (num_workers, AsyncClient)
- [ ] **Parquet**: Store results in Parquet, not CSV
- [ ] **Lazy**: Use lazy evaluation for large datasets (pl.lazy().collect())
- [ ] **Retry**: Configure auto-retry with exponential backoff
- [ ] **Validate**: Check data quality immediately after fetching
- [ ] **Memory**: Stream or chunk for large files; use lazy evaluation
- [ ] **Document**: Log transformations; store metadata with results; extract docs

Following these patterns makes your pipelines fast, reliable, and maintainable.
