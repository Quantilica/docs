---
title: bcb-sgs-fetcher — Séries temporais do Banco Central do Brasil
description: Coleta séries temporais do SGS/BCB via API JSON e scraping HTML — câmbio, SELIC, CDI, IPCA e centenas de outros indicadores macroeconômicos.
---

# Banco Central do Brasil (SGS)

O Sistema Gerenciador de Séries Temporais (SGS) é o repositório oficial de indicadores macroeconômicos do BCB. O catálogo lista 19.607 séries (6.841 delas desativadas; contagem de 2026-10-13), muitas com histórico desde a década de 1980.

**bcb-sgs-fetcher** expõe dois clientes resilientes: o `SgsDataClient` para a API JSON pública, e o `ScraperClient` para contornar a ausência de uma API de metadados via scraping.

!!! warning "Pegadinhas da fonte oficial"

    - **Séries diárias capadas silenciosamente:** a API `/dados` do BCB não retorna o histórico completo para séries de alta frequência se você não passar uma janela de data estrita; ela apenas trunca os resultados velhos. A CLI da Quantilica resolve isso ancorando uma data recente e fazendo paginação retroativa ano a ano até secar o poço.
    - **Metadados invisíveis:** Não existe API pública para descobrir os nomes das séries. A CLI faz um scraping HTML com sessão stateful para descobrir isso. Por isso, a descoberta da árvore de grupos (`catalogo arvore-grupos`) é sequencial; a coleta em lote dos metadados (`catalogo metadata-bulk`) aceita `--workers`.
    - **Séries Zumbis:** Séries encerradas pelo BCB (como antigas taxas do mercado livre) ainda existem no SGS mas podem retornar conjuntos de dados vazios ou corrompidos.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install bcb-sgs

# Ou como biblioteca no seu projeto
uv add bcb-sgs-fetcher --index https://index.quantilica.com/simple/
```

**Requisitos:** Python 3.12+

## CLI Oficial (Ambiente Unificado)

Para baixar os dados diretamente, prefira o hub central `quantilica`:

```bash
# Dados históricos de câmbio USD/BRL (série 1, diária)
quantilica bcb-sgs series sync 1 -f D -o ./dados

# Dados da taxa SELIC mensal
quantilica bcb-sgs series sync 11 -f M -o ./dados

# Sincronizar o catálogo completo de metadados
# (varre o site do BCB via web scraping)
quantilica bcb-sgs catalogo sync
```

!!! info "A Mágica da Periodicidade `D`"
    Ao passar `-f D`, o fetcher ativa a estratégia retroativa ano a ano para driblar os bloqueios não-documentados da API do governo. Não use `-f D` para séries mensais!

---

## Séries Importantes (Macro-Grupos)

Em vez de grupos nomeados, o BCB opera unicamente por **IDs Numéricos**. Eis as âncoras da macroeconomia brasileira:

| ID | Nome | Periodicidade |
|---|---|---|
| **1** | Taxa de câmbio — Livre — USD/BRL (compra) | Diária |
| **11** | Taxa de juros — Selic — meta Copom | Mensal |
| **12** | Taxa de juros — CDI | Diária |
| **189** | IPCA-15 — Variação mensal | Mensal |
| **433** | IPCA — Variação mensal | Mensal |
| **7478** | Taxa de câmbio — Livre — EUR/BRL (compra) | Diária |
| **13522** | IPCA — Variação acumulada em 12 meses | Mensal |

Para descobrir outros IDs na CLI:
`quantilica bcb-sgs series search "inadimplência"`

---

## Cookbook Analítico: Séries Temporais com Polars

O `bcb-sgs-fetcher` despeja JSONs contendo as séries no disco, pois é uma ponte desenhada principalmente para alimentar a camada de ETL do [`bcb-sgs-sql`](bcb-sgs-sql.md). Mas se você deseja consumi-los puramente via scripts analíticos:

```python
import polars as pl
from pathlib import Path

# Supondo que baixamos a SELIC acumulada no mês (4390) e o IPCA (433) com
#   quantilica bcb-sgs series sync 4390 -o ./dados
#   quantilica bcb-sgs series sync 433 -o ./dados
# Cada série vira dados/data/series_<id>@<AAAAMMDDTHHMMSS>.json: uma lista de
# objetos {"series_id": 433, "date": "2026-08-01", "value": "-0.32", "date_end": null}
def le_serie(serie_id, nome):
    arquivo = max(Path("dados/data").glob(f"series_{serie_id}@*.json"))  # snapshot mais recente
    return pl.read_json(arquivo).select(
        pl.col("date").str.to_date(),                 # datas já vêm em ISO (AAAA-MM-DD)
        pl.col("value").cast(pl.Float64).alias(nome),
    )

df_selic_clean = le_serie(4390, "selic_mensal")
df_ipca_clean = le_serie(433, "ipca_mensal")

# Juntar (JOIN) a inflação e a Selic para calcular Juro Real
juros_reais = (
    df_selic_clean
    .join(df_ipca_clean, on="date", how="inner")
    .with_columns(
        (pl.col("selic_mensal") - pl.col("ipca_mensal")).alias("juro_real")
    )
    .sort("date", descending=True)
)

print(juros_reais.head())
```

## Uso via Python Puro (Bibliotecas de Extração)

```python
from bcb_sgs_fetcher import SgsDataClient

# Download resiliente do Câmbio (USD/BRL)
with SgsDataClient() as client:
    points = client.fetch_series_data(
        series_id=1,
        frequency_acronym="D",
    )

print(points[0].date, points[0].value)
```

## Saiba Mais

- **[bcb-sgs-sql](bcb-sgs-sql.md)** — Motor ETL que envia estas séries para PostgreSQL com histórico de revisões.
- **[Arquitetura do Ecossistema](../concepts/arquitetura.md)** — Como as bibliotecas se conectam.
