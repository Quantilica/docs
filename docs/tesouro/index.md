# Treasury Direct (Tesouro Direto)

Brazilian government fixed-income securities platform. Treasury Direct offers direct investment in federal government bonds for individuals and institutions.

**tddata** is an industrial-grade financial engineering suite for Treasury Direct microdata—far more than a data client, it abstracts government communication and natively implements sophisticated financial mathematics for portfolio analytics.

## The Challenge

Treasury Direct data analysis encounters critical obstacles:

- **Volume & Speed**: Massive daily files with millions of records; traditional libraries (Pandas) cause memory exhaustion
- **FIFO Complexity**: Computing returns for investors with multiple purchases and partial sales requires strict accounting controls
- **Portfolio Performance**: Calculating monthly returns with deposits, withdrawals, and coupon income demands GIPS-compliant methodologies (Modified Dietz)

**tddata** solves these through smart async fetching, Polars-powered processing (10x faster), automatic FIFO lot matching, and Modified Dietz portfolio analytics.

## Architecture: How tddata Powers Treasury Analysis

```
┌─────────────────────────────────────────────────────┐
│     Brazilian Treasury (CKAN API)                   │
│     (Large daily files: prices, yields, volumes)    │
└─────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│  tddata (Smart Fetching + Analytics Layer)           │
│  ────────────────────────────────────────────────    │
│  ✓ Async downloads with idempotence checks          │
│  ✓ Polars processing (10x faster than Pandas)       │
│  ✓ FIFO inventory control (per-lot returns)         │
│  ✓ Modified Dietz (GIPS-compliant portfolio returns)│
│  ✓ Returns: Clean Polars DataFrames                 │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│     Your Analysis (Portfolio, Risk, Curve)          │
│     (Ready for BI, optimization, research)          │
└──────────────────────────────────────────────────────┘
```

## Core Capabilities

- ✅ **Smart async fetching** with idempotence (skip unchanged files)
- ✅ **Polars-powered analytics** (10x faster than Pandas)
- ✅ **FIFO lot matching** (precise per-lot returns with coupon injection)
- ✅ **Modified Dietz portfolio returns** (GIPS-compliant performance measurement)
- ✅ **Market-to-market pricing** (O(1) lookups for speed)
- ✅ **All bond types**: LTN, NTN-B, NTN-F, LFT, NTN-C
- ✅ **Export to Parquet, CSV, PostgreSQL**

## Use Cases

### Economic Monitoring
Track real-time Brazilian fixed-income market conditions:
- Yield curve trends (prefixed vs. inflation-indexed spreads)
- Duration risk exposure
- Market volatility and repricing

### Portfolio Management
Build and optimize Brazilian government bond portfolios:
- FIFO lot matching for per-lot returns
- Modified Dietz portfolio performance (GIPS-compliant)
- Asset allocation and duration management

### Quantitative Analysis
Model term structure and price dynamics:
- Yield curve modeling
- Interest rate sensitivity (duration/convexity)
- Market microstructure

### Academic Research
Study emerging market fixed-income dynamics with 20+ years of historical data.

### Risk Management
Calculate bond-level and portfolio-level risks:
- Interest rate risk (duration)
- Liquidity risk (bid-ask spreads)
- Credit risk (government solvency)

## Data Available

### Bond Types

| Code | Full Name | Characteristics |
|------|-----------|-----------------|
| **LTN** | Treasury Notes | Prefixed (zero-coupon), short-term |
| **NTN-B** | IPCA-indexed Notes | Inflation-protected, semi-annual coupons |
| **NTN-F** | Fixed-rate Notes | Prefixed with coupons, longer-term |
| **NTN-C** | CCI-indexed Notes | Currency-indexed (INPC) |
| **LFT** | Financial Treasury Letters | Selic-linked, floating-rate bonds |

### Available Metrics

For each bond and date:

- **Yield (YTM)**: Annual percentage yield
- **Price**: Market price as % of par
- **Duration**: Modified duration in years
- **Maturity Date**: When the bond expires
- **Accrued Interest**: Interest accrued since last coupon
- **Outstanding Volume**: Amount in circulation

## Workflow: Fetch → Process → Analyze

### Step 1: Fetch Treasury Data (Smart Async with Idempotence)

```python
import asyncio
from tddata import TreasuryFetcher

async def fetch_data():
    # 5 concurrent connections, skip if files unchanged
    fetcher = TreasuryFetcher(concurrent_downloads=5, check_etag=True)
    
    data = await fetcher.fetch_all(
        bond_types=["LTN", "NTN-B", "NTN-F", "LFT"],
        force_refresh=False  # Uses cache if available
    )
    
    await fetcher.aclose()
    return data

result = asyncio.run(fetch_data())
print(f"✓ Data ready: {len(result)} bond types")
```

### Step 2: Calculate Per-Lot Returns (FIFO Matching)

```python
from tddata import PortfolioAnalytics
import polars as pl

# Your transaction history
transactions = pl.read_parquet("transactions.parquet")

analytics = PortfolioAnalytics()

# FIFO: automatically matches sales to oldest purchases
lots = analytics.calculate_operations_returns(
    transactions=transactions,
    method="fifo",
    include_coupons=True  # Add coupon income
)

print(lots.select(["purchase_date", "sale_date", "annualized_return"]))
```

### Step 3: Calculate Monthly Portfolio Returns (Modified Dietz)

