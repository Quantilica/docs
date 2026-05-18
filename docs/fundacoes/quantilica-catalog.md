---
title: quantilica-catalog
description: Modelo de observação canônico e catálogo unificado para cruzamento de dados de múltiplas fontes brasileiras.
---

# `quantilica-catalog`

Modelo de dados canônico e adaptadores para normalizar observações de diferentes fontes num esquema unificado. Resolve o problema central do cruzamento de dados: cada fonte usa estrutura, nomes de colunas e granularidade geográfica diferentes.

> **O problema:** SIDRA usa `localidade`, BCB-SGS não tem geografia, INMET usa código de estação. Para cruzar um índice BCB com dados climáticos do INMET, você precisa de um modelo comum. `quantilica-catalog` fornece esse modelo.

## Instalação

```bash
uv add "quantilica-catalog @ git+https://github.com/Quantilica/quantilica-catalog.git"
```

## O Modelo: Star Schema

O catálogo organiza os dados em um star schema com uma tabela fato e dimensões de suporte:

```
fact_observation  (o que? quando? onde? quanto?)
├── dim_indicator      — metadados do indicador (nome, categoria, frequência)
├── dim_geo_entity     — entidades geográficas (estados, municípios, estações)
├── dim_geo_relationship — hierarquias entre entidades geográficas
└── dim_geo_code       — códigos externos (IBGE, INMET, etc.)
```

## Tabela Fato: `fact_observation`

Cada linha responde: *qual foi o valor do indicador X no tempo T no lugar G?*

```python
from quantilica_catalog import OBSERVATION_CONTRACT
# Schema: indicator_id (Utf8), date (Date), geo_id (Utf8?),
#         value (Float64?), date_end (Date?)
```

| Campo | Tipo | Descrição |
|---|---|---|
| `indicator_id` | `Utf8` | `"fonte:id"` — ex.: `"bcb-sgs:433"`, `"sidra:1705:93"` |
| `date` | `Date` | Data de início da observação |
| `geo_id` | `Utf8?` | `null` para séries nacionais sem desagregação geográfica |
| `value` | `Float64?` | Valor numérico |
| `date_end` | `Date?` | Data de fim (séries com intervalo, ex.: trimestres móveis) |

## Adaptadores

Os adaptadores convertem DataFrames no formato de cada fetcher para o formato canônico:

```python
from quantilica_catalog.adapters.bcb_sgs import to_observations as sgs_obs
from quantilica_catalog.adapters.sidra import to_observations as sidra_obs
import polars as pl

# BCB-SGS → observações canônicas (sem geo_id — série nacional)
df_sgs = pl.read_parquet("series_433.parquet")  # formato SGS_CONTRACT
obs = sgs_obs(df_sgs)
# indicator_id="bcb-sgs:433", geo_id=null
```

Adaptadores disponíveis e formato do `indicator_id` gerado:

| Módulo | Fonte | Formato do `indicator_id` |
|---|---|---|
| `adapters.bcb_sgs` | BCB-SGS | `"bcb-sgs:{series_id}"` |
| `adapters.rtn` | Tesouro Nacional RTN | `"rtn:{planilha}:{coluna}"` |
| `adapters.inmet` | INMET BDMEP | `"inmet:{variável}"` |
| `adapters.tesouro_direto` | Tesouro Direto | `"td:{tipo_titulo}"` |
| `adapters.sidra` | IBGE SIDRA | `"sidra:{agregado_id}:{variavel_id}"` (ou `:{categoria_ids}` se classificado) |

!!! note "SIDRA com categorias"
    Quando o agregado SIDRA tem classificações (ex.: desemprego por faixa etária), o `indicator_id` inclui os IDs das categorias separados por `|`: `"sidra:1705:93:49223|49702"`.

## Dimensão de Indicadores

```python
from quantilica_catalog import IndicatorEntry, DataCategory, Frequency, entries_to_frame

entries = [
    IndicatorEntry(
        indicator_id="bcb-sgs:433",
        source_id="bcb",
        source_dataset_id="sgs",
        name="IPCA — Variação mensal",
        category=DataCategory.PRICES,
        unit="%",
        frequency=Frequency.MONTHLY,
    ),
]

dim_df = entries_to_frame(entries)
```

