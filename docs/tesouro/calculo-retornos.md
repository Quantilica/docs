# Portfolio Returns & Duration Guide

Calculate returns, YTM, and interest rate sensitivity for fixed-income portfolios.

## Key Concepts

### Yield to Maturity (YTM)

Annual return if bond is held to maturity. Accounts for:
- Current market price
- Coupon payments
- Principal repayment at maturity
- Reinvestment at same yield

```
Price = Σ(Coupon / (1 + YTM)^t) + Principal / (1 + YTM)^T
```

For Brazilian bonds, YTM is already provided by **tddata**.

### Modified Duration

Measure of bond price sensitivity to interest rate changes:

```
Duration_modified = Duration_macaulay / (1 + YTM)
```

**Rule of thumb:** 1% yield increase → Duration% price decrease

Example: 5-year bond with 5 years duration:
- Yield rises 1% → Price falls ~5%
- Yield falls 1% → Price rises ~5%

### Accrued Interest

Interest earned since last coupon date but not yet paid:

```
Accrued = Coupon × (Days since last coupon) / (Days in coupon period)
```

**Clean price**: Quoted bond price (ex-accrued)
**Dirty price**: Clean price + accrued interest = what you actually pay

### Real Return (IPCA-Indexed)

For NTN-B bonds, separate nominal yield into components:

```
Nominal Yield = Real Yield + Inflation Expectation
```

Example:
- NTN-B yield: 5.0%
- Expected IPCA: 3.5%
- Implied real yield: 1.5%

## Quick Calculations

### Single Bond Holding

```python
import polars as pl
from datetime import date
from pathlib import Path
from tddata import reader
from tddata.constants import Column as C, BondType

# Read the prices CSV downloaded with `tddata download --dataset prices`
prices = reader.read_prices(next(Path("./data").glob("taxas-dos-titulos*.csv")))

# Pick one bond: NTN-B (Tesouro IPCA+ com Juros Semestrais) maturing 2027-05-15
bond = prices.filter(
    (pl.col(C.BOND_TYPE.value) == BondType.NTNB.value)
    & (pl.col(C.MATURITY_DATE.value) == date(2027, 5, 15))
).sort(C.REFERENCE_DATE.value).tail(1).row(0, named=True)

face_value = 1000.0
purchase_price = bond[C.BUY_PRICE.value]   # current ask, in BRL
ytm_pct        = bond[C.BUY_YIELD.value]   # already in percent in the CSV

print(f"Purchase price: R${purchase_price:,.2f}")
print(f"Annual YTM:     {ytm_pct:.2f}%")
```

### Portfolio Weighted Average Yield

```python
import polars as pl

# Portfolio
portfolio = pl.DataFrame({
    "bond_name": ["LTN_2025", "NTN-B_2027", "LFT_2026"],
    "quantity": [100, 50, 75],  # Units held
    "current_price": [97.50, 105.25, 100.10],  # Clean price
    "ytm": [9.5, 5.8, 10.6]  # Annual YTM %
})

# Calculate portfolio value and weighted yield
portfolio = portfolio.with_columns([
    (pl.col("quantity") * pl.col("current_price")).alias("market_value")
])

total_value = portfolio["market_value"].sum()
portfolio_ytm = (
    (portfolio["market_value"] * portfolio["ytm"]).sum() / total_value
)

print(f"Total portfolio value: R${total_value:,.2f}")
print(f"Portfolio YTM: {portfolio_ytm:.2f}%")

# Show allocation
portfolio = portfolio.with_columns([
    (pl.col("market_value") / total_value * 100).alias("allocation_%")
])
print(portfolio.select(["bond_name", "allocation_%"]))
```

### Portfolio Duration (Interest Rate Risk)

