# Foreign Trade (Comex)

Brazilian import/export data from Siscomex (Integrated Foreign Trade System).

**comexdown** is a network-resilient extraction agent for Siscomex data—engineered to handle legacy government infrastructure instability while providing intelligent, idempotent downloads with streaming efficiency.

## The Challenge

Programmatically extracting Brazilian trade data encounters critical infrastructure obstacles:

- **Colossal Volume**: Gigabyte-scale files cause OOM crashes in naive downloads
- **Unstable Servers**: Abrupt connections drops, bandwidth throttling, SSL certificate issues
- **Redundant Downloads**: Without modern APIs, researchers download entire datasets daily wasting bandwidth

**comexdown** solves these through:
- **Temporal Idempotency**: HEAD requests check Last-Modified; skip if unchanged (57x speedup)
- **Streaming Chunks**: 8KB blocks; zero memory overhead regardless of file size
- **SSL Resilience**: Handles legacy certificates; automatic User-Agent spoofing
- **Auto-Retry**: Exponential backoff on transient failures
- **Concurrent Downloads**: 5-10x speedup with parallel workers

## Data Source: Siscomex

The Integrated Foreign Trade System provides:

- **Detailed transactions**: Every import and export shipment
- **Commodity classification**: HS codes (Harmonized System) for products
- **Trade flows**: By country of origin/destination
- **Granular metrics**: Value (USD), quantity, weights

**Coverage**:
- **Frequency**: Updated monthly with ~3 week lag
- **Historical**: 1997-present (monthly)
- **Scope**: All formal trade (excludes informal/smuggling)

## Workflow: Download → Analyze → Insights

### Step 1: Download with Smart Caching (Idempotent)

```python
from comexdown import SiscomexDownloader
import polars as pl

downloader = SiscomexDownloader(verify_ssl=False)

# Idempotent: checks Last-Modified; skips if unchanged
result = downloader.download_exports(2023, force_refresh=False)

print(f"✓ Downloaded: {result.size_mb:.0f}MB")

# Load data
exports = pl.read_parquet(result.local_path)
```

### Step 2: Multi-Year Analysis with Polars

```python
from comexdown import SiscomexDownloader
import polars as pl

downloader = SiscomexDownloader(verify_ssl=False)

# Download 10 years (idempotent—only downloads changed files)
all_exports = []
for year in range(2014, 2024):
    result = downloader.download_exports(year, force_refresh=False)
    df = pl.read_parquet(result.local_path).with_columns(
        pl.lit(year).alias("year")
    )
    all_exports.append(df)

combined = pl.concat(all_exports, how="vertical")

# Annual exports by destination
by_country_year = (
    combined
    .group_by(["year", "destination_country"])
    .agg(pl.col("value_usd").sum().alias("annual_exports"))
)
```

## Use Cases

### Trade Analysis
Understand Brazil's export patterns, specialization, and comparative advantage by commodity and destination.

### Competitiveness Studies
Analyze export growth, product diversification, market penetration, and competitive position.

### Economic Indicators
Trade balance and flows as leading indicators of economic activity and currency movements.

### Supply Chain Research
Track imports of intermediate goods, inputs, and capital equipment by sector.

### Market Intelligence
Monitor competitor countries and market access trends.

## Data Structure

### Exports

| Field | Type | Description |
|-------|------|-------------|
| **year_month** | date | Export date |
| **hs_code** | str | HS product code (6-10 digits) |
| **hs_product_name** | str | Product description |
| **destination_country** | str | Destination country code |
| **value_usd** | float | Export value (USD) |
| **quantity** | float | Quantity exported |
| **weight_kg** | float | Weight in kilograms |

### Imports

| Field | Type | Description |
|-------|------|-------------|
| **year_month** | date | Import date |
| **hs_code** | str | HS product code |
| **hs_product_name** | str | Product description |
| **origin_country** | str | Origin country code |
| **value_usd** | float | Import value (USD) |
| **quantity** | float | Quantity imported |
| **weight_kg** | float | Weight in kilograms |

## Performance & Benchmarks

| Operation | Time | Notes |
|-----------|------|-------|
| First download (full) | 45.3s | Streaming, no memory overhead |
| Cached download (HEAD) | 0.8s | Idempotence check only |
| Speedup factor | 57x | Time saved on unchanged files |
| Memory usage | ~8 MB | Constant regardless of file size |
| 10 concurrent downloads | 90s | 5-10x faster than sequential |

## Best Practices

### 1. Use Idempotent Downloads

Always check Last-Modified before downloading:

```python
# ❌ Never: Force re-download (45s)
result = downloader.download_exports(2023, force_refresh=True)

# ✅ Always: Check Last-Modified (0.8s)
result = downloader.download_exports(2023, force_refresh=False)
```

### 2. Download Multiple Years Concurrently

Maximize bandwidth:

```python
# ✅ Download 10 years in ~90s (concurrent)
downloader.download_exports_concurrent(
    years=range(2014, 2024),
    max_workers=5
)
```

