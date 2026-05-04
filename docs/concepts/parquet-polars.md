# Parquet + Polars

Tutorial dedicado ao formato (Parquet) e biblioteca (Polars) que formam a espinha do processamento na plataforma. Os exemplos usam datasets dos três principais domínios — IBGE/SIDRA, RAIS/CAGED e Tesouro Direto — para mostrar que os mesmos padrões servem volumes muito diferentes.

## Por que Parquet?

Datasets brasileiros variam de pequenos (séries macroeconômicas SIDRA: KB) a massivos (RAIS anual: GB; Siscomex anual: dezenas de GB). CSV tem três limitações que aparecem rapidamente:

- carrega arquivo inteiro em memória,
- faz parse de todos os tipos a cada leitura,
- filtragem requer varredura completa.

Parquet contorna todos os três:

- **Armazenamento colunar** — lê apenas as colunas necessárias.
- **Comprimido** — ~80-90% menor que CSV equivalente.
- **Predicate pushdown** — filtros são aplicados antes da leitura completa.
- **Schema preservado** — sem adivinhação de tipos.

| Volume típico | CSV | Parquet | Compressão |
|---|---|---|---|
| Tesouro 20 anos | ~5 MB | ~1 MB | 80% |
| CAGED mensal | ~50 MB | ~6 MB | 88% |
| RAIS 2023 | ~850 MB | ~100 MB | 88% |
| Siscomex anual | ~500 MB | ~50 MB | 90% |

## Início rápido

### Converter CSV para Parquet

```python
import polars as pl

# RAIS bruto (CSV grande)
df = pl.read_csv("rais_2023.csv")
df.write_parquet("rais_2023.parquet")
# CSV: 850 MB → Parquet: 100 MB

# Tesouro bruto (CSV pequeno)
df = pl.read_csv("PrecoTaxaTesouroDireto.csv", separator=";")
df.write_parquet("tesouro_precos.parquet")
```

### Ler Parquet

```python
import polars as pl

# Leitura completa
df = pl.read_parquet("rais_2023.parquet")

# Apenas colunas necessárias (mais rápido)
df = pl.read_parquet(
    "rais_2023.parquet",
    columns=["employee_id", "salary", "sector"]
)

# Com filtro pushdown
df = pl.read_parquet(
    "rais_2023.parquet",
    filters=[("state", "==", "SP")]
)
```

## Workflows eficientes em memória

### Lazy evaluation: o caso de uso central

`pl.scan_parquet` (lazy) é quase sempre superior a `pl.read_parquet` (eager) para datasets grandes — o otimizador empurra filtros e seleções para a leitura.

```python
import polars as pl

# Pipeline lazy: filtra, seleciona, agrega — tudo otimizado em pass único
query = (
    pl.scan_parquet("rais_2023.parquet")
    .filter(pl.col("state") == "SP")
    .select(["employee_id", "salary", "sector"])
    .group_by("sector")
    .agg(pl.col("salary").mean().alias("avg_salary"))
)

result = query.collect()
# Polars otimiza:
# 1. Empurra filtro state == "SP" para a leitura
# 2. Seleciona colunas cedo (descarta o resto)
# 3. Agrega em pass único
```

### Streaming para volumes maiores que a RAM

```python
import polars as pl

# collect(streaming=True) processa em chunks — uso baixo de memória
result = (
    pl.scan_parquet("rais_2023.parquet")
    .group_by("state")
    .agg(pl.col("salary").mean())
    .collect(streaming=True)
)
```

## Tarefas comuns por domínio

### SIDRA: pivotar séries macroeconômicas

```python
import polars as pl

# Após buscar do SIDRA via sidra-fetcher e salvar como Parquet
gdp = pl.read_parquet("gdp_raw.parquet")

# Cast e enriquecimento explícitos
gdp = gdp.with_columns([
    pl.col("V").cast(pl.Float64, strict=False).alias("value"),
    pl.col("D2C").alias("period"),
]).select(["period", "value"])

gdp = gdp.with_columns(
    pl.col("value").pct_change().alias("growth")
)
```

