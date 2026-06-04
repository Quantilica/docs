# Arquitetura do Ecossistema

Como o Ecossistema Quantilica é organizado e como as partes se conectam. Esta página descreve a forma do sistema; os [Princípios de Design](principios.md) explicam **por que** ele tem essa forma.

## Visão de sistema

```mermaid
graph TD
    Sources["Fontes de Dados Governamentais<br/>(IBGE, Tesouro/STN, BCB, Trabalho, Comércio, Saúde, Clima)"]

    Sources -->|IBGE SIDRA| SF["sidra-fetcher"]
    Sources -->|IBGE SIDRA| SQL["sidra-sql"]
    Sources -->|Tesouro Direto| TD["tesouro-direto-fetcher"]
    Sources -->|RTN/STN| RTN["rtn-fetcher"]
    Sources -->|BCB SGS| BCB["bcb-sgs-fetcher"]
    Sources -->|BCB SGS| BCBSQL["bcb-sgs-sql"]
    Sources -->|RAIS/CAGED| PD["pdet-fetcher"]
    Sources -->|Siscomex| CX["comex-fetcher"]
    Sources -->|DATASUS| DS["datasus-fetcher"]
    Sources -->|INMET BDMEP| IN["inmet-fetcher"]

    SF --> Processing["Processamento & Transformação<br/>(Polars vetorial / Pandas)"]
    SQL --> Processing
    TD --> Processing
    RTN --> Processing
    BCB --> Processing
    BCBSQL --> Processing
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

O ecossistema é organizado em **quatro camadas**: extração, processamento, armazenamento, análise. Cada camada tem responsabilidades estritas.

## Fundações Técnicas

A infraestrutura da Quantilica repousa sobre o princípio da **Neutralidade de Domínio**. O pacote `quantilica-core` não possui conhecimento sobre fontes específicas (SIDRA, DATASUS, etc); ele lida exclusivamente com abstrações técnicas.

A fundação é dividida em dois pilares para equilibrar leveza e poder:

1.  **`quantilica-core` (Infraestrutura de I/O):** Base estável e sem dependências binárias pesadas. Contém clientes HTTP/FTP resilientes, gerenciamento de manifestos (proveniência) e interface de storage.
2.  **`quantilica-analytics` (Data Access Layer):** Camada analítica que depende do Polars. Responsável por leitura multi-formato, conversão otimizada para Parquet e contratos de dados (schemas).

### Tipos de Pacotes no Ecossistema

| Tipo | Padrão Esperado | Exemplos |
| :--- | :--- | :--- |
| **Client (Fetcher)** | Biblioteca Python + CLI simples | `sidra-fetcher`, `datasus-fetcher`, `bcb-sgs-fetcher` |
| **Pipeline** | Motor ETL + definições TOML/SQL | `sidra-sql`, `bcb-sgs-sql`, `sidra-pipelines` |
| **Data Package** | Download + Transformação + Export | `rtn-fetcher`, `inmet-fetcher` |
| **CLI Host** | CLI unificada com descoberta por entry points | `quantilica-cli` |

## Camadas e responsabilidades

### Extração (`sidra-fetcher`, `tesouro-direto-fetcher`, `rtn-fetcher`, `bcb-sgs-fetcher`, `pdet-fetcher`, `comex-fetcher`, `datasus-fetcher`, `inmet-fetcher`)

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

- **Polars** — arquivos grandes, transformações complexas, lazy evaluation. Default do ecossistema.
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

A camada que consome o resto. Fora do escopo do ecossistema — você pluga sua ferramenta de BI/ciência de dados favorita nos arquivos Parquet ou no PostgreSQL.

## ETL vs. ELT

O ecossistema adota predominantemente **ELT** (Extract → Load → Transform), não ETL clássico.

```mermaid
graph LR
    A[Dados brutos] --> B[Load<br/>armazenar como-é]
    B --> C[Raw Parquet]
    C --> D[Transform<br/>on-demand]
    D --> E[Análise]
