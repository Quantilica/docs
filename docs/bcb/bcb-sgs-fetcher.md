---
title: bcb-sgs-fetcher — Séries temporais do Banco Central do Brasil
description: Coleta séries temporais do SGS/BCB via API JSON e scraping HTML — câmbio, SELIC, CDI, IPCA e centenas de outros indicadores macroeconômicos.
---

# bcb-sgs-fetcher

!!! warning "Pegadinhas da fonte oficial"
    - **Séries diárias:** a API `/dados` não retorna o histórico completo para séries de alta frequência. O fetcher usa uma estratégia retroativa ano a ano para contornar esse limite — espere múltiplas requisições ao baixar uma série diária longa.
    - **Metadados:** não existe API pública de metadados. A coleta exige scraping HTML com sessão stateful via `ScraperClient`. A sessão é gerenciada automaticamente, mas não é compatível com execução paralela.
    - **Séries desativadas:** séries encerradas pelo BCB ainda existem no SGS mas podem retornar conjuntos de dados parciais.

---

## O Que É

O **SGS** (Sistema Gerenciador de Séries Temporais) é o repositório oficial de indicadores macroeconômicos do Banco Central do Brasil. São mais de **17.000 séries**, muitas com histórico desde a década de 1980, organizadas em temas:

| Tema | Exemplos |
|---|---|
| Câmbio | USD/BRL, EUR/BRL, GBP/BRL |
| Juros | SELIC, CDI, TR, TBF |
| Inflação | IPCA, IPCA-15, IGP-M |
| Crédito | Estoque de crédito, inadimplência, spreads |
| Balanço de pagamentos | Conta corrente, investimento direto |
| Meios de pagamento | M1, M2, M3, M4 |
| Atividade econômica | IBC-Br, Resultado primário |

`bcb-sgs-fetcher` expõe dois clientes independentes: `SgsDataClient` para a API JSON pública e `ScraperClient` para os metadados via HTML.

---

## Instalação

```bash
# Workspace Quantilica
uv add bcb-sgs-fetcher

# Uso com quantilica-cli (plugin registrado automaticamente)
uv add quantilica-cli bcb-sgs-fetcher
```

O pacote registra o subcomando `bcb-sgs` na CLI do Quantilica via entry point:

```toml
[project.entry-points."quantilica.fetchers"]
bcb-sgs = "bcb_sgs_fetcher.plugin:app"
```

---

## CLI

Os comandos são agrupados em `series` (operações por série) e `catalogo`
(catálogo de metadados), disponíveis tanto pelo CLI standalone quanto pelo
`quantilica-cli`.

=== "quantilica-cli"

    ```bash
    # Dados históricos de câmbio USD/BRL (série 1, diária)
    quantilica bcb-sgs series sync 1 -f D -o ./dados

    # Dados da taxa SELIC mensal
    quantilica bcb-sgs series sync 11 -f M -o ./dados

    # Metadados de uma série
    quantilica bcb-sgs series metadata 433 -o ./dados

    # Buscar séries por texto
    quantilica bcb-sgs series search "câmbio dólar"

    # Sincronizar o catálogo completo de metadados
    quantilica bcb-sgs catalogo sync
    ```

=== "CLI standalone"

    ```bash
    # Dados históricos de câmbio USD/BRL (série 1, diária)
    bcb-sgs-fetcher series sync 1 --frequency D --output ./dados

    # Dados da taxa SELIC mensal
    bcb-sgs-fetcher series sync 11 --frequency M --output ./dados

    # Metadados de uma série
    bcb-sgs-fetcher series metadata 433 --output ./dados

    # Buscar séries por texto
    bcb-sgs-fetcher series search "câmbio dólar"

    # Sincronizar o catálogo completo de metadados
    bcb-sgs-fetcher catalogo sync
    ```

### Opções do comando `series sync`

| Opção | Padrão | Descrição |
|---|---|---|
| `series_id` | _(obrigatório)_ | ID numérico da série no SGS |
| `-f / --frequency` | _(detectado automaticamente)_ | Periodicidade: `D` diária, `S` semanal, `M` mensal, `T` trimestral, `Qd` quadrimestral, `A` anual |
| `-o / --output` | `/data/bcb-sgs` | Diretório de saída |
| `--verbose` | `False` | Logs detalhados |

!!! info "Periodicidade `D` (diária)"
    Ao passar `-f D`, o fetcher ativa a estratégia retroativa ano a ano. Não use `-f D` para séries de periodicidade mensal ou maior — a detecção automática é suficiente nesses casos.

---

## API Python

### Buscar dados de uma série

```python
from bcb_sgs_fetcher import SgsDataClient

# USD/BRL — série 1, periodicidade diária
with SgsDataClient() as client:
    points = client.fetch_series_data(
        series_id=1,
        frequency_acronym="D",  # ativa estratégia retroativa
    )

for p in points[:5]:
    print(p.date, p.value)
# 2025-01-02 5.8734
# 2025-01-03 5.9210
# ...
```

### Buscar metadados

```python
from bcb_sgs_fetcher import (
    ScraperClient,
    parse_metadata_basic,
    parse_metadata_full,
)

with ScraperClient() as scraper:
    htmls = scraper.request_metadata_html(series_id=1)

basic = parse_metadata_basic(htmls["basic"])
full = parse_metadata_full(htmls["full"])

print(basic.name)           # "Taxa de câmbio - Livre - Dólar americano (compra)"
print(basic.frequency)      # "Diária"
print(basic.unit)           # "Real/Dólar americano"
print(basic.start_date)     # datetime.date(1984, 11, 28)
print(full.last_update)     # datetime.date(2025, 5, 12)
```

