# Foreign Trade (Comex)

Brazilian import/export data from Siscomex (Integrated Foreign Trade System).

**comexdown** is a network-resilient extraction agent for Siscomex data — engineered to handle legacy government infrastructure with idempotent downloads and streaming efficiency.

## The Challenge

Programmatically extracting Brazilian trade data hits real infrastructure obstacles:

- **Colossal volume**: Gigabyte-scale CSV files exhaust naive in-memory downloads
- **Unstable servers**: Bandwidth throttling, SSL certificate issues, occasional drops
- **Redundant downloads**: Without modern APIs, re-running pipelines re-fetches files that have not changed

**comexdown** solves these through:

- **Temporal idempotency**: HEAD request checks `Last-Modified`; skips files already up to date
- **Streaming chunks**: 8 KiB blocks; constant memory regardless of file size
- **SSL resilience**: unverified SSL context for SECEX servers with bad certs; browser User-Agent
- **Auto-retry**: up to 3 attempts with exponential backoff (1 s → 2 s → 4 s)
- **Atomic writes**: download to `*.tmp` then rename, so partial files never appear

## Data Source: Siscomex

The Integrated Foreign Trade System provides:

- **Detailed transactions**: every import and export shipment
- **Commodity classification**: NCM (Nomenclatura Comum do Mercosul, ≈ HS) codes
- **Trade flows**: by country of origin / destination, optionally by Brazilian municipality
- **Granular metrics**: USD value, quantity, weight

**Coverage**:

- **Frequency**: monthly, ~3-week lag
- **Historical**: NCM-based 1997–present, NBM-based 1989–1996
- **Scope**: all formal trade

## Workflow: Download → Analyze → Insights

### Step 1: Download with Smart Caching (Idempotent)

```bash
# Exports + imports for 2023 (HEAD check skips up-to-date files)
comexdown trade 2023 -o ./DATA
```

Equivalent Python:

```python
from pathlib import Path
import comexdown

comexdown.get_year(Path("./DATA"), year=2023)
```

The CSVs land at `./DATA/exp/2023.csv` and `./DATA/imp/2023.csv`. Re-running the
command issues a HEAD request, sees `Last-Modified` matches local `mtime`, and
skips the GET entirely.

### Step 2: Multi-Year Analysis with Polars

```bash
# Download a decade
comexdown trade 2014:2023 -o ./DATA
```

```python
import polars as pl
from pathlib import Path

data_dir = Path("./DATA")

exports = pl.concat([
    pl.read_csv(data_dir / "exp" / f"{y}.csv", separator=";")
        .with_columns(pl.lit(y).alias("year"))
    for y in range(2014, 2024)
])

# Annual exports by destination
by_country_year = (
    exports
    .group_by(["year", "CO_PAIS"])
    .agg(pl.col("VL_FOB").sum().alias("annual_exports_usd"))
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

The SECEX CSVs are `;`-separated, `latin-1` (older years) or UTF-8 (recent), with columns named in Portuguese. Key fields for the NCM-based files (1997+):

| Field | Description |
|-------|-------------|
| `CO_ANO`, `CO_MES` | Year and month of the transaction |
| `CO_NCM` | NCM product code (8 digits) |
| `CO_UNID` | Statistical unit code (kg, m³, …) |
| `CO_PAIS` | Country of origin (imports) / destination (exports) |
| `SG_UF_NCM` | State of producer / importer |
| `CO_VIA` | Mode of transport |
| `CO_URF` | Customs unit |
| `QT_ESTAT` | Statistical quantity |
| `KG_LIQUIDO` | Net weight (kg) |
| `VL_FOB` | FOB value (USD) |

Use `comexdown table` (run without args) to list every auxiliary table that decodes these codes (`pais`, `ncm`, `via`, `urf`, `uf`, …).

## Performance & Behavior

| Operation | Notes |
|-----------|-------|
| First download | Streaming GET in 8 KiB chunks; written atomically via `*.tmp` rename |
| Up-to-date file | Single HEAD request; GET is skipped |
| Memory usage | ~8 KiB per active stream — bounded regardless of file size |
| Retries | 3 attempts, exponential backoff (1 s → 2 s → 4 s) |

`comexdown` does not download files in parallel today — calls are sequential.
For multi-year batches, just pass a range to the CLI (`trade 2014:2023`) and let
the idempotent HEAD checks make re-runs cheap.

## Best Practices

### 1. Re-run instead of forcing refresh

Every run already does the right thing — files with the same `Last-Modified` are
skipped. There is no `force_refresh` flag; if you really need to re-download,
delete the local file first.

```bash
# Idempotent: HEAD-checks every file, fetches only what is new
comexdown trade 2023 -o ./DATA
```

### 2. Use `complete` for static historical analysis

If you only need the full back-catalog, the bundled file is one download:

```bash
comexdown trade complete -o ./DATA
```

### 3. Pull auxiliary tables alongside trade data

The trade CSVs only carry codes — keep the lookup tables in sync:

```bash
comexdown table all -o ./DATA
```

### 4. Handle SECEX SSL quirks

`comexdown` already uses an unverified SSL context (`ssl._create_unverified_context()`) and a browser User-Agent, so it works against SECEX servers with expired or misconfigured certificates out of the box. No flag to set.

## Common Analyses

### Trade Balance by Country

```python
import polars as pl
from pathlib import Path