```

| | ETL clássico | ELT (escolha do ecossistema) |
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
from sidra_fetcher.fetcher import SidraClient
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

O ecossistema suporta quatro padrões principais de deployment, do mais simples ao mais complexo.

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
| `tesouro-direto-fetcher` (todos os títulos) | 5-10 s | ~1 000 títulos |
| `pdet-fetcher` (RAIS ano completo) | 30-60 s | 60M registros |
| `pdet-fetcher` (CAGED mensal) | 5-10 s | 10k-100k linhas |
| `comex-fetcher` (anual) | 10-20 s | 1M-10M transações |
| `datasus-fetcher` (doença/ano) | 5-15 s | 100k-1M registros |

### Compressão Parquet

Compressão típica: 80-90% vs. CSV — RAIS 2023 de 850 MB cabe em 100 MB de Parquet. Volumes completos em [Parquet + Polars](parquet-polars.md#por-que-parquet).

### Escalabilidade

Parquet em disco e Polars escalam bem sem infraestrutura adicional:

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
import asyncio
from pathlib import Path
import polars as pl
from sidra_fetcher.fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao
from tesouro_direto_fetcher import downloader, reader
from tesouro_direto_fetcher.constants import Column as C

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
    gdp_rows = client.get(gdp_param.url())

tesouro_dir = Path("raw/tesouro")
asyncio.run(downloader.download(
    dest_dir=tesouro_dir,
    dataset_id="taxas-dos-titulos-ofertados-pelo-tesouro-direto",
))
bonds_csv = max(tesouro_dir.glob("taxas-*.csv"), key=lambda p: p.stat().st_mtime)
bonds = reader.read_prices(bonds_csv)

# 2. TRANSFORM: Polars vetorizado, cada fonte em seu próprio frame
gdp = (
    pl.DataFrame(gdp_rows[1:])  # linha 0 é cabeçalho descritivo
    .select(
        pl.col("D3C").alias("periodo"),
        pl.col("V").cast(pl.Float64, strict=False).alias("pib"),
    )
    .drop_nulls("pib")
)

bonds_monthly = (
    bonds
    .with_columns(pl.col(C.REFERENCE_DATE.value).dt.truncate("1mo").alias("month"))
    .group_by("month")
    .agg(pl.col(C.BUY_YIELD.value).mean().alias("yield_avg"))
    .sort("month")
)

# 3. LOAD: dois destinos coexistindo (Parquet + PostgreSQL)
gdp.write_parquet("gdp_sidra.parquet")
bonds_monthly.write_parquet("bonds_monthly.parquet")
bonds_monthly.write_database(
    "bonds_monthly",
    connection="postgresql://user:pass@host/db",
    if_table_exists="replace",
)

# 4. ANALYZE
print(bonds_monthly.select(pl.col("yield_avg").mean()))
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

## Arquitetura de CLI

Cada fetcher pode ser usado como biblioteca Python, como ferramenta standalone ou como plugin integrado no hub central (`quantilica-cli`). Para suportar esses três casos sem sobrecarregar o usuário com dependências desnecessárias, o ecossistema adota uma **CLI Híbrida**:

### CLI Nativa (Leve)

- **Arquivo:** `src/<package_name>/cli.py`
- **Tecnologia:** `argparse` (biblioteca padrão do Python).
- **Dependências:** apenas `quantilica-core` e bibliotecas padrão.
- **Objetivo:** garantir que o pacote funcione em ambientes restritos, mantendo `pyproject.toml` limpo.

### Plugin para CLI Unificada (Rico)

- **Arquivo:** `src/<package_name>/plugin.py`
- **Tecnologia:** `typer` e `rich` (fornecidos pelo host, não declarados como dep do fetcher).
- **Objetivo:** UX superior com tabelas coloridas, painéis e subcomandos quando usada via `quantilica-cli`.

### Estado atual

| Projeto | CLI Nativa (`argparse`) | Plugin Typer (`plugin.py`) |
| :--- | :---: | :---: |
| `comex-fetcher` | Sim | Sim |
| `sidra-fetcher` | Sim | Sim |
| `datasus-fetcher` | Sim | Sim |
| `pdet-fetcher` | Sim | Sim |
| `rtn-fetcher` | Sim | Sim |
| `tesouro-direto-fetcher` | Sim | Sim |
| `inmet-fetcher` | Sim | Sim |
| `bcb-sgs-fetcher` | Sim | Sim |

Para diretrizes detalhadas de implementação, veja [Padronização de CLI](../normas/cli-fetchers.md).

---

## Saiba mais

- [Princípios de Design](principios.md) — por que o sistema é assim.
- [Padrões Práticos](padroes.md) — como aplicar os padrões em código.
- [Parquet + Polars](parquet-polars.md) — o tutorial sobre o formato/biblioteca centrais.
- [Cookbook](../cookbook/index.md) — receitas que combinam múltiplos domínios.
