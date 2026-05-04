# Arquitetura da Plataforma

Como a Plataforma Brasileira de Dados Públicos é organizada e como as partes se conectam. Esta página descreve a forma do sistema; os [Princípios de Design](principios.md) explicam **por que** ele tem essa forma.

## Visão de sistema

```mermaid
graph TD
    Sources["Fontes de Dados Governamentais<br/>(IBGE, Tesouro, Trabalho, Comércio, Saúde, Clima)"]

    Sources -->|IBGE SIDRA| SF["sidra-fetcher"]
    Sources -->|IBGE SIDRA| SQL["sidra-sql"]
    Sources -->|Tesouro Direto| TD["tddata"]
    Sources -->|RAIS/CAGED| PD["pdet-data"]
    Sources -->|Siscomex| CX["comexdown"]
    Sources -->|DATASUS| DS["datasus-fetcher"]
    Sources -->|INMET BDMEP| IN["inmet-bdmep-data"]

    SF --> Processing["Processamento & Transformação<br/>(Polars vetorial / Pandas)"]
    SQL --> Processing
    TD --> Processing
    PD --> Processing
    CX --> Processing
    DS --> Processing
    IN --> Processing

    Processing --> Storage["Armazenamento Estruturado"]
    Storage --> PQ["Arquivos Parquet<br/>(analítico)"]
    Storage --> PG["PostgreSQL<br/>(operacional)"]

    PQ --> Analytics["Analytics & BI<br/>(dashboards, ML, relatórios)"]
    PG --> Analytics
```

A plataforma é organizada em **quatro camadas**: extração, processamento, armazenamento, análise. Cada camada tem responsabilidades estritas — o que ela deve e o que ela **não** deve fazer.

## Camadas e responsabilidades

### Extração (`sidra-fetcher`, `tddata`, `pdet-data`, `comexdown`, `datasus-fetcher`, `inmet-bdmep-data`)

Obter dados de APIs/FTPs governamentais com confiabilidade.

**Faz:**

- Trata características das fontes (paginação, rate limits, retries, SSL).
- Normaliza formatos de data quando necessário para extração.
- Valida schema na origem.
- Exporta em formatos padrão (Parquet, DataFrame, CSV).

**Não faz:**

- Transforma dados analiticamente (responsabilidade do usuário).
- Faz suposições sobre uso downstream.
- Esconde falhas silenciosamente.

### Processamento (Polars, Pandas)

Transformação rápida e flexível.

- **Polars** — arquivos grandes, transformações complexas, lazy evaluation. Default da plataforma.
- **Pandas** — integração com bibliotecas estatísticas, funções customizadas, datasets menores.

### Armazenamento (Parquet, PostgreSQL)

Persistência eficiente e confiável.

| Critério | Parquet | PostgreSQL |
|---|---|---|
| Caso de uso | Análise, arquivamento | Operacional, dashboards ao vivo |
| Tamanho típico | TBs em disco | 100M+ linhas indexadas |
| Compressão | 80-90% vs. CSV | Moderada |
| Concorrência | Leitura única por arquivo | Multi-usuário ACID |
| Schema | Preservado | Estrito |
| Tempo real | Não | Sim |
| Custo de infra | Apenas arquivos | Instância de banco |

**Estratégia comum:** Parquet para histórico longo + PostgreSQL para últimos meses ao vivo. Arquive para Parquet quando dados saem da janela operacional.

### Análise (Jupyter, R, dashboards)

A camada que consome o resto. Fora do escopo da plataforma — você pluga sua ferramenta de BI/ciência de dados favorita nos arquivos Parquet ou no PostgreSQL.

## ETL vs. ELT

A plataforma adota predominantemente **ELT** (Extract → Load → Transform), não ETL clássico.

```mermaid
graph LR
    A[Dados brutos] --> B[Load<br/>armazenar como-é]
    B --> C[Raw Parquet]
    C --> D[Transform<br/>on-demand]
    D --> E[Análise]
```

| | ETL clássico | ELT (escolha da plataforma) |
|---|---|---|
| Onde transforma | Antes de armazenar | Depois de armazenar |
| Dados brutos | Descartados após transformação | Preservados |
| Re-transformar | Requer re-fetch | Trivial — leia o raw e reprocesse |
| Armazenamento | Menor | Maior (raw + processado) |
| Flexibilidade | Baixa | Alta |
| Quando usa ETL | Datasets pequenos com transformações estáveis | — |

Datasets brasileiros são grandes e fontes governamentais publicam revisões com frequência. Preservar o raw é essencial para reprodutibilidade e re-processamento sem custo de rede.

### Exemplo de ELT na prática

```python
import polars as pl
from sidra_fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao

# EXTRACT & LOAD: armazenar linhas brutas do SIDRA
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
    rows = client.get(param.url())  # list[dict]

pl.DataFrame(rows).write_parquet("gdp_raw.parquet")  # raw preservado

# TRANSFORM: on-demand, re-rodável sem re-fetch
gdp = pl.read_parquet("gdp_raw.parquet").with_columns(
    pl.col("V").cast(pl.Float64, strict=False).pct_change().alias("growth")
)
```

## Padrões de deployment

A plataforma suporta quatro padrões principais de deployment, do mais simples ao mais complexo.

### 1. Local development

```mermaid
graph TD
    A["Seu computador"] --> B["Extrair"]
    B --> C["Transformar"]
    C --> D["Arquivos Parquet"]
    D --> E["Jupyter / Script Python"]
```

**Melhor para:** análise exploratória, prototipagem, pesquisa acadêmica de uma pessoa.

### 2. Daily batch pipeline

