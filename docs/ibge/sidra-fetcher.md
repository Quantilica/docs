# sidra-fetcher

Advanced SDK for programmatic extraction from IBGE's SIDRA API.

## What It Is

**`sidra-fetcher`** is a production-grade Python SDK engineered for robust extraction of data and metadata from the Sistema IBGE de Recuperação Automática (SIDRA).

It serves as the network infrastructure layer between IBGE servers and data science applications: typed metadata models, URL abstraction via the `Parametro` class, and resilient HTTP clients (sync + async) with automatic retries.

## Problem It Solves

SIDRA is one of Brazil's richest data sources—housing everything from IPCA inflation to Census demographics. However, consuming this data at scale encounters **two severe engineering bottlenecks**:

### 1. Network Instability

Government servers frequently suffer overload, resulting in:

- Connection drops and timeouts
- Transient errors (HTTP 429 rate limiting, 500+ server errors)
- Scripts that fail and interrupt entire pipelines

### 2. Parametric Complexity

The SIDRA API uses cryptic positional URL structures:

```
/t/1737/n1/all/n3/all/v/2265/p/all/d/m
```

Manual URL construction via string concatenation is error-prone and difficult to maintain.

**`sidra-fetcher` was architected specifically to mitigate both bottlenecks:**

```python
# Build a SIDRA request declaratively, no string concatenation
from sidra_fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao

param = Parametro(
    agregado="1620",
    territorios={"1": ["all"]},
    variaveis=["116"],
    periodos=[],
    classificacoes={},
    formato=Formato.A,
    decimais={"": Precisao.M},
)

with SidraClient(timeout=60) as client:
    data = client.get(param.url())  # raw list[dict] from SIDRA
```

## Architecture & Key Features

### Dual Client Model (Sync + Async)

The library exposes two HTTP clients based on `httpx`:

- **`SidraClient`**: Synchronous client for point extractions, notebook exploration, or `ThreadPoolExecutor` workflows
- **`AsyncSidraClient`**: 100% asynchronous via `asyncio`. Fetch metadata, periods, and localidades concurrently with `asyncio.gather()`, drastically reducing I/O-bound wait times

### Industrial-Grade Resilience (Smart Retries)

Tolerance policies via `tenacity`:
- ✅ Retries up to 3 attempts on each metadata method
- ✅ Exponential backoff for periodos requests (`min=3`, `max=30` seconds)
- ✅ Handles transient `httpx` failures (timeouts, network errors)

### URL Abstraction Engine (`Parametro`)

The `sidra_fetcher.sidra` module eliminates magic strings:
- ✅ Transforms Python dicts/lists → valid SIDRA URLs transparently
- ✅ Native enums for output `Formato` (`A`, `C`, `N`, `U`) and `Precisao` (`S`, `M`, `D0`–`D20`)
- ✅ Reverse engineering: `parameter_from_url()` parses any SIDRA URL → `Parametro` object

### Strict Domain Modeling (Strong Typing)

Metadata responses are parsed into rich dataclasses:
- ✅ `Agregado` (root) → `Variavel`, `Classificacao`, `Categoria`, `Periodicidade`, `AgregadoNivelTerritorial`
- ✅ `Periodo`, `Localidade`, `NivelTerritorial`
- ✅ `IndicePesquisaAgregados`, `IndiceAgregado` for catalog navigation
- ✅ IDE autocompletion + linter integration

### Additional Features
- ✅ Streaming HTTP responses (low memory footprint)
- ✅ JSON parsing of all responses
- ✅ Reader helpers (`read_metadados`, `read_periodos`, `read_localidades`)
- ✅ Save/load metadata to disk (`save_agregado`, `load_agregado`)
- ✅ Logging via stdlib `logging` (logger name = `sidra_fetcher`)

## Installation

=== "pip"

    ```bash
    pip install sidra-fetcher
    ```

=== "uv"

    ```bash
    uv pip install sidra-fetcher
    ```

=== "from source"

    ```bash
    pip install git+https://github.com/Quantilica/sidra-fetcher.git
    ```

## Async/Await: High-Throughput Metadata Extraction

For large-scale metadata harvesting, use the **`AsyncSidraClient`** to fetch multiple aggregates concurrently. Network I/O is the bottleneck; `asyncio.gather()` removes it.

### Sync vs Async Performance

**Sync approach** (sequential):