```python
# Your holdings and cash flows
holdings = pl.read_parquet("holdings.parquet")
prices = pl.read_parquet("prices.parquet")
cash_flows = pl.read_parquet("cash_flows.parquet")  # Deposits, withdrawals, coupons

# GIPS-compliant portfolio performance
monthly_returns = analytics.calculate_portfolio_monthly_returns(
    holdings=holdings,
    prices=prices,
    cash_flows=cash_flows,
    method="modified_dietz"
)

print(monthly_returns.select(["year_month", "return_pct"]))
```

## Best Practices

### 1. Always Use Async for Data Fetching

Concurrent downloads are dramatically faster:

```python
import asyncio
from tddata import TreasuryFetcher

# ❌ Slow: Sequential (30s)
fetcher = TreasuryFetcher(concurrent_downloads=1)

# ✅ Fast: Concurrent (5-10s)
fetcher = TreasuryFetcher(concurrent_downloads=5)

async def main():
    data = await fetcher.fetch_all(force_refresh=False)
    await fetcher.aclose()
    return data

asyncio.run(main())
```

### 2. Use Modified Dietz for Portfolio Returns

Never use simple returns when cash flows occur:

```python
# ❌ Wrong: Ignores timing of deposits
simple = (ending_value - beginning_value) / beginning_value

# ✅ Correct: GIPS-compliant (Modified Dietz)
monthly_returns = analytics.calculate_portfolio_monthly_returns(
    holdings=holdings,
    prices=prices,
    cash_flows=cash_flows,
    method="modified_dietz"  # Weights deposits by timing
)
```

### 3. Include Coupons in FIFO Returns

Always inject coupon income for accurate per-lot returns:

```python
# ✅ Correct: Includes coupon payments
lots = analytics.calculate_operations_returns(
    transactions=transactions,
    include_coupons=True  # Coupon income added
)

# ❌ Incomplete: Misses coupons
lots = analytics.calculate_operations_returns(
    transactions=transactions,
    include_coupons=False  # Only price appreciation
)
```

### 4. Use Polars, Not Pandas

Polars is 10x faster for large Treasury datasets:

```python
import polars as pl

# ❌ Slow (Pandas)
import pandas as pd
df = pd.read_csv("treasury.csv")  # Slow, high memory
grouped = df.groupby("bond_type").agg({"yield": "mean"})  # Minutes

# ✅ Fast (Polars)
df = pl.read_parquet("treasury.parquet")  # Fast, low memory
grouped = df.group_by("bond_type").agg(pl.col("yield").mean())  # <1s
```

### 5. Store in Parquet Format

Parquet provides 80%+ compression and faster I/O:

```python
import polars as pl

# Save processed data
result.write_parquet("treasury_processed.parquet")

# Load later (10x faster than CSV)
df = pl.read_parquet("treasury_processed.parquet")
```

### 6. Normalize Real Returns (NTN-B)

For IPCA-indexed bonds, separate nominal yield from inflation:

```python
from ibge_sidra_tabelas import SidraClient

# Get NTN-B yields
ntnb = pl.read_parquet("ntnb_data.parquet")

# Get IPCA inflation
ibge = SidraClient()
ipca = ibge.fetch(table="1737", variable=63)

# Calculate real yield
combined = (
    ntnb
    .join(ipca.rename({"value": "ipca_monthly"}), on="date")
    .with_columns([
        (pl.col("yield") - pl.col("ipca_monthly")).alias("real_yield")
    ])
)
```

## Key Concepts

### Prefixed Bonds (LTN, NTN-F)
You know the exact return when you buy. Fixed interest rate, paid at maturity (LTN) or semi-annually (NTN-F).

### IPCA-Indexed Bonds (NTN-B)
Principal adjusts by IPCA inflation. Coupon rate is typically 4-6% above inflation—the real return.

### Selic-Linked Bonds (LFT)
Interest rate tracks the Selic overnight rate. Minimal interest rate risk, but subject to inflation.

### Duration
Measures bond price sensitivity to interest rate changes. Higher duration = greater price volatility.

### Yield Curve
Relationship between yield and time-to-maturity. Steep curve suggests rate increases expected; flat suggests uncertainty.

## Tools in This Section

### [tddata](tddata.md)
Industrial-grade financial engineering suite for Treasury Direct. Master:
- **Smart async fetching** with idempotence (skip unchanged files)
- **FIFO lot matching** (per-lot returns with coupon injection)
- **Modified Dietz** (GIPS-compliant portfolio performance)
- **Polars processing** (10x faster than Pandas)
- **High-performance analytics** (10M+ rows in seconds)

### [Portfolio Returns Guide](calculo-retornos.md)
Deep dive into fixed-income mathematics:
- YTM and duration calculations
- Modified Dietz methodology
- Real returns for inflation-indexed bonds

## Performance & Benchmarks

- **Async fetching**: First run 30s → cached runs <1s (40x speedup)
- **Polars processing**: 15M rows in 0.34s (44M rows/sec throughput)
- **FIFO matching**: 500k transactions in 2.4s (208k tx/sec)

## When to Use tddata

**Use tddata when:**
- Building production Treasury Direct pipelines
- Calculating GIPS-compliant portfolio returns
- Analyzing millions of historical transactions
- Need precise per-lot return attribution (FIFO)
- Combining Treasury data with other data sources

**Use simple scripts when:**
- Quick one-off analysis
- Small datasets (<100MB)
- Academic exploration

## Learn More

- **[tddata Documentation](tddata.md)** — Complete feature reference
- **[IBGE Macroeconomics](../ibge/index.md)** — Pair Treasury yields with inflation data
- **[Architecture Overview](../architecture/overview.md)** — System design principles
- **[Treasury Direct Official](https://www.tesouro.gov.br/tesouro-direto)** — Government site (Portuguese)
