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
# ✅ Idempotent: Check Last-Modified before downloading
downloader = SiscomexDownloader(verify_ssl=False)
result = downloader.download_exports(2023, force_refresh=False)
# HEAD request checks Last-Modified
# Downloads only if remote file is newer than local file
# Speedup: 45s first run → 0.8s cached run (57x faster)

# ❌ Not idempotent: Always re-download
result = downloader.download_exports(2023, force_refresh=True)
# Wastes bandwidth and time
```

### Pattern: Smart Resume

```python
# ✅ Resume interrupted downloads
crawler = DATASUSCrawler(
    num_workers=5,
    smart_resume=True  # Enable size-based idempotence
)

# First attempt: interrupted at 70%
result = crawler.fetch_subsystem("SIM", year=2023, force_refresh=True)
# Downloads 70%, then connection drops

# Second attempt: automatically resumes
result = crawler.fetch_subsystem("SIM", year=2023, force_refresh=False)
# Compares remote file size with local file
# Skips complete files, downloads only remaining 30%
```

### Pattern: Modification Time Hashing

```python
# ✅ Skip re-processing unchanged input files
processor = RAISProcessor()

# First run: processes RAIS_2023.zip (62 seconds)
result = processor.process_year(2023, force_refresh=False)

# Second run: checks modification time of input file
# If unchanged, skips processing entirely (0.08 seconds)
result = processor.process_year(2023, force_refresh=False)
# 778x speedup on re-runs
```

### Pattern: Application-Level Caching

```python
import hashlib
import json

# Store metadata about downloaded files
def cache_key(subsystem, year, state):
    return f"{subsystem}_{year}_{state}"

def is_cached(subsystem, year, state):
    cache_file = f"cache/{cache_key(subsystem, year, state)}.json"
    if not os.path.exists(cache_file):
        return False
    
    with open(cache_file) as f:
        cached = json.load(f)
    
    # Check if remote file has changed
    remote_size = get_remote_file_size(subsystem, year, state)
    return cached["file_size"] == remote_size

# Use cache to skip unnecessary downloads
if not is_cached("SIM", 2023, "SP"):
    result = crawler.fetch_sliced(
        subsystem="SIM",
        state="SP",
        year=2023
    )
    # Update cache with file metadata
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

async def fetch_multiple_tables():
    client = AsyncSidraClient()
    
    # ✅ Concurrent: fetch 3 tables simultaneously
    results = await asyncio.gather(
        client.fetch(table="1620", variable=116),  # GDP
        client.fetch(table="1419", variable=11),   # Inflation
        client.fetch(table="6381", variable=4099)  # Unemployment
    )
    
    return results

# Sequential: ~60 seconds
# Concurrent: ~15 seconds (4x faster)
results = asyncio.run(fetch_multiple_tables())
```

### Pattern: Multithreaded FTP Crawling

```python
from datasus_fetcher import DATASUSCrawler

# ✅ Multithreaded: 5 concurrent FTP connections
crawler = DATASUSCrawler(
    num_workers=5,
    max_recursive_depth=3,
    smart_resume=True
)

result = crawler.fetch_subsystem(
    subsystem="SIM",
    year_range=(2018, 2023),
    states="all"
)

# Sequential: 300 minutes
# Concurrent (5 workers): 50 minutes (6x faster)
```

### Pattern: Concurrent Multi-Year Downloads

```python
from comexdown import SiscomexDownloader
import concurrent.futures

downloader = SiscomexDownloader(verify_ssl=False)

# ✅ Download 10 years concurrently
def download_year(year):
    return downloader.download_exports(year, force_refresh=False)

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    results = executor.map(download_year, range(2014, 2024))
    results = list(results)

# Sequential: 10 years × 45s = 450 seconds
# Concurrent (5 workers): ~90 seconds (5x faster)
```

### Anti-Pattern: Nested Concurrency

```python
# ❌ WRONG: Concurrent fetches inside concurrent downloads
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    def download_and_fetch(year):
        export_data = downloader.download_exports(year)
        
        # Starting 3 more concurrent operations inside
        results = asyncio.run(fetch_economic_indicators())
        
        return export_data, results
    
    # This creates 5 × N threads, causing excessive context switching

# ✅ RIGHT: Keep concurrency at one level
# Either concurrent downloads OR concurrent API fetches, not both
```

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

### Pattern: Automatic Tool Output

```python
import polars as pl

# Most tools already output Parquet
processor = RAISProcessor()
result = processor.process_year(2023)
# Automatically saves as RAIS_2023.parquet