```
Fetch metadata for table 1620: ~2 seconds
Fetch metadata for table 1612: ~2 seconds
Fetch metadata for table 1637: ~2 seconds
Total: ~6 seconds
```

**Async approach** (concurrent):

```
Fetch all three concurrently
Total: ~2 seconds (3x faster)
```

### Async Example

```python
import asyncio
from sidra_fetcher import AsyncSidraClient

async def fetch_macro_metadata():
    """Fetch metadata for GDP, GVA, and Investment aggregates concurrently."""
    async with AsyncSidraClient(timeout=60) as client:
        gdp_meta, gva_meta, inv_meta = await asyncio.gather(
            client.get_agregado(1620),  # GDP
            client.get_agregado(1612),  # GVA
            client.get_agregado(1637),  # Investment
        )
    return gdp_meta, gva_meta, inv_meta

gdp, gva, inv = asyncio.run(fetch_macro_metadata())
print(f"{gdp.nome}: {len(gdp.periodos)} periods, {len(gdp.localidades)} localidades")
```

## Quick Example (Synchronous)

```python
from sidra_fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao

with SidraClient(timeout=60) as client:
    # 1. Fetch metadata
    agregado = client.get_agregado_metadados(1620)
    print(f"Table: {agregado.nome}")
    print(f"Variables: {[v.id for v in agregado.variaveis]}")

    # 2. Build a data request
    param = Parametro(
        agregado="1620",
        territorios={"1": ["all"]},   # Brazil total
        variaveis=["116"],
        periodos=[],                  # all periods
        classificacoes={},
        formato=Formato.A,
        decimais={"": Precisao.M},
    )

    # 3. Fetch the data (raw list[dict])
    rows = client.get(param.url())
    print(f"Got {len(rows)} rows")
```

The data is returned as a `list[dict]` matching the SIDRA `/values` JSON schema.
Convert to a DataFrame yourself with Polars or pandas:

```python
import polars as pl
df = pl.DataFrame(rows)
df.write_parquet("gdp.parquet")
```

## How It Works

### Architecture

```
Build a Parametro:
    Parametro(agregado="1620", variaveis=["116"], ...)
         ↓
Render URL:
    parametro.url()
    → /t/1620/n1/all/v/116/p/all/h/y/f/a/d/m
         ↓
HTTP Client (with @retry decorators):
    client.get(url)
    → tenacity retries on transient failures
    → streams the response body
         ↓
JSON parsing:
    Returns raw list[dict] (SIDRA /values format)
         ↓
User processes data:
    Polars / pandas / database insert
```

### URL Abstraction: No More Magic Strings

```python
# ❌ Error-prone (manual URL construction)
url = f"/t/1620/n1/all/v/116/p/all/d/m?lang=en"

# ✅ Type-safe (Parametro abstraction)
from sidra_fetcher.sidra import Parametro, Formato, Precisao

param = Parametro(
    agregado="1620",
    territorios={"1": ["all"]},
    variaveis=["116"],
    periodos=[],
    classificacoes={},
    formato=Formato.A,
    decimais={"": Precisao.M},
)
print(param.url())
# https://apisidra.ibge.gov.br/values/t/1620/n1/all/v/116/p/all/h/y/f/a/d/m
```

### Reverse Engineering: URL to Python

Copied a URL from the SIDRA website? Parse it directly:

```python
from sidra_fetcher.sidra import parameter_from_url

url = "https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2265/p/all/d/m"
param = parameter_from_url(url)
print(param.agregado)   # "1737"
print(param.variaveis)  # ["2265"]
print(param.territorios)  # {"1": ["all"]}
```

### Authentication & Rate Limits

SIDRA API is public—no authentication required. Be courteous with rate (especially during business hours in Brazil); `tenacity` handles transient failures but won't help if you saturate the server.

### Retry Logic

Retries are wired in via `tenacity` decorators on each metadata method:

- `get_indice_pesquisas_agregados`: up to 3 attempts
- `get_agregado_metadados`: up to 3 attempts
- `get_agregado_periodos`: up to 3 attempts with exponential backoff (3s → 30s)

The raw `client.get(url)` is **not** decorated with retry. If you need retries on data downloads, wrap your call:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=3, max=60))
def fetch_with_retry(client, url):
    return client.get(url)

rows = fetch_with_retry(client, param.url())
```

## API Reference

### `SidraClient(timeout=60)` — Synchronous Client

```python
from sidra_fetcher import SidraClient

with SidraClient(timeout=60) as client:
    ...