```python
import polars as pl

# Portfolio with duration data
portfolio = pl.DataFrame({
    "bond_name": ["LTN_2025", "NTN-B_2027", "LFT_2026"],
    "market_value": [97500, 52625, 75075],  # Total value in Reais
    "duration": [0.9, 4.5, 1.2]  # Modified duration in years
})

# Calculate portfolio duration
total_value = portfolio["market_value"].sum()
portfolio_duration = (
    (portfolio["market_value"] * portfolio["duration"]).sum() / total_value
)

print(f"Portfolio duration: {portfolio_duration:.2f} years")
print(f"If yields rise 1%, portfolio loses ~{portfolio_duration:.2f}%")
print(f"If yields fall 1%, portfolio gains ~{portfolio_duration:.2f}%")

# Show duration by position
portfolio = portfolio.with_columns([
    (pl.col("market_value") / total_value * 100).alias("weight_%"),
    (pl.col("duration") * pl.col("market_value") / total_value).alias("duration_contribution")
])

print(portfolio.select(["bond_name", "weight_%", "duration", "duration_contribution"]))
```

### Rate Shock Analysis

How does portfolio perform if yields change?

```python
import polars as pl

bonds = pl.DataFrame({
    "name": ["LTN_2025", "NTN-B_2027"],
    "clean_price": [97.50, 105.25],
    "quantity": [100, 50],
    "duration": [0.9, 4.5],
    "ytm": [9.5, 5.8]
})

# Current market value
bonds = bonds.with_columns([
    (pl.col("clean_price") * pl.col("quantity")).alias("market_value")
])

current_value = bonds["market_value"].sum()

# Calculate price impact of yield changes using duration
# New price ≈ Old price - Duration × Price × ΔYield
yield_changes = [-1.0, -0.5, 0.0, 0.5, 1.0]  # Percentage points

print(f"Current portfolio value: R${current_value:,.2f}\n")
print("Yield change | New value | P&L")
print("-" * 40)

for dy in yield_changes:
    new_price = bonds.with_columns([
        (pl.col("clean_price") * (1 - pl.col("duration") * dy / 100)).alias("new_price")
    ])
    new_value = (new_price["new_price"] * new_price["quantity"]).sum()
    pnl = new_value - current_value
    
    print(f"{dy:+.1f}% | R${new_value:,.0f} | R${pnl:+,.0f}")
```

## Bond Pricing

### Clean vs. Dirty Price

```python
import polars as pl

bond = pl.DataFrame({
    "bond": ["NTN-B_2027"],
    "clean_price": [105.25],
    "accrued_interest": [1.45],  # From last coupon date
    "quantity": [50]
})

# Calculate total cost
bond = bond.with_columns([
    pl.col("clean_price") + pl.col("accrued_interest"),
    (
        (pl.col("clean_price") + pl.col("accrued_interest")) *
        pl.col("quantity") / 100
    ).alias("total_cost")
])

print(f"Clean price: R${bond['clean_price'][0]}")
print(f"Accrued interest: R${bond['accrued_interest'][0]}")
print(f"Dirty price: R${bond['clean_price'][0] + bond['accrued_interest'][0]}")
print(f"Total cost for {bond['quantity'][0]} units: R${bond['total_cost'][0]:,.2f}")
```

## Real Return Calculation (IPCA-Indexed Bonds)

### Method 1: Using Provided YTM

```python
import polars as pl

# NTN-B with YTM and realized inflation
bonds = pl.DataFrame({
    "date": ["2023-01-01", "2024-01-01"],
    "yield": [5.8, 6.2],  # Nominal yield %
    "ipca_realized": [10.1, 4.5]  # Actual IPCA %
})

# Real return = (1 + Nominal) / (1 + Inflation) - 1
bonds = bonds.with_columns([
    (
        ((1 + pl.col("yield") / 100) / (1 + pl.col("ipca_realized") / 100)) - 1
    ).alias("real_return")
])

print(bonds.select(["date", "yield", "ipca_realized", "real_return"]))
```

### Method 2: Break-Even Inflation

What inflation rate makes you indifferent between prefixed and IPCA-indexed?

```python
# LTN (prefixed) yield
ltn_yield = 0.095  # 9.5%

# NTN-B (inflation-indexed) yield
ntb_yield = 0.058  # 5.8%

# Break-even inflation = (1 + LTN yield) / (1 + NTB yield) - 1
breakeven = ((1 + ltn_yield) / (1 + ntb_yield)) - 1

print(f"LTN yield: {ltn_yield*100:.1f}%")
print(f"NTN-B yield: {ntb_yield*100:.1f}%")
print(f"Market expects inflation: {breakeven*100:.1f}%")
```

## Production Pipeline