# Never convert back to CSV for analysis
df = pl.read_parquet(result.path)  # Efficient reading

# Even if you export results, keep intermediate data in Parquet
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

### Pattern: Configure Retries

```python
from datasus_fetcher import DATASUSCrawler

# ✅ Production-ready: Configure retries
crawler = DATASUSCrawler(
    num_workers=5,
    timeout=60,         # 60-second timeout per request
    max_retries=5,      # Retry up to 5 times on failure
    backoff_factor=2    # Exponential backoff: 1s, 2s, 4s, 8s, 16s
)

result = crawler.fetch_subsystem("SIM", year=2023)
# Transient failures are handled automatically
# Retries use exponential backoff: waits before retrying

# ❌ Not production-ready: No retry configuration
crawler = DATASUSCrawler(num_workers=1)
# Fails on first transient error; no automatic retry
```

### Pattern: Wrapping Retries in Your Code

```python
import time
from datetime import datetime

def fetch_with_retry(func, max_retries=3, backoff_factor=2):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to call
        max_retries: Maximum number of retries
        backoff_factor: Multiplier for backoff delay
    
    Returns:
        Result of successful function call
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            
            if attempt < max_retries - 1:
                delay = backoff_factor ** attempt
                print(f"Attempt {attempt + 1} failed: {e}")
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"All {max_retries} attempts failed")
    
    raise last_exception

# Use it
def fetch_data():
    crawler = DATASUSCrawler(num_workers=5)
    return crawler.fetch_subsystem("SIM", year=2023)

result = fetch_with_retry(fetch_data, max_retries=5, backoff_factor=2)
```

## 6. Validate Data at the Source

**Definition**: Validate data immediately after fetching, before expensive transformations. Catch data quality issues early.

### Why It Matters

- **Fail fast**: Detect data problems before wasting time on analysis
- **Better error messages**: Know exactly which source file is corrupt
- **Prevent garbage in, garbage out**: Invalid data doesn't contaminate your analysis

### Pattern: Size-Based Validation

```python
# ✅ Validate file size to detect truncation
def validate_downloaded_file(expected_size_bytes, actual_path):
    actual_size = os.path.getsize(actual_path)
    
    if actual_size < expected_size_bytes * 0.95:
        # Downloaded file is less than 95% of expected size
        # Probably truncated due to connection drop
        raise ValueError(
            f"Downloaded file appears truncated:\n"
            f"  Expected: {expected_size_bytes} bytes\n"
            f"  Actual: {actual_size} bytes\n"
            f"  Please retry download"
        )
    
    return True

# After downloading
result = crawler.fetch_subsystem("SIM", year=2023)
validate_downloaded_file(expected_size=1000000000, actual_path=result.path)
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
# ✅ Streaming download (8KB chunks): constant memory overhead
from comexdown import SiscomexDownloader

downloader = SiscomexDownloader(verify_ssl=False)
result = downloader.download_exports(2023)
# Streams in 8KB chunks regardless of file size
# Memory usage: ~8 MB (constant)
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
import polars as pl
import json
from datetime import datetime

# ✅ Save metadata alongside data
processor = RAISProcessor()
result = processor.process_year(2023, force_refresh=False)

metadata = {
    "source": "RAIS 2023",
    "download_timestamp": datetime.now().isoformat(),
    "fetch_method": "pdet_data.RAISProcessor",
    "row_count": len(pl.read_parquet(result.path)),
    "columns": pl.read_parquet(result.path).columns,
    "transformations": [
        "Converted to Parquet",
        "Removed invalid salary values (salary <= 0)",
        "Deduplicated records by employee_id"
    ]
}

with open("rais_2023_metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)
```

### Pattern: Documentation Extraction

```python
# ✅ Download documentation alongside data
crawler = DATASUSCrawler(num_workers=3, smart_resume=True)

result = crawler.fetch_subsystem_with_docs(
    subsystem="SIM",
    year=2023,
    include_layouts=True,        # Schema files
    include_documentation=True,  # PDFs
    include_lookup_tables=True   # Code mappings
)

# Now you have:
# - SIM_2023.parquet (data)
# - SIM_2023_layout_@2024-04-10T14:32:15Z.pdf (schema)
# - SIM_2023_docs_@2024-04-10T14:32:15Z.pdf (documentation)
# - SIM_2023_codebook_@2024-04-10T14:32:15Z.csv (ICD-10 codes)

# Later, readers know exactly which layout/docs apply to this dataset
```

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