```

**Constructor:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `timeout` | int | 60 | Per-request timeout in seconds |

**Methods:**

| Method | Returns | Purpose |
|--------|---------|---------|
| `client.get(url)` | `Any` (parsed JSON) | Raw GET request; use for `Parametro.url()` data downloads |
| `client.get_indice_pesquisas_agregados()` | `list[IndicePesquisaAgregados]` | Index of all surveys + their aggregates |
| `client.get_agregado_metadados(agregado_id)` | `Agregado` | Variables, classifications, periodicidade, territorial levels |
| `client.get_agregado_periodos(agregado_id)` | `list[Periodo]` | All periods for the aggregate |
| `client.get_agregado_localidades(agregado_id, localidades_nivel)` | `list[Localidade]` | Territorial units at the requested level(s) |
| `client.get_agregado(agregado_id)` | `Agregado` | Composed: metadata + periods + all localidades |
| `client.get_acervo(acervo)` | `Any` | Fetch the acervo index (`AcervoEnum.A` / `.E`) |

Use as a context manager (`with SidraClient(...) as client:`) to ensure the underlying `httpx.Client` is closed.

### `AsyncSidraClient(timeout=60)` — Asynchronous Client

```python
from sidra_fetcher import AsyncSidraClient
import asyncio

async def main():
    async with AsyncSidraClient(timeout=60) as client:
        results = await asyncio.gather(
            client.get_agregado(1620),
            client.get_agregado(1612),
            client.get_agregado(1637),
        )
    return results

asyncio.run(main())
```

Same method surface as `SidraClient`, but every method is `async`. Use `async with` for the context manager.

### `Parametro` — SIDRA URL Builder

```python
from sidra_fetcher.sidra import Parametro, Formato, Precisao

param = Parametro(
    agregado="1620",
    territorios={"1": ["all"], "3": ["35", "33"]},
    variaveis=["116", "117"],
    periodos=["202301", "202302"],
    classificacoes={"11255": ["all"]},
    cabecalho=True,
    formato=Formato.A,
    decimais={"": Precisao.M},
)
url = param.url()
```

**Constructor:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agregado` | str | required | SIDRA table code |
| `territorios` | dict[str, list[str]] | required | Territory level → unit codes (`["all"]` or `[]` = all) |
| `variaveis` | list[str] | required | Variable codes (empty = all) |
| `periodos` | list[str] | required | Period codes (empty = all) |
| `classificacoes` | dict[str, list[str]] | required | Classification → category codes |
| `cabecalho` | bool | True | Include header row (`/h/y` vs `/h/n`) |
| `formato` | Formato | `Formato.A` | Output formato (`A`, `C`, `N`, `U`) |
| `decimais` | dict[str, Precisao] | `{"": Precisao.M}` | Decimal precision per variable |

**Helpers:**

| Function | Purpose |
|----------|---------|
| `param.url()` | Render the full SIDRA `/values` URL |
| `param.assign(name, value)` | Return a copy with one field replaced |
| `parameter_from_url(url)` | Parse a SIDRA URL → `Parametro` |
| `get_sidra_url_request_period(parametro, period_id)` | Render URL with periods replaced by a single period |

### Domain Model (Dataclasses)

Returned by metadata methods:

```python
from sidra_fetcher.agregados import (
    Agregado, Variavel, Classificacao, Categoria,
    Periodo, Localidade, NivelTerritorial,
    Periodicidade, AgregadoNivelTerritorial,
    Pesquisa, IndicePesquisaAgregados, IndiceAgregado,
)
```

`Agregado` (returned by `get_agregado_metadados` / `get_agregado`):

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | str | Aggregate id |
| `nome` | str | Aggregate name |
| `url` | str | SIDRA URL for this table |
| `pesquisa` | Pesquisa | Owning survey |
| `assunto` | str | Subject |
| `periodicidade` | Periodicidade | Frequency + date range |
| `nivel_territorial` | AgregadoNivelTerritorial | Supported levels |
| `variaveis` | list[Variavel] | Available variables |
| `classificacoes` | list[Classificacao] | Available classifications |
| `periodos` | list[Periodo] | Periods (populated by `get_agregado`) |
| `localidades` | list[Localidade] | Localities (populated by `get_agregado`) |

### Reader Helpers