### Tesouro: yield curve por título

```python
import polars as pl

prices = pl.read_parquet("data/tesouro/precos.parquet")

# Yield médio por título nos últimos 252 dias úteis
yield_curve = (
    prices.lazy()
    .filter(pl.col("data_base") >= pl.col("data_base").max() - pl.duration(days=365))
    .group_by("titulo")
    .agg([
        pl.col("taxa_compra_manha").mean().alias("yield_avg"),
        pl.col("preco_compra_manha").last().alias("preco_atual"),
    ])
    .sort("yield_avg")
    .collect()
)
```

### RAIS: emprego por estado e setor

```python
import polars as pl

df = pl.read_parquet("rais_2023.parquet")

summary = (
    df.group_by(["state", "sector"])
    .agg([
        pl.col("employee_id").count().alias("num_employees"),
        pl.col("salary").mean().alias("avg_salary"),
        pl.col("salary").median().alias("median_salary"),
        pl.col("salary").std().alias("salary_std"),
    ])
    .sort(["state", "sector"])
)

summary.write_parquet("employment_summary.parquet")
```

### Análise temporal multi-ano (RAIS)

```python
import polars as pl

# RAIS é anual (snapshot 31 dez). Combine para tendências:
years = []
for year in range(2021, 2024):
    df = pl.read_parquet(f"rais_{year}.parquet").with_columns(
        pl.lit(year).alias("year")
    )
    years.append(df)

combined = pl.concat(years, how="vertical")

by_year = (
    combined.lazy()
    .group_by(["year", "sector"])
    .agg([
        pl.col("employee_id").count().alias("employment"),
        pl.col("salary").mean().alias("avg_wage"),
    ])
    .sort(["sector", "year"])
    .with_columns([
        pl.col("employment").pct_change().over("sector").alias("employment_growth"),
        pl.col("avg_wage").pct_change().over("sector").alias("wage_growth"),
    ])
    .collect()
)
```

### Top-N: setores que mais empregam

```python
import polars as pl

df = pl.read_parquet("rais_2023.parquet")

top_sectors = (
    df.group_by("sector")
    .agg(pl.col("employee_id").count().alias("employment"))
    .sort("employment", descending=True)
    .head(10)
)
```

### Joins entre fontes (SIDRA × RAIS)

```python
import polars as pl

# PIB trimestral via SIDRA
gdp = pl.read_parquet("gdp.parquet")  # colunas: period, value

# Emprego anual via RAIS — agregado para join
rais = (
    pl.read_parquet("rais_2023.parquet")
    .group_by("state")
    .agg(pl.col("employee_id").count().alias("employment"))
)

# Tabelas externas (CNAE → setor humano)
sectors = pl.read_csv("cnae_sectors.csv")

enriched = rais.join(
    sectors,
    left_on="sector",
    right_on="sector_code",
    how="left",
)
```

## Schema e tipos

### Inspecionar schema

```python
import polars as pl

df = pl.read_parquet("rais_2023.parquet")
print(df.schema)
# {'employee_id': String,
#  'year': Int32,
#  'state': String,
#  'sector': String,
#  'salary': Float64,
#  'tenure_days': Int32}
```

### Cast de tipos

```python
import polars as pl

df = pl.read_parquet("rais_2023.parquet")

# Converter salário para inteiro (economiza espaço se aceitável perder centavos)
df = df.with_columns(pl.col("salary").cast(pl.Int32).alias("salary"))
df.write_parquet("rais_2023_int.parquet")
```

### Colunas computadas