```mermaid
graph TD
    A["Tarefa agendada<br/>(cron / orquestrador)"] --> B["Extrair dados recentes"]
    B --> C["Validar"]
    C --> D["Transformar"]
    D --> E["Adicionar ao armazenamento"]
    E --> F["PostgreSQL<br/>(aplicações)"]
    E --> G["Parquet<br/>(análise)"]
```

**Melhor para:** dados operacionais regulares, dashboards, relatórios diários/semanais.

### 3. Real-time streaming

```mermaid
graph TD
    A["API/FTP Governamental"] --> B["Monitorar novos dados"]
    B --> C["Validar"]
    C --> D["Transformar"]
    D --> E["Banco em tempo real"]
    E --> F["Dashboard ao vivo / alertas"]
```

**Melhor para:** vigilância (epidemiologia, monitoramento comercial, picos de preços). Raro — fontes brasileiras quase nunca publicam em tempo real.

### 4. Integração multi-fonte

```mermaid
graph TD
    A["Múltiplas APIs<br/>(IBGE, Tesouro, Trabalho, etc.)"] --> B["Extrair em paralelo"]
    B --> C["Unir por chaves comuns<br/>(data, geografia, setor)"]
    C --> D["Dataset unificado"]
    D --> E["Data warehouse / data lake"]
    E --> F["Analytics, ML, relatórios"]
```

**Melhor para:** análise macroeconômica, modelagem econométrica, dashboards integrados de política pública. Veja a [receita Análise Econômica Multi-Fonte](../cookbook/analise-economica-multi-fonte.md).

## Características de performance

### Tempo típico de extração

| Ferramenta | Tempo | Volume |
|---|---|---|
| `sidra-fetcher` (série única) | 5-10 s | 100-1 000 linhas |
| `sidra-fetcher` (varredura) | 30-60 s | 10k-100k linhas |
| `tddata` (todos os títulos) | 5-10 s | ~1 000 títulos |
| `pdet-data` (RAIS ano completo) | 30-60 s | 60M registros |
| `pdet-data` (CAGED mensal) | 5-10 s | 10k-100k linhas |
| `comexdown` (anual) | 10-20 s | 1M-10M transações |
| `datasus-fetcher` (doença/ano) | 5-15 s | 100k-1M registros |

### Compressão Parquet

| Dataset | CSV bruto | Parquet | Compressão |
|---|---|---|---|
| RAIS 2023 | ~850 MB | ~100 MB | 88% |
| Tesouro (20 anos) | ~5 MB | ~1 MB | 80% |
| CAGED mensal | ~50 MB | ~6 MB | 88% |
| Siscomex anual | ~500 MB | ~50 MB | 90% |

### Escalabilidade

**Para a maioria dos casos** (até bilhões de linhas):

- Parquet em disco escala para TBs facilmente.
- Polars processa arquivos maiores que a RAM via streaming.
- PostgreSQL lida com 100M+ linhas com indexação adequada.

**Para escala extrema** (petabytes):

- Data lake (S3 / object storage em nuvem).
- Processamento distribuído (Spark, Dask, DuckDB).
- Data warehouse cloud (BigQuery, Redshift, Snowflake).

## Exemplo: pipeline de análise econômica

Combinando IBGE + Tesouro num pipeline ELT canônico:

```python
import polars as pl
from sidra_fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao
from tddata.converter import convert_to_parquet

# 1. EXTRACT: cada ferramenta usa seu próprio padrão de acesso
gdp_param = Parametro(
    agregado="1620",
    territorios={"1": ["all"]},
    variaveis=["116"],
    periodos=[],
    classificacoes={},
    formato=Formato.A,
    decimais={"": Precisao.M},
)
with SidraClient(timeout=60) as client:
    gdp = pl.DataFrame(client.get(gdp_param.url()))

convert_to_parquet(src_dir="raw/tesouro", dest_dir="data/tesouro", dataset_type="precos")
bonds = pl.read_parquet("data/tesouro/precos.parquet")

# 2. TRANSFORM: Polars vetorizado
combined = gdp.join(bonds, on="date", how="inner").with_columns([
    pl.col("V").cast(pl.Float64, strict=False).pct_change().alias("gdp_growth"),
    pl.col("yield").pct_change().alias("yield_change"),
])

# 3. LOAD: dois destinos coexistindo (Parquet + PostgreSQL)
combined.write_parquet("gdp_bonds_analysis.parquet")
combined.write_database(
    "gdp_bonds",
    connection="postgresql://user:pass@host/db",
    if_table_exists="replace",
)

# 4. ANALYZE
print(combined.select(pl.corr("gdp_growth", "yield_change")))
```

## Integração com ferramentas externas

A camada de armazenamento é deliberadamente **agnóstica** — Parquet e PostgreSQL conectam-se com qualquer ferramenta padrão.

| Categoria | Ferramentas comuns |
|---|---|
| BI | Tableau, Power BI, Metabase (via PostgreSQL) |
| Notebooks | Jupyter, Quarto (lendo Parquet diretamente) |
| ML | Scikit-learn, XGBoost, Prophet, TensorFlow |
| Distribuído | Spark, Dask, DuckDB |
| Data warehouse | Snowflake, BigQuery, Redshift |
| Reverse ETL | Exportar insights de volta a sistemas operacionais |

---

## Saiba mais

- [Princípios de Design](principios.md) — por que o sistema é assim.
- [Padrões Práticos](padroes.md) — como aplicar os padrões em código.
- [Parquet + Polars](parquet-polars.md) — o tutorial sobre o formato/biblioteca centrais.
- [Cookbook](../cookbook/index.md) — receitas que combinam múltiplos domínios.