### Daily Update Script

```python
import asyncio
import polars as pl
from pathlib import Path
from tddata import downloader, reader
from tddata.constants import Column as C

data_dir = Path("data/treasury")
data_dir.mkdir(parents=True, exist_ok=True)

# 1. Fetch latest prices CSV (idempotent on Last-Modified)
asyncio.run(
    downloader.download(
        data_dir,
        dataset_id="taxas-dos-titulos-ofertados-pelo-tesouro-direto",
        max_concurrency=3,
    )
)

# 2. Read newest CSV
latest_csv = max(data_dir.glob("taxas-dos-titulos*.csv"), key=lambda p: p.stat().st_mtime)
prices = reader.read_prices(latest_csv)

# 3. Append to running history (dedup by reference_date + bond_type + maturity)
history_file = data_dir / "prices_history.parquet"
if history_file.exists():
    existing = pl.read_parquet(history_file)
    prices = pl.concat([existing, prices]).unique(
        subset=[C.REFERENCE_DATE.value, C.BOND_TYPE.value, C.MATURITY_DATE.value]
    )

prices.write_parquet(history_file)

# 4. Snapshot the latest reference date
latest_date = prices[C.REFERENCE_DATE.value].max()
latest = prices.filter(pl.col(C.REFERENCE_DATE.value) == latest_date)
latest.write_parquet(data_dir / "latest_snapshot.parquet")

print(f"Updated {prices.height:,} rows; latest reference date {latest_date}")

# 5. Per-bond-type aggregates
metrics = (
    latest.group_by(C.BOND_TYPE.value)
    .agg(
        avg_buy_yield=pl.col(C.BUY_YIELD.value).mean(),
        avg_buy_price=pl.col(C.BUY_PRICE.value).mean(),
        n_maturities=pl.col(C.MATURITY_DATE.value).n_unique(),
    )
)
metrics.write_parquet(data_dir / "portfolio_metrics.parquet")
```

### Monitoring Dashboard Metrics

```python
import polars as pl
from datetime import datetime

# Load latest data
bonds = pl.read_parquet("data/treasury/latest_snapshot.parquet")

# Key metrics by bond type
metrics = bonds.group_by("bond_type").agg([
    pl.col("yield").mean().alias("avg_ytm"),
    pl.col("duration").mean().alias("avg_duration"),
    pl.col("volume").sum().alias("total_volume"),
    pl.col("bond_id").count().alias("num_bonds")
]).sort("bond_type")

print(f"Treasury Dashboard - {datetime.now().strftime('%Y-%m-%d')}\n")
print(metrics)

# Yield curve (NTN-B example)
ntb = bonds.filter(pl.col("bond_type") == "NTN-B").sort("maturity_date")
print("\nNTN-B Yield Curve:")
print(ntb.select(["maturity_date", "yield", "duration"]))
```

## Common Pitfalls

### Mistake 1: Confusing Clean and Dirty Price

Always remember: **you pay dirty price** but bond quotes are clean price.

```python
# Wrong: Buying 50 bonds at quoted 105.25
cost = 50 * 105.25 * 10  # Wrong: doesn't include accrued

# Right: Add accrued interest
cost = 50 * (105.25 + 1.45) * 10  # Correct
```

### Mistake 2: Ignoring Coupon Dates

Coupons are paid on specific dates. If you buy between coupon dates, seller gets your accrued:

```python
# If you buy bond between coupon dates
# 1. You pay accrued interest to seller
# 2. On next coupon date, you receive full coupon
# 3. Net effect: you earn accrued interest until coupon date
```

### Mistake 3: Using YTM for Short-Term Returns

YTM assumes holding to maturity. For short-term trades, use:

```
Price return = (New price - Purchase price) / Purchase price
Total return = Price return + Coupon received / Purchase price
```

### Mistake 4: Forgetting Reinvestment Risk

YTM assumes coupons are reinvested at the same yield. In reality:

```python
# Lower yields when reinvesting coupons
current_yield = 5.8  # %
coupon_yield = 4.5   # % for reinvestment

# Actual return < YTM
```

## See Also

- [Treasury Overview](index.md)
- [tddata Tool](tddata.md)
- [IBGE Data](../ibge/index.md) — For inflation data