**Categorias** (`DataCategory`): `monetary`, `fiscal`, `financial`, `climate`, `labor`, `trade`, `health`, `demographic`, `economic`, `prices`.

**Frequências** (`Frequency`): `hourly`, `daily`, `weekly`, `monthly`, `quarterly`, `semi_annual`, `rolling_quarterly`, `yearly`, `multi_year`, `irregular`.

## Dimensão Geográfica

### Entidades — `dim_geo_entity`

```python
from quantilica_catalog import GeoEntityEntry, GeoType, state_id, municipality_id

entries = [
    GeoEntityEntry(geo_id=state_id("SP"), geo_type=GeoType.TERRITORY, name="São Paulo"),
    GeoEntityEntry(geo_id=municipality_id("3550308"), geo_type=GeoType.TERRITORY, name="São Paulo"),
]
```

**Construtores de `geo_id`:**

| Função | Exemplo de saída |
|---|---|
| `country_id()` | `"BR"` |
| `region_id("1")` | `"BR:R:1"` |
| `state_id("SP")` | `"BR:SP"` |
| `mesoregion_id("3515")` | `"BR:MR:3515"` |
| `microregion_id("35061")` | `"BR:MCR:35061"` |
| `municipality_id("3550308")` | `"BR:M:3550308"` |
| `district_id("355030805")` | `"BR:D:355030805"` |
| `census_sector_id("350030805000001")` | `"BR:CS:350030805000001"` |
| `station_id("INMET", "A701")` | `"INMET:A701"` |

### Hierarquias — `dim_geo_relationship`

```python
from quantilica_catalog import GeoRelationshipEntry, RelType, GeoSystem

rel = GeoRelationshipEntry(
    from_geo_id=municipality_id("3550308"),
    to_geo_id=state_id("SP"),
    rel_type=RelType.ADMINISTRATIVE_PARENT,
    system=GeoSystem.IBGE_TRADITIONAL,
)
```

**Tipos de relação** (`RelType`): `administrative_parent`, `contains`, `overlaps`, `borders`.

**Sistemas** (`GeoSystem`): `ibge_traditional`, `ibge_rgint`, `ibge_census`, `datasus_health`, `ana_hydrographic`, `inmet`.

### Códigos externos — `dim_geo_code`

```python
from quantilica_catalog import GeoCodeEntry

code = GeoCodeEntry(geo_id=state_id("SP"), system="ibge", code="35")
```

## DDL PostgreSQL

Para criar as tabelas de dimensão geográfica num banco PostgreSQL:

```python
from sqlalchemy import text
from quantilica_catalog.sql.ddl import CREATE_ALL_GEO_TABLES

with engine.connect() as conn:
    conn.execute(text(CREATE_ALL_GEO_TABLES))
    conn.commit()
```

Cria `dim_geo_entity`, `dim_geo_relationship` e `dim_geo_code` com índices otimizados para lookup por código e consultas de hierarquia.

## Por que um modelo canônico?

Sem `quantilica-catalog`, cruzar IPCA (BCB-SGS) com temperatura por estado (INMET) exige renomear colunas de cada fonte, decidir um identificador de indicador ad hoc e alinhar a granularidade geográfica manualmente.

O catálogo faz isso **uma vez**, tornando os dados inter-operáveis por construção: um `JOIN` em `indicator_id` + `geo_id` + `date` une qualquer par de fontes.

## Saiba Mais

- [quantilica-io](quantilica-io.md) — os `DataContract`s em que o catálogo se apoia
- [Proveniência & Manifestos](../concepts/proveniencia.md) — rastreabilidade dos dados
- [Cookbook — Análise econômica multi-fonte](../cookbook/analise-economica-multi-fonte.md)

## Repositório

[github.com/Quantilica/quantilica-catalog](https://github.com/Quantilica/quantilica-catalog) — MIT.
