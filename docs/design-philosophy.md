# Design Philosophy

The Brazilian Public Data Suite is built on five core principles that guide every tool, from sidra-fetcher to datasus-fetcher. Understanding these principles helps you use the tools effectively and extend them for your own needs.

## 1. Modularity

Each tool is **independent and self-contained**. You can use only what you need without pulling in unnecessary dependencies or coupling.

### Why It Matters

Brazilian government data sources are diverse and fragmented. Forcing a single unified API would sacrifice the specialized optimizations each tool needs.

- **sidra-fetcher** is optimized for IBGE REST APIs with async concurrency
- **pdet-data** is optimized for massive CSV files with Polars vectorial processing
- **datasus-fetcher** is optimized for legacy FTP infrastructure with multithreaded crawling

Each tool solves its specific infrastructure challenge. Mixing them into a monolithic "mega-fetcher" would weaken all of them.

### How We Apply It

- No shared internal dependencies between tools
- Each tool has its own retry logic, error handling, and caching strategy
- Tools are composable: combine sidra-fetcher + tddata + pdet-data in a single pipeline without conflicts

### Example: Using Multiple Tools

```python
import asyncio
from sidra_fetcher import AsyncSidraClient
from pdet_data import RAISProcessor
from tddata import PortfolioAnalytics

# Three independent tools, zero coupling
async def multi_source_analysis():
    # Concurrent fetch from IBGE
    sidra = AsyncSidraClient()
    gdp = await sidra.fetch(table="1620", variable=116)
    
    # Transform RAIS labor data
    processor = RAISProcessor()
    rais = processor.process_year(2023, force_refresh=False)
    
    # Calculate portfolio returns
    analytics = PortfolioAnalytics()
    returns = analytics.calculate_monthly_returns(my_transactions)
    
    return gdp, rais, returns
```

## 2. Performance

**Speed matters**. All tools are engineered for speed at scale:

- Multithreaded concurrency where applicable (datasus-fetcher: 6-10x speedup)
- Async/await where applicable (sidra-fetcher: 4x speedup)
- Vectorial processing where applicable (pdet-data: 10x speedup)
- Smart caching and idempotence checks (comexdown: 57x speedup on re-runs)
- Streaming/chunked processing for large files (comexdown: constant memory overhead)
- Columnar storage formats (Parquet: 95%+ compression vs CSV)

### Why It Matters

When you're processing 50M+ row labor market datasets or downloading gigabytes of trade data, performance isn't a luxury—it's a prerequisite. Legacy tools like Pandas exhaust memory. Sequential downloads take weeks. Poor choices here lock you into slow, expensive infrastructure.

### How We Apply It

Every tool is benchmarked. Performance metrics are documented. When a faster approach exists, we use it:

- **RAIS (50M rows)**: Polars vectorial processing, not Pandas
- **DATASUS microdata (100+ GB)**: Multithreaded concurrent crawling, not sequential FTP
- **Treasury bonds (100k+ transactions)**: Async concurrent fetches, not sync requests
- **Siscomex (gigabyte files)**: Streaming chunks, not in-memory buffering

### Example: Idempotent Processing with 57x Speedup

```python
from comexdown import SiscomexDownloader

downloader = SiscomexDownloader(verify_ssl=False)

# First run: downloads full dataset (45 seconds)
result = downloader.download_exports(2023, force_refresh=False)

# Second run: checks Last-Modified via HEAD request (0.8 seconds)
# If unchanged, skips re-download entirely
result = downloader.download_exports(2023, force_refresh=False)

# 57x faster on re-runs because we check before downloading
```

## 3. Resilience

**Failures happen**. All tools are engineered to handle them gracefully.

### Why It Matters

Government APIs go down. FTP servers time out. SSL certificates expire. Network connections drop. Legacy infrastructure is unstable. Tools that crash on transient failures are unusable in production.

### How We Apply It

- **Auto-retry with exponential backoff**: Transient failures are retried 3-5 times with increasing delays
- **Smart resume**: If a download fails at 70%, subsequent runs resume from that point, not the beginning
- **SSL resilience**: Handle expired/misconfigured government certificates gracefully (comexdown)
- **Size-based idempotence**: Compare remote file size with local file; skip if identical (datasus-fetcher)
- **Validation at source**: Detect corruption/truncation immediately, not after expensive transformation

### Example: Auto-Retry with Exponential Backoff

```python
from datasus_fetcher import DATASUSCrawler

crawler = DATASUSCrawler(
    num_workers=5,
    timeout=60,
    max_retries=5,      # Retry up to 5 times
    backoff_factor=2    # Wait 1s, 2s, 4s, 8s, 16s between retries
)

# Transient failures are handled automatically
result = crawler.fetch_subsystem("SIM", year=2023)
# If a single FTP connection drops, others continue
# Failed downloads are retried automatically
```

### Example: Smart Resume

```python
# First attempt: interrupted at 70%
result1 = crawler.fetch_subsystem("SIM", year=2023, force_refresh=True)
# Downloads 70%, then connection drops

# Second attempt: resumes from checkpoint
result2 = crawler.fetch_subsystem("SIM", year=2023, force_refresh=False)
# Detects 70% complete locally; downloads only remaining 30%
# Total time: not 2x the first attempt, but 1.3x
```