```python
from sidra_fetcher.reader import (
    read_metadados,
    read_periodos,
    read_localidades,
    save_agregado,
    load_agregado,
    flatten_aggregate_metadata,
    flatten_surveys_metadata,
)

# Persist an Agregado to disk for later reuse
save_agregado(agregado, "agregado_1620.json")

# Reload it without hitting the API
agregado = load_agregado("agregado_1620.json")
```

## Common Patterns

### Discover a Table's Variables and Periods

```python
from sidra_fetcher import SidraClient

with SidraClient() as client:
    agregado = client.get_agregado_metadados(1620)

    print(f"Table: {agregado.nome}")
    print(f"Periodicidade: {agregado.periodicidade.frequencia}")

    print("\nVariables:")
    for v in agregado.variaveis:
        print(f"  {v.id}: {v.nome} ({v.unidade})")

    print("\nClassifications:")
    for c in agregado.classificacoes:
        print(f"  {c.id}: {c.nome} ({len(c.categorias)} categories)")
```

### Build a Data Request from a SIDRA Web URL

```python
from sidra_fetcher import SidraClient
from sidra_fetcher.sidra import parameter_from_url

# Copied from sidra.ibge.gov.br
web_url = "https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2265/p/all/d/m"
param = parameter_from_url(web_url)

with SidraClient() as client:
    rows = client.get(param.url())
```

### Period-by-Period Streaming

For large tables, fetch one period at a time to bound memory:

```python
from sidra_fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao, get_sidra_url_request_period

base = Parametro(
    agregado="1620",
    territorios={"6": []},
    variaveis=["116"],
    periodos=[],
    classificacoes={},
    formato=Formato.A,
    decimais={"": Precisao.M},
)

with SidraClient() as client:
    periodos = client.get_agregado_periodos(1620)
    for p in periodos:
        url = get_sidra_url_request_period(base, p.id)
        rows = client.get(url)
        # process / persist `rows` here
```

### Concurrent Metadata Harvesting

```python
import asyncio
from sidra_fetcher import AsyncSidraClient

async def harvest(table_ids):
    async with AsyncSidraClient(timeout=60) as client:
        return await asyncio.gather(
            *(client.get_agregado(tid) for tid in table_ids)
        )

agregados = asyncio.run(harvest([1620, 1612, 1637, 1737]))
```

### Convert to DataFrame and Persist

```python
import polars as pl

rows = client.get(param.url())  # list[dict]
df = pl.DataFrame(rows)
df.write_parquet("data.parquet")
```

## Performance Tips

### 1. Cache Metadata to Disk

Metadata changes infrequently. Save it once, reload from disk on subsequent runs:

```python
from pathlib import Path
from sidra_fetcher import SidraClient
from sidra_fetcher.reader import save_agregado, load_agregado

cache = Path("agregado_1620.json")

if cache.exists():
    agregado = load_agregado(cache)
else:
    with SidraClient() as client:
        agregado = client.get_agregado(1620)
    save_agregado(agregado, cache)
```

### 2. Filter Periods Server-Side

Don't fetch all history if you only need a window. Use the `periodos` field on `Parametro`:

```python
param = Parametro(
    agregado="1620",
    territorios={"1": ["all"]},
    variaveis=["116"],
    periodos=["202001", "202002", "202003"],  # only Q1-Q3 2020
    classificacoes={},
)
```

### 3. Use Async for Many Tables

If you're harvesting metadata for dozens of aggregates, `AsyncSidraClient` + `asyncio.gather` is significantly faster than a sync loop.

### 4. Stream Period-by-Period for Huge Tables

Tables like RAIS, Censo, and PAM municipal have millions of rows. Iterate periods individually and persist each chunk; never load the entire table into memory.

## Debugging

`sidra_fetcher` uses the stdlib `logging` module under the logger name `sidra_fetcher`. Enable debug output:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("sidra_fetcher").setLevel(logging.DEBUG)

from sidra_fetcher import SidraClient
with SidraClient() as client:
    rows = client.get("https://apisidra.ibge.gov.br/values/t/1620/n1/all/v/116/p/all/d/m")
# Logs the URL, request duration, and response size
```

## See Also

- [sidra-sql](sidra-sql.md) — Data warehousing & ETL motor that consumes `sidra-fetcher`
- [sidra-pipelines](sidra-pipelines.md) — Standard pipeline catalog
- [SIDRA Database (Portuguese)](https://sidra.ibge.gov.br/)
- [SIDRA API Help (Portuguese)](https://apisidra.ibge.gov.br/home/ajuda)