### Buscar séries por texto

```python
from bcb_sgs_fetcher import ScraperClient, extract_table_data
from bs4 import BeautifulSoup

with ScraperClient() as scraper:
    html = scraper.search_series_by_text("taxa selic")

soup = BeautifulSoup(html, "lxml")
rows = extract_table_data(soup.find("table"))

for row in rows:
    print(row.series_id, row.name_index, row.frequency_acronym)
```

### Navegar a árvore de grupos

```python
from bcb_sgs_fetcher import ScraperClient, extract_arvore_grupos
from bs4 import BeautifulSoup

with ScraperClient() as scraper:
    html = scraper.get_grupos_principais()

soup = BeautifulSoup(html, "lxml")
grupos = extract_arvore_grupos(soup.find("table"))

for g in grupos:
    print(g.nome, g.hd_oid_grupo_selecionado)
```

---

## Modelos de Dados

### `SeriesPoint`

Retornado por `fetch_series_data()`. Um ponto da série temporal.

```python
@dataclass
class SeriesPoint:
    series_id: int
    date: date           # data de início da observação
    value: Decimal | None
    date_end: date | None  # data final (séries não diárias)
```

### `SeriesMetadataBasic`

Retornado por `parse_metadata_basic()`. Dados cadastrais da série.

```python
@dataclass
class SeriesMetadataBasic:
    series_id: int
    name: str | None                # nome completo em português
    name_abbreviated: str | None
    name_english: str | None
    theme_hierarchy: list[str]      # caminho temático: ["Câmbio", "Taxas livres"]
    frequency: str | None           # "Diária", "Mensal", etc.
    unit: str | None
    source: str | None
    start_date: date | None
    end_date: date | None
    precision: int | None
    min_value: float | None
    max_value: float | None
    special: bool | None            # série especial (restrição de uso)
```

### `SeriesMetadataFull`

Retornado por `parse_metadata_full()`. Metodologia e divulgação.

```python
@dataclass
class SeriesMetadataFull:
    last_update: date | None
    provider_data: list[ProviderField]         # dados do divulgador
    description: list[DescriptionField]        # descrição por seções
    methodology: list[MethodologyField]        # notas metodológicas
    dissemination_formats: list[DisseminationField]  # formatos de divulgação
```

---

## Séries Importantes

Algumas séries de referência do SGS/BCB:

| ID | Nome | Periodicidade |
|---|---|---|
| 1 | Taxa de câmbio — Livre — USD/BRL (compra) | Diária |
| 11 | Taxa de juros — Selic — meta Copom | Mensal |
| 12 | Taxa de juros — CDI | Diária |
| 189 | IPCA-15 — Variação mensal | Mensal |
| 433 | IPCA — Variação mensal | Mensal |
| 7478 | Taxa de câmbio — Livre — EUR/BRL (compra) | Diária |
| 13522 | IPCA — Variação acumulada em 12 meses | Mensal |

Para descobrir outros IDs, use `bcb-sgs-fetcher series search "<termo>"` ou acesse o portal SGS diretamente.

---

## Estratégia para Séries Diárias

A API pública BCB (`api.bcb.gov.br`) impõe um limite não documentado de janela temporal para séries de alta frequência. Sem parâmetros de data, o endpoint `/dados` retorna apenas os registros mais recentes — o histórico completo é truncado.

O fetcher resolve isso com a função `get_daily_series()`:

```
1. Busca os últimos 20 registros → ancora a data mais recente
2. Entra em loop retroativo: requisita Jan 1 – Dez 31 de cada ano anterior
3. Continua até o API retornar vazio (sem dados para aquele ano)
4. Agrega e ordena todos os pontos coletados
```

Essa estratégia garante o histórico completo sem depender de limites documentados da API.

---

## Armazenamento

O comando `series sync` salva os dados no arquivo `{output}/series_{series_id}.json`.

O comando `series metadata` usa um subdiretório particionado por mês:

```
{output}/
└── bcb-sgs_{YYYY-MM}/
    └── metadata/
        ├── 000001_basic.json
        └── 000001_full.json
```

Todos os arquivos são escritos atomicamente via `quantilica_core.files`.

!!! note "Saída em Parquet?"

    O `bcb-sgs-fetcher` produz apenas **JSON / dataclasses** — é um adaptador de
    fonte. A serialização em Parquet tipado fica a cargo da camada de ETL: o
    [`bcb-sgs-sql`](bcb-sgs-sql.md) carrega as séries em PostgreSQL e materializa
    saídas analíticas.

---

## Fonte de Dados

| Cliente | Endpoint | Formato |
|---|---|---|
| `SgsDataClient` | `api.bcb.gov.br/dados/serie/bcdata.sgs.{id}/dados` | JSON |
| `ScraperClient` | `www3.bcb.gov.br/sgspub` | HTML |

- [Portal SGS/BCB](https://www.bcb.gov.br/estatisticas/tabelaestatistica)
- [API BCB — documentação](https://www.bcb.gov.br/api/catalogo/apis)

---

## Saiba Mais

- [bcb-sgs-sql](bcb-sgs-sql.md) — carrega estas séries em PostgreSQL com histórico de revisões (o "Stack 2" de produção)
- [Arquitetura de CLI](../concepts/cli.md) — como fetchers se integram ao `quantilica-cli`
- [Manifestos & proveniência](../concepts/proveniencia.md) — rastreamento de origem dos dados
- [Convenções de armazenamento](../concepts/storage.md) — layout de diretórios e escrita atômica
- [Cookbook — Análise econômica multi-fonte](../cookbook/analise-economica-multi-fonte.md)
