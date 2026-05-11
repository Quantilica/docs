---
title: Estiagem no Nordeste — 30 anos de INMET
description: Série climática histórica do BDMEP para identificar tendência de precipitação no semiárido brasileiro. Só inmet-fetcher + Polars.
---

# Estiagem no Nordeste — 30 anos de INMET

> **Tempo estimado:** 15 minutos (depois do download inicial). **Pacotes:** `inmet-fetcher`, `polars`, `altair`.

O Nordeste tem o maior corpo conhecido de séries climáticas estável do Brasil. Vamos baixar 30 anos do BDMEP, filtrar as estações nordestinas e visualizar a evolução da precipitação anual.

## O que você vai produzir

Um gráfico de precipitação total anual média por estado do Nordeste, com tendência linear, ao longo de 30 anos.

## Setup

```bash
uv add "inmet-fetcher @ git+https://github.com/Quantilica/inmet-fetcher.git" polars "altair[save]"
```

## A receita

### 1. Baixar 30 anos em paralelo

```bash
inmet-fetcher fetch 1995:2024 --data-dir ./dados --workers 8
```

O `--workers 8` paraleliza os downloads anuais. Para 30 ZIPs, fica em poucos minutos numa conexão razoável.

### 2. Ler e filtrar para o Nordeste

```python
import polars as pl
import altair as alt

# O inmet-fetcher já entrega snake_case, latin-1 resolvido, -9999 → null
df = pl.read_parquet("dados/inmet.parquet")  # gerado por `inmet-fetcher read`

nordeste = ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"]

chuva_anual = (
    df.filter(pl.col("uf").is_in(nordeste))
      .with_columns(ano=pl.col("data_hora").dt.year())
      .group_by("uf", "ano")
      .agg(pl.col("precipitacao_total").sum().alias("mm_ano"))
      .filter(pl.col("mm_ano") > 0)   # estações sem dado caem
)
```

### 3. Gerar a série de tendência

```python
import numpy as np

def add_trend(df_pd):
    if len(df_pd) < 5:
        return df_pd
    x = df_pd["ano"].to_numpy()
    y = df_pd["mm_ano"].to_numpy()
    slope, intercept = np.polyfit(x, y, 1)
    df_pd["tendencia"] = slope * x + intercept
    return df_pd

tend = chuva_anual.to_pandas().groupby("uf", group_keys=False).apply(add_trend)
```

### 4. Plotar

```python
base = alt.Chart(tend).encode(x="ano:O")

points = base.mark_line(opacity=0.5).encode(y="mm_ano:Q", color="uf:N")
trend = base.mark_line(strokeDash=[6, 4]).encode(y="tendencia:Q", color="uf:N")

(points + trend).properties(
    width=750, height=450,
    title="Precipitação anual média por UF — Nordeste, 1995–2024"
).facet(column="uf:N", columns=3).save("estiagem.html")
```

## O que está acontecendo

- O `inmet-fetcher` já entregou Parquet com `snake_case`, `datetime` nativo e nulos (`-9999`) tratados.
- Agregamos por UF e ano, somando precipitação horária. Estações múltiplas dentro do mesmo estado entram naturalmente na agregação.
- A tendência linear simples é só ilustrativa — para análise climática séria, use Mann-Kendall ou Theil-Sen.

## Pegadinhas

- **Cobertura desigual.** Antes de 2008, a rede automática era pequena. Estações convencionais cobrem mais tempo, mas com granularidade diária. Decida qual usar.
- **Precipitação horária ≠ acumulado oficial.** O INMET publica acumulados pluviométricos em estações convencionais separadas. Para análise séria de cheia/seca, complemente.
- **Estações se mudam.** Alguns códigos `A###` mudaram de localização ao longo do tempo. O `inmet-fetcher` preserva o código WMO, mas confira lat/lon antes de assumir continuidade.
- **El Niño domina a variabilidade.** 1997-98, 2015-16, 2023 são anos atípicos. Para tendência, considere ciclos.

## Variações

- **Mapa coroplético** — agregue por município (usando o município mais próximo de cada estação) e plote com `geopandas`.
- **Compare com produção agrícola** — junte com PAM via `sidra-fetcher` e olhe correlação chuva × safra.
- **Anomalia padronizada** — calcule `(valor - média) / dp` por estação para visualizar secas relativas.

## Veja também

- [inmet-fetcher](../clima/inmet-fetcher.md)
- [Princípios — Performance](../concepts/principios.md#performance) — por que processar Parquet com Polars é rápido para esse volume.
