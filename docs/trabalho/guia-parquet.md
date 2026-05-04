# Guia Parquet + Polars

Trabalhando com grandes datasets de trabalho eficientemente.

## Por Que Parquet?

Datasets de trabalho brasileiros são grandes:

- **RAIS 2023**: ~60 milhões de registros de emprego (~1 GB CSV bruto)
- **CAGED mensal**: ~500k-1M fluxos de trabalho por mês
- **Histórico**: 30-40 anos de dados = arquivos multi-GB

**CSV é lento**:

- Carrega arquivo inteiro em memória
- Faz parse de todos os tipos de dados
- Filtragem requer varredura de tabela completa

**Parquet é rápido**:

- Armazenamento colunar (lê apenas colunas necessárias)
- Comprimido (~80% de redução)
- Predicate pushdown (filtra antes de carregar)
- Schema preservado (sem adivinhação de tipos)

## Início Rápido

### Converter CSV para Parquet

```python
import polars as pl

# Ler CSV
df = pl.read_csv("rais_2023.csv")

# Escrever Parquet
df.write_parquet("rais_2023.parquet")

# Comparação de tamanho de arquivo:
# CSV: 850 MB
# Parquet: 120 MB (14% do original)
```

### Ler Parquet

```python
import polars as pl

# Leitura completa
df = pl.read_parquet("rais_2023.parquet")

# Colunas seletivas (mais rápido)
df = pl.read_parquet(
    "rais_2023.parquet",
    columns=["employee_id", "salary", "sector"]
)

# Com filtro
df = pl.read_parquet(
    "rais_2023.parquet",
    filters=[("state", "==", "SP")]
)
```

## Workflows Eficientes em Memória

### Streaming de Arquivos Grandes

Não carregue o arquivo inteiro — processe em batches:

```python
import polars as pl

# Modo stream: carregar em chunks
reader = pl.read_parquet(
    "rais_2023.parquet"
)

# Processar em batches
batch_size = 100000
for i in range(0, len(reader), batch_size):
    batch = reader[i:i+batch_size]
    
    # Processar batch
    result = batch.group_by("sector").agg(
        pl.col("salary").mean()
    )
    
    # Anexar ao arquivo
    result.write_parquet(f"output_{i}.parquet", append=True)
```

### Lazy Evaluation

Use lazy evaluation para otimizar consultas:

```python
import polars as pl

# Lazy (ainda não avaliado)
query = (
    pl.scan_parquet("rais_2023.parquet")
    .filter(pl.col("state") == "SP")
    .select(["employee_id", "salary", "sector"])
    .group_by("sector")
    .agg(pl.col("salary").mean())
)

# Coletar quando pronto
result = query.collect()

# Polars otimiza a consulta antes da execução:
# 1. Empurrar filtro para baixo (state == "SP")
# 2. Selecionar colunas cedo (descartar dados não utilizados)
# 3. Agregar eficientemente
```

## Tarefas Comuns

### Filtrar por Múltiplos Critérios

```python
import polars as pl

# Ler com filtros
df = pl.read_parquet(
    "rais_2023.parquet",
    filters=[
        ("state", "in", ["SP", "RJ", "MG"]),
        ("salary", ">", 2000)
    ]
)

# Resultado: Apenas linhas correspondentes carregadas
```

### Group and Aggregate

```python
import polars as pl

df = pl.read_parquet("rais_2023.parquet")

# Emprego por estado e setor
summary = (
    df.group_by(["state", "sector"])
    .agg([
        pl.col("employee_id").count().alias("num_employees"),
        pl.col("salary").mean().alias("avg_salary"),
        pl.col("salary").median().alias("median_salary"),
        pl.col("salary").std().alias("salary_std")
    ])
    .sort("state", "sector")
)

print(summary)
summary.write_parquet("employment_summary.parquet")
```

### Time Series Analysis

RAIS is annual (December 31 snapshot). For trends:

```python
import polars as pl

# Combinar múltiplos anos
data_2021 = pl.read_parquet("rais_2021.parquet")
data_2022 = pl.read_parquet("rais_2022.parquet")
data_2023 = pl.read_parquet("rais_2023.parquet")

combined = pl.concat([data_2021, data_2022, data_2023])

# Agregar por ano
by_year = (
    combined
    .with_columns(pl.lit(2021, 2022, 2023).alias("year"))  # Adicionar ano se não presente
    .group_by(["year", "sector"])
    .agg([
        pl.col("employee_id").count().alias("employment"),
        pl.col("salary").mean().alias("avg_wage")
    ])
)

# Calcular crescimento
by_year = by_year.sort("year")
by_year = by_year.with_columns([
    pl.col("employment").pct_change().alias("employment_growth"),
    pl.col("avg_wage").pct_change().alias("wage_growth")
])

print(by_year)
```

### Top-N Queries

Find top sectors by employment:

```python
import polars as pl

df = pl.read_parquet("rais_2023.parquet")

# Top 10 setores por emprego
top_sectors = (
    df.group_by("sector")
    .agg(pl.col("employee_id").count().alias("employment"))
    .sort("employment", descending=True)
    .head(10)
)

print(top_sectors)
```

### Join Multiple Files

Combine RAIS with external data:

```python
import polars as pl

# RAIS employment
rais = pl.read_parquet("rais_2023.parquet")

# Dados externos (metadados de setor)
sector_info = pl.read_csv("sectors.csv")

# Unir
enriched = rais.join(
    sector_info,
    left_on="sector",
    right_on="sector_code",
    how="left"
)

# Now have sector names, classifications, etc.
print(enriched.select(["sector", "sector_name", "salary"]).head())
```

## Schema Management

### Inspect Parquet Schema

```python
import polars as pl

# Get schema
df = pl.read_parquet("rais_2023.parquet")
print(df.schema)

# Output:
# {'employee_id': String,
#  'year': Int32,
#  'state': String,
#  'sector': String,
#  'occupation': String,
#  'education': String,
#  'salary': Float64,
#  'tenure_days': Int32}
```

### Cast Types

```python
import polars as pl

df = pl.read_parquet("rais_2023.parquet")

# Converter salário para inteiro (economizar espaço)
df = df.with_columns([
    pl.col("salary").cast(pl.Int32).alias("salary")
])

# Save with new schema
df.write_parquet("rais_2023_int.parquet")
```

### Add Computed Columns

```python
import polars as pl

df = pl.read_parquet("rais_2023.parquet")

# Adicionar grupos de tempo de serviço
df = df.with_columns([
    pl.when(pl.col("tenure_days") < 90)
    .then("< 3 months")
    .when(pl.col("tenure_days") < 365)
    .then("3-12 months")
    .when(pl.col("tenure_days") < 1825)
    .then("1-5 years")
    .otherwise("> 5 years")
    .alias("tenure_group")
])

df.write_parquet("rais_2023_with_tenure_group.parquet")
```

## Otimização de Performance

### Comparação 1: CSV vs Parquet

**Leitura CSV** (arquivo de 1 GB):
```
Tempo: 12 segundos
```

**Leitura Parquet** (mesmos dados):
```
Tempo: 0.3 segundos (40x mais rápido)
```

**Parquet com filtro**:
```
Tempo: 0.05 segundos (240x mais rápido)
```

### Perfil Suas Queries

```python
import polars as pl
import time

df = pl.read_parquet("rais_2023.parquet")

# Cronometrize suas operações
start = time.time()

result = (
    df
    .filter(pl.col("state") == "SP")
    .group_by("sector")
    .agg(pl.col("salary").mean())
)

elapsed = time.time() - start
print(f"Query levou {elapsed:.3f} segundos")
```

### Particionar Arquivos Grandes

Armazene arquivos Parquet por partição (ex: por ano ou estado):

```python
import polars as pl
from pathlib import Path

df = pl.read_parquet("rais_combined.parquet")

# Escrever particionado por estado
(
    df
    .with_columns(pl.col("state").alias("partition_state"))
    .write_parquet(
        "rais_partitioned",
        partition_by="partition_state"
    )
)

# Ler apenas partição específica
sp_data = pl.read_parquet("rais_partitioned/partition_state=SP")
```

## Padrões Comuns

### Análise Reproduzível

```python
import polars as pl
from pathlib import Path

# Versione seus arquivos parquet
today = Path.cwd().parent / "data"
today.mkdir(exist_ok=True)

# Salvar com timestamp
timestamp = "2024_01_15"
filename = today / f"rais_analysis_{timestamp}.parquet"

df = pl.read_parquet("rais_2023.parquet")
result = df.group_by("sector").agg(pl.col("salary").mean())

result.write_parquet(filename)

# Carregue dados consistentes depois
result = pl.read_parquet(filename)
```

### Agregação Incremental

Processe dados CAGED mensais conforme chegam:

```python
import polars as pl
from pathlib import Path

data_dir = Path("caged_data")

# Agregue todos meses disponíveis
dfs = []
for parquet_file in data_dir.glob("caged_2024_*.parquet"):
    df = pl.read_parquet(parquet_file)
    dfs.append(df)

combined = pl.concat(dfs)

# Agregue uma vez, salve
summary = combined.group_by("state").agg(
    [pl.col("net_flow").sum()]
)

summary.write_parquet("caged_2024_summary.parquet")
```

## Resolução de Problemas

### Falta de Memória em Arquivo Grande

**Problema**: Arquivo é muito grande para carregar completamente

**Solução**: Use filtragem na leitura:

```python
import polars as pl

# Em vez de:
df = pl.read_parquet("huge_file.parquet")  # Crash

# Use filtro:
df = pl.read_parquet(
    "huge_file.parquet",
    filters=[("state", "==", "SP")]
)  # Rápido, pouca memória
```

### Queries Lentas em Parquet

**Problema**: Query é mais lenta que o esperado

**Solução**: Use lazy evaluation:

```python
import polars as pl

# Eager (executa imediatamente)
df = pl.read_parquet("file.parquet")
result = df.filter(...)

# Lazy (otimiza primeiro)
result = pl.scan_parquet("file.parquet").filter(...).collect()
```

### Type Mismatch na Escrita

**Problema**: Salário escrito como string em vez de float

**Solução**: Fazer cast antes de escrever:

```python
import polars as pl

df = pl.read_parquet("rais.parquet")

# Corrigir tipos
df = df.with_columns([
    pl.col("salary").cast(pl.Float64)
])

df.write_parquet("rais_fixed.parquet")
```

## Saiba Mais

- [Ferramenta pdet-data](pdet-data.md)
- [Documentação Polars](https://pola-rs.github.io/)