## 4. Reproducibility

**Every transformation is deterministic and auditable**. You can replay any pipeline from raw data and get identical results.

### Why It Matters

In research, finance, and public health, reproducibility is non-negotiable. If you can't explain exactly what data was fetched, transformed, and stored, your analysis is worthless.

### How We Apply It

- **Versioned outputs**: Every download includes metadata (timestamp, source version, schema version)
- **Deterministic ordering**: Results are always sorted consistently; no random variation
- **Complete lineage**: Track which raw files produced which Parquet files
- **Audit trails**: Log every transformation step; never silently drop or modify data
- **Documentation extraction**: Download layouts, PDFs, and lookup tables alongside data (datasus-fetcher)

### Example: Versioned Outputs with Metadata

```python
from datasus_fetcher import DATASUSCrawler

crawler = DATASUSCrawler(num_workers=5, smart_resume=True)

result = crawler.fetch_subsystem_with_docs(
    subsystem="SIM",
    year=2023,
    include_layouts=True,
    include_documentation=True,
    include_lookup_tables=True
)

# Result includes:
# - data files (SIM_2023.parquet)
# - layouts (SIM_2023_layout_@timestamp.pdf)
# - documentation (SIM_2023_docs_@timestamp.pdf)
# - lookup tables (SIM_2023_codebook_@timestamp.csv)
# - metadata.json with download timestamp, source URL, checksums

# Later: you can use the exact documentation version from download time
# Reproducible: same input + same documentation version = same results
```

### Example: Complete Lineage

```python
# Raw RAIS CSV → Parquet transformation
processor = RAISProcessor()
result = processor.process_year(2023, force_refresh=False)

# Result includes metadata:
# {
#   "input_file": "RAIS_2023.zip",
#   "input_size_bytes": 8589934592,
#   "input_checksum": "sha256:...",
#   "output_file": "RAIS_2023.parquet",
#   "output_size_bytes": 402653184,
#   "schema_version": "2023-04-01",
#   "processing_timestamp": "2024-04-10T14:32:15Z",
#   "row_count": 58234521,
#   "processing_duration_seconds": 62.4
# }

# You can audit exactly what was transformed and when
```

## 5. No Magic

**Explicit is better than implicit**. You should understand what data is being fetched, how it's transformed, and where it's stored.

### Why It Matters

"Magic" is tempting for API designers. "Just call `fetch_all()` and it works!" But when something breaks, invisible magic makes debugging impossible. When you need to modify behavior, magic prevents it.

In data engineering, transparency is critical. You need to know:
- Exactly which API endpoints are being called
- Which rows are being filtered or transformed
- Why a pipeline succeeded or failed
- How to modify behavior for your specific needs

### How We Apply It

- **No implicit type conversions**: Date strings stay as strings until explicitly converted
- **No silent filtering**: If data is dropped, it's logged and reversible
- **Explicit concurrency**: Specify `num_workers=5` rather than auto-detecting CPU count
- **Clear error messages**: When something fails, the error message tells you why and how to fix it
- **Readable code**: Complex algorithms (FIFO lot matching, Modified Dietz) are documented with comments

### Example: Explicit Configuration

```python
# ✅ Clear: Explicit num_workers tells you exactly what's happening
crawler = DATASUSCrawler(
    num_workers=5,          # 5 concurrent FTP connections
    timeout=60,             # 60-second timeout per request
    max_retries=3,          # Retry up to 3 times on failure
    smart_resume=True       # Skip files unchanged since last run
)

# ❌ Unclear: Magic auto-detection hides what's actually happening
crawler = DATASUSCrawler()  # What concurrency level? What timeout?
```

### Example: Explicit Transformations

```python
# ❌ Magic: Lost data is invisible
df_filtered = df.filter(lambda row: row["salary"] > 0)  # Silently drops rows

# ✅ Clear: Explicitly track what was filtered and why
invalid_count = len(df.filter(pl.col("salary") <= 0))
df_filtered = df.filter(pl.col("salary") > 0)
print(f"Filtered {invalid_count} rows with salary ≤ 0")  # You know what happened
```

### Example: Explicit Error Messages

```python
# ✅ Clear error message
# "FTP connection timeout after 60 seconds.
#  Server: ftp.datasus.gov.br
#  Path: /dissemin/arquivos/SIM/
#  Retrying (attempt 2/5) with 2-second backoff..."

# ❌ Unclear error message
# "Error: Connection failed"
```

## Summary

These five principles work together:

1. **Modularity** lets you pick the right tool for your data source
2. **Performance** means you can handle Brazil's massive datasets
3. **Resilience** means your pipelines work despite infrastructure instability
4. **Reproducibility** means your analysis is auditable and replayable
5. **No Magic** means you understand and can troubleshoot everything

When you build on top of these tools, follow the same principles in your own code. The result is a data platform that is fast, reliable, transparent, and maintainable.
