# Receita: Análise Econômica Multi-Fonte

Combinar três fontes — IPCA do IBGE, yields do Tesouro Direto e salários da RAIS — para construir um painel macroeconômico básico. Esta receita demonstra **[Modularidade](../concepts/principios.md#modularidade)** em prática: três ferramentas independentes, sem dependências cruzadas, compostas num pipeline coerente.

## Objetivo

Responder à pergunta: **como yield real (yield nominal − inflação esperada) se relaciona com crescimento de salários reais ao longo do tempo?**

Para isso precisamos de:

- IPCA mensal acumulado em 12 meses → inflação realizada (proxy de expectativa).
- Yield médio mensal da NTN-B (indexada ao IPCA) e LTN (prefixada).
- Salário médio anual RAIS, deflacionado pelo IPCA.

## Pré-requisitos

```bash
pip install sidra-fetcher tddata pdet-data polars
```

Para `pdet-data`, é necessário ter o binário `7z` no `PATH` (descompressão `.7z`).

## Pipeline

### 1. Buscar IPCA via SIDRA

```python
import polars as pl
from sidra_fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao

# IPCA: tabela 1737, variável 2266 (variação mensal)
ipca_param = Parametro(
    agregado="1737",
    territorios={"1": ["all"]},
    variaveis=["2266"],
    periodos=[],
    classificacoes={},
    formato=Formato.A,
    decimais={"": Precisao.M},
)

with SidraClient(timeout=60) as client:
    rows = client.get(ipca_param.url())

ipca = (
    pl.DataFrame(rows)
    .select([
        pl.col("D2C").alias("month_str"),  # YYYYMM
        pl.col("V").cast(pl.Float64, strict=False).alias("ipca_pct"),
    ])
    .with_columns(
        pl.col("month_str").str.strptime(pl.Date, "%Y%m").alias("month")
    )
    .drop("month_str")
    .sort("month")
    .with_columns(
        # IPCA acumulado em 12 meses (rolling product)
        ((pl.col("ipca_pct") / 100 + 1).log().rolling_sum(12).exp() - 1).alias("ipca_12m")
    )
)

ipca.write_parquet("data/ipca.parquet")
print(f"IPCA: {len(ipca)} meses")
```

### 2. Buscar yields do Tesouro Direto

```python
import asyncio
from pathlib import Path
from tddata import downloader, reader

async def fetch_treasury():
    await downloader.download(
        Path("data/tesouro"),
        dataset_id="taxas-dos-titulos-ofertados-pelo-tesouro-direto",
        max_concurrency=3,
    )

asyncio.run(fetch_treasury())

# Ler CSV de preços/taxas em DataFrame Polars tipado
prices_csv = next(Path("data/tesouro").glob("taxas-dos-titulos*.csv"))
prices = reader.read_prices(prices_csv)

# Yield mensal médio por tipo de título (NTN-B prefixados longos vs LTN)
yields_monthly = (
    prices.lazy()
    .with_columns([
        pl.col("data_base").dt.truncate("1mo").alias("month"),
    ])
    .filter(pl.col("tipo_titulo").is_in(["Tesouro IPCA+", "Tesouro Prefixado"]))
    .group_by(["month", "tipo_titulo"])
    .agg(pl.col("taxa_compra_manha").mean().alias("yield_avg"))
    .collect()
    .pivot(values="yield_avg", index="month", on="tipo_titulo")
    .rename({
        "Tesouro IPCA+": "yield_real_ntnb",
        "Tesouro Prefixado": "yield_nominal_ltn",
    })
    .sort("month")
)

yields_monthly.write_parquet("data/yields.parquet")
print(f"Yields: {len(yields_monthly)} meses")
```

### 3. Buscar salários médios RAIS

```python
from pathlib import Path
from pdet_data import connect, fetch_rais, convert_rais

# Fetch + convert idempotentes; primeira execução leva tempo, demais são quase instantâneas
ftp = connect()
try:
    fetch_rais(ftp=ftp, dest_dir=Path("data/rais/raw"))
finally:
    ftp.close()

convert_rais(Path("data/rais/raw"), Path("data/rais/parquet"))

# Salário médio anual (todos os vínculos)
years = []
for year in range(2010, 2024):
    parquet_path = Path(f"data/rais/parquet/rais-vinculos/{year}.parquet")
    if not parquet_path.exists():
        continue
    df = (
        pl.scan_parquet(parquet_path)
        .filter(pl.col("vl_remun_medio_nominal") > 0)
        .select([
            pl.lit(year).alias("year"),
            pl.col("vl_remun_medio_nominal").mean().alias("avg_wage_nominal"),
        ])
        .collect()
    )
    years.append(df)

wages_annual = pl.concat(years, how="vertical").sort("year")
wages_annual.write_parquet("data/wages.parquet")
print(f"Salários: {len(wages_annual)} anos")
```

### 4. Combinar e analisar

```python
ipca = pl.read_parquet("data/ipca.parquet")
yields = pl.read_parquet("data/yields.parquet")
wages = pl.read_parquet("data/wages.parquet")

# Join IPCA + yields por mês
monthly = ipca.join(yields, on="month", how="inner")

# Yield real implícito da LTN: (1 + yield_nominal) / (1 + ipca_12m) - 1
monthly = monthly.with_columns(
    ((1 + pl.col("yield_nominal_ltn") / 100) /
     (1 + pl.col("ipca_12m")) - 1).alias("yield_real_implicit")
)

# Spread NTN-B vs yield real implícito (prêmio de inflação)
monthly = monthly.with_columns(
    (pl.col("yield_real_ntnb") / 100 - pl.col("yield_real_implicit")).alias("inflation_premium")
)

# Deflacionar salários: precisamos de IPCA acumulado por ano até dezembro
ipca_dec = (
    ipca.filter(pl.col("month").dt.month() == 12)
    .with_columns(pl.col("month").dt.year().alias("year"))
    .select(["year", "ipca_12m"])
)

wages_real = (
    wages.join(ipca_dec, on="year", how="inner")
    .with_columns(
        # Deflate to base year (mais recente)
        (pl.col("avg_wage_nominal") / (1 + pl.col("ipca_12m"))).alias("avg_wage_real")
    )
    .with_columns(
        pl.col("avg_wage_real").pct_change().alias("real_wage_growth")
    )
)

print("=== Yield real implícito vs. NTN-B (média mensal) ===")
print(monthly.select([
    pl.col("yield_real_ntnb").mean(),
    (pl.col("yield_real_implicit") * 100).mean().alias("yield_real_implicit_pct"),
    (pl.col("inflation_premium") * 100).mean().alias("inflation_premium_pct"),
]))

print("\n=== Crescimento real de salários (RAIS) ===")
print(wages_real.select(["year", "avg_wage_real", "real_wage_growth"]))

# Persistir resultado integrado
monthly.write_parquet("data/macro_monthly.parquet")
wages_real.write_parquet("data/wages_real.parquet")
```

## O que esta receita demonstra

- **Modularidade**: três pacotes (`sidra-fetcher`, `tddata`, `pdet-data`) sem dependências cruzadas, compostos em camada do usuário.
- **Idempotência**: as três etapas de extração são seguras para re-rodar — `sidra-fetcher` cacheia via `Last-Modified`, `tddata.downloader` verifica `last_modified` no CKAN, `pdet-data fetch` pula `.7z` já baixados.
- **Performance**: tudo em Polars com lazy evaluation; mesmo cobrindo 14 anos da RAIS (~700M registros), agregações finais rodam em segundos.
- **Reprodutibilidade**: cada estágio salva um Parquet intermediário, então re-análises não exigem re-fetch.

## Variações

- **Substituir RAIS por CAGED** se quiser frequência mensal em vez de anual. Use `convert_caged` em vez de `convert_rais`.
- **Adicionar PIB**: tabela SIDRA 1620, variável 116. Útil para testar correlação yield vs. ciclo econômico.
- **Recortar por estado/setor**: filtre RAIS por `cnae_code` ou `state` antes de agregar.

## Saiba mais

- **[sidra-fetcher](../ibge/sidra-fetcher.md)** — SDK SIDRA detalhado.
- **[tddata](../tesouro/tddata.md)** — análise Tesouro Direto.
- **[pdet-data](../trabalho/pdet-data.md)** — RAIS/CAGED.
- **[Cálculo de Retornos](../tesouro/calculo-retornos.md)** — matemática por trás de yield real, duration, FIFO.
- **[Arquitetura da Plataforma](../concepts/arquitetura.md)** — padrão multi-fonte ELT.