```python
import polars as pl

df = pl.read_parquet("rais_2023.parquet")

df = df.with_columns([
    pl.when(pl.col("tenure_days") < 90).then(pl.lit("< 3 meses"))
    .when(pl.col("tenure_days") < 365).then(pl.lit("3-12 meses"))
    .when(pl.col("tenure_days") < 1825).then(pl.lit("1-5 anos"))
    .otherwise(pl.lit("> 5 anos"))
    .alias("tenure_group")
])
```

## Performance

### CSV vs. Parquet em arquivo de 1 GB

| Operação | Tempo |
|---|---|
| `read_csv` (eager) | ~12 s |
| `read_parquet` (eager) | ~0,3 s (40× mais rápido) |
| `scan_parquet().filter().collect()` | ~0,05 s (240× mais rápido) |

### Profile suas queries

```python
import time
import polars as pl

df = pl.read_parquet("rais_2023.parquet")

start = time.time()
result = (
    df.filter(pl.col("state") == "SP")
    .group_by("sector")
    .agg(pl.col("salary").mean())
)
print(f"Query levou {time.time() - start:.3f}s")
```

### Particionar arquivos grandes

```python
import polars as pl

df = pl.read_parquet("rais_combined.parquet")

# Escreve particionado por estado — leitura por partição fica trivial
df.write_parquet("rais_partitioned", partition_by="state")

# Lê apenas SP
sp = pl.read_parquet("rais_partitioned/state=SP")
```

## Padrões de produção

### Análise reproduzível com versionamento

```python
from pathlib import Path
from datetime import date
import polars as pl

data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

# Versione com data
filename = data_dir / f"rais_summary_{date.today():%Y_%m_%d}.parquet"

df = pl.read_parquet("rais_2023.parquet")
result = df.group_by("sector").agg(pl.col("salary").mean())
result.write_parquet(filename)
```

### Agregação incremental (CAGED mensal)

```python
from pathlib import Path
import polars as pl

data_dir = Path("caged_data")

# Agrega todos os meses disponíveis
dfs = [pl.read_parquet(p) for p in data_dir.glob("caged_2024_*.parquet")]
combined = pl.concat(dfs)

summary = combined.group_by("state").agg(pl.col("net_flow").sum())
summary.write_parquet("caged_2024_summary.parquet")
```

## Troubleshooting

### Falta de memória em arquivo grande

**Problema:** o arquivo não cabe em RAM.

**Solução:** filtragem na leitura ou streaming lazy.

```python
import polars as pl

# ❌ Carrega tudo
df = pl.read_parquet("huge_file.parquet")

# ✅ Filtra na leitura
df = pl.read_parquet("huge_file.parquet", filters=[("state", "==", "SP")])

# ✅ Ou lazy + streaming
df = pl.scan_parquet("huge_file.parquet").filter(pl.col("state") == "SP").collect(streaming=True)
```

### Queries lentas

**Problema:** query mais lenta que o esperado.

**Solução:** lazy evaluation expõe otimizações.

```python
import polars as pl

# ❌ Eager (executa imediatamente, sem otimização global)
df = pl.read_parquet("file.parquet")
result = df.filter(pl.col("state") == "SP")

# ✅ Lazy (otimiza primeiro)
result = (
    pl.scan_parquet("file.parquet")
    .filter(pl.col("state") == "SP")
    .collect()
)
```

### Tipos errados no Parquet escrito

**Problema:** salário escrito como string em vez de float.

**Solução:** cast explícito antes de escrever.

```python
import polars as pl

df = pl.read_parquet("rais.parquet")
df = df.with_columns(pl.col("salary").cast(pl.Float64))
df.write_parquet("rais_fixed.parquet")
```

---

## Saiba mais

- [Padrões Práticos](padroes.md) — `Parquet em vez de CSV`, `Lazy evaluation`, `Memória para arquivos grandes`.
- [Princípios de Design](principios.md#performance) — por que Parquet é o default da plataforma.
- [Documentação Polars](https://pola-rs.github.io/) — referência oficial.