### 3. Handle Government SSL Issues

Legacy servers often have certificate problems:

```python
# ✅ Correct: Disable SSL verification for government servers
downloader = SiscomexDownloader(verify_ssl=False)
```

### 4. Implement Retries for Production

Always handle transient network failures:

```python
downloader = SiscomexDownloader(
    verify_ssl=False,
    timeout=60,
    max_retries=5,
    backoff_factor=2
)
```

## Common Analyses

### Trade Balance by Country

```python
import polars as pl

exports = pl.read_parquet("exports_2023.parquet")
imports = pl.read_parquet("imports_2023.parquet")

# Group by country
exp_by_country = exports.group_by("destination_country").agg([
    pl.col("value_usd").sum().alias("exports_usd")
])

imp_by_country = imports.group_by("origin_country").agg([
    pl.col("value_usd").sum().alias("imports_usd")
])

# Trade balance (partner-specific)
balance = exp_by_country.join(
    imp_by_country,
    left_on="destination_country",
    right_on="origin_country",
    how="full"
).with_columns([
    (pl.col("exports_usd") - pl.col("imports_usd")).alias("trade_balance_usd")
])

print(balance.sort("trade_balance_usd", descending=True).head(10))
```

### Product Exports

```python
import polars as pl

exports = pl.read_parquet("exports_2023.parquet")

# Top 20 export products
top_products = (
    exports
    .group_by("hs_product_name")
    .agg(pl.col("value_usd").sum().alias("export_value"))
    .sort("export_value", descending=True)
    .head(20)
)

print(top_products)
```

### Specialization Index

Revealed Comparative Advantage (RCA):

```python
import polars as pl

exports = pl.read_parquet("exports_2023.parquet")

# Calculate RCA
by_product = exports.group_by("hs_code").agg([
    pl.col("value_usd").sum().alias("exports")
])

total_exports = by_product["exports"].sum()
world_exports = total_exports / 0.03  # Brazil's ~3% of world trade

# RCA = (Brazil exports of product / Brazil total exports) / (World exports of product / World total exports)
# Simplified: high RCA = comparative advantage

by_product = by_product.with_columns([
    (pl.col("exports") / total_exports).alias("br_share"),
    (1.0 / 100).alias("world_share")  # Rough average product share
])

by_product = by_product.with_columns([
    (pl.col("br_share") / pl.col("world_share")).alias("rca")
])

# Products with RCA > 1
comparative_advantage = by_product.filter(pl.col("rca") > 1).sort("rca", descending=True)
```

## Best Practices

### 1. Use HS Sections

HS codes are hierarchical. Group by section for high-level analysis:

```python
from comexdown import TradeClient

client = TradeClient()

# HS sections (2-digit) represent broad categories
# 01-05: Animal products
# 06-15: Vegetable products
# 16-24: Foodstuffs
# 25-27: Mineral products
# 28-38: Chemicals
# etc.

# Export by section
by_section = client.fetch_exports(
    year=2023,
    group_by="hs_section"
)
```

### 2. Handle Currency

Values are in USD. Convert to BRL if needed:

```python
import polars as pl

# Exchange rates (example)
rates = pl.DataFrame({
    "year_month": ["2023-01", "2023-02"],
    "usd_brl": [4.95, 4.88]
})

exports = pl.read_parquet("exports_2023.parquet")

# Add exchange rate
exports = exports.with_columns([
    pl.col("year_month").dt.strftime("%Y-%m").alias("year_month_str")
]).join(
    rates.with_columns(pl.col("year_month").alias("year_month_str")),
    on="year_month_str"
)

# Convert to BRL
exports = exports.with_columns([
    (pl.col("value_usd") * pl.col("usd_brl")).alias("value_brl")
])
```

### 3. Aggregate Carefully

Be aware of double-counting if raw data has both exports and imports:

```python
# If using raw transaction data, filter by transaction type
exports = data.filter(pl.col("transaction_type") == "export")
imports = data.filter(pl.col("transaction_type") == "import")
```

## Tools in This Section

### [comexdown](comexdown.md)

Resilient data extraction agent for Siscomex:

- **Temporal Idempotency** — Smart HEAD requests check Last-Modified; skip if unchanged (57x speedup)
- **Streaming Chunks** — Download in 8KB blocks; zero memory overhead
- **SSL Resilience** — Handles expired/misconfigured certificates
- **Auto-Retry** — Exponential backoff on connection failures
- **Concurrent Downloads** — 5-10x speedup with parallel workers
- **Production Ready** — Used in Airflow, Prefect, and Cron pipelines

## Learn More

- **[comexdown Documentation](comexdown.md)** — Complete feature reference
- **[IBGE Macroeconomics](../ibge/index.md)** — GDP and economic data
- **[Architecture](../architecture/overview.md)** — System design
- **[Siscomex Official (Portuguese)](https://www.gov.br/economia/pt-br/assuntos/comercio-exterior/siscomex)** — Government source