data_dir = Path("./DATA")
exports = pl.read_csv(data_dir / "exp" / "2023.csv", separator=";")
imports = pl.read_csv(data_dir / "imp" / "2023.csv", separator=";")

exp_by_country = exports.group_by("CO_PAIS").agg(
    pl.col("VL_FOB").sum().alias("exports_usd")
)
imp_by_country = imports.group_by("CO_PAIS").agg(
    pl.col("VL_FOB").sum().alias("imports_usd")
)

balance = exp_by_country.join(imp_by_country, on="CO_PAIS", how="full").with_columns(
    (pl.col("exports_usd").fill_null(0) - pl.col("imports_usd").fill_null(0))
        .alias("trade_balance_usd")
)

print(balance.sort("trade_balance_usd", descending=True).head(10))
```

### Top Export Products (joined with NCM names)

```python
import polars as pl
from pathlib import Path

data_dir = Path("./DATA")
exports = pl.read_csv(data_dir / "exp" / "2023.csv", separator=";")
ncm = pl.read_csv(data_dir / "auxiliary-tables" / "NCM.csv", separator=";")

top_products = (
    exports
    .group_by("CO_NCM")
    .agg(pl.col("VL_FOB").sum().alias("export_value_usd"))
    .join(ncm.select(["CO_NCM", "NO_NCM_POR"]), on="CO_NCM", how="left")
    .sort("export_value_usd", descending=True)
    .head(20)
)

print(top_products)
```

### Revealed Comparative Advantage (sketch)

```python
import polars as pl

# Brazil's share of own exports per product
by_product = exports.group_by("CO_NCM").agg(pl.col("VL_FOB").sum().alias("br_exports"))
total_br = by_product["br_exports"].sum()
by_product = by_product.with_columns(
    (pl.col("br_exports") / total_br).alias("br_share")
)
# Combine with an external "world share" table (from BACI / WTO)
# to compute RCA = br_share / world_share.
```

## Tools in This Section

### [comexdown](comexdown.md)

Resilient SECEX/COMEX downloader:

- **Temporal idempotency** — HEAD + `Last-Modified` skip already-current files
- **Streaming chunks** — 8 KiB blocks, constant memory
- **Atomic writes** — `*.tmp` + rename, no partial files
- **Auto-retry** — exponential backoff on transient failures
- **SSL resilience** — unverified context for SECEX servers with bad certs
- **No deps** — pure standard library

## Learn More

- **[comexdown Documentation](comexdown.md)** — Complete reference
- **[IBGE Macroeconomics](../ibge/index.md)** — GDP and economic data
- **[Architecture](../architecture/overview.md)** — System design
- **[Siscomex Official (Portuguese)](https://www.gov.br/produtividade-e-comercio-exterior/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta)** — Government source
