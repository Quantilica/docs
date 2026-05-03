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
from pdet_data.fetch import connect, fetch_rais
from tddata.analytics import calculate_portfolio_monthly_returns

# Three independent tools, zero coupling
async def multi_source_analysis():
    # 1. SIDRA metadata via async client
    async with AsyncSidraClient(timeout=60) as sidra:
        agregado = await sidra.get_agregado(1620)

    # 2. RAIS labor data via FTP
    ftp = connect()
    rais = fetch_rais(ftp, dest_dir="raw/rais")

    # 3. Treasury portfolio returns
    returns = calculate_portfolio_monthly_returns(my_transactions)

    return agregado, rais, returns
```

## 2. Performance

**Speed matters**. All tools are engineered for speed at scale:

- Multithreaded concurrency where applicable (datasus-fetcher: 6-10x speedup)
- Async/await where applicable (sidra-fetcher: 3x speedup on metadata harvest)
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

### Example: Idempotent Processing with HEAD + `Last-Modified`

```python
from pathlib import Path
import comexdown

# First run: streams the SECEX CSVs in 8 KiB chunks
comexdown.get_year(Path("./DATA"), year=2023)

# Second run: HEAD shows Last-Modified == local mtime, GET is skipped entirely
comexdown.get_year(Path("./DATA"), year=2023)

# Re-runs cost a single HEAD round-trip per file when nothing has changed.
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

### Example: Auto-Retry on Transient FTP Failures

```sh
# datasus-fetcher retries each file up to 3 times on FTP errors
# If one connection drops, the other threads continue downloading.
datasus-fetcher data --data-dir ./data sim-do-cid10 \
    --start 2023 --end 2023 --threads 5
```

Internally, each `Fetcher` thread reconnects and retries failed transfers without aborting the batch.

### Example: Size-Based Idempotence

```sh
# First run: downloads everything
datasus-fetcher data --data-dir ./data sim-do-cid10 --start 2023 --end 2023

# Re-run after a partial failure: remote size is compared to local size,
# and only missing or mismatched files are re-fetched.
datasus-fetcher data --data-dir ./data sim-do-cid10 --start 2023 --end 2023
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

```sh
# Microdata + codebooks + reference tables, each with date-stamped filenames
datasus-fetcher data --data-dir ./data sim-do-cid10 --start 2023 --end 2023
datasus-fetcher docs --data-dir ./docs sim
datasus-fetcher aux  --data-dir ./aux  sim
```

Each downloaded `.dbc` is named `dataset_uf_period_YYYYMMDD.dbc`, so multiple DATASUS revisions of the same period coexist on disk. Use `datasus-fetcher archive` to move non-latest versions out of the active tree while preserving them for audit.

### Example: Complete Lineage

```bash
# Raw RAIS .7z → typed Parquet
pdet-data fetch ./raw          # idempotent: skips files already on disk
pdet-data convert ./raw ./parquet
```

```python
# Capture lineage alongside the converted Parquet
import json, hashlib, polars as pl
from datetime import datetime, timezone
from pathlib import Path

raw  = Path("raw/rais-vinculos/rais-vinculos_2023@20240410.7z")
out  = Path("parquet/rais-vinculos/2023.parquet")

lineage = {
    "input_file":  str(raw),
    "input_size":  raw.stat().st_size,
    "input_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
    "output_file": str(out),
    "output_size": out.stat().st_size,
    "row_count":   pl.scan_parquet(out).select(pl.len()).collect().item(),
    "processed_at": datetime.now(timezone.utc).isoformat(),
    "tool": "pdet_data.convert_rais",
}
out.with_suffix(".lineage.json").write_text(json.dumps(lineage, indent=2))
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

```sh
# ✅ Clear: every flag is explicit
datasus-fetcher data \
    --data-dir ./data sim-do-cid10 \
    --start 2023 --end 2023 \
    --regions sp rj mg \
    --threads 5

# ❌ Implicit: defaults hide what is actually being fetched
datasus-fetcher data --data-dir ./data    # all 113 datasets, ~320 GB
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
