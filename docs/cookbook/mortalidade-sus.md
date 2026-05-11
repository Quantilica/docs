---
title: Mortalidade infantil × cobertura SUS por município
description: Cruza microdados do SIM com população do SIDRA e cadastro CNES. DATASUS + IBGE em um pipeline reproduzível.
---

# Mortalidade infantil × cobertura SUS por município

> **Tempo estimado:** 30 minutos (depende do recorte). **Pacotes:** `datasus-fetcher`, `sidra-fetcher`, `polars`, `pyreaddbc`.

Taxa de mortalidade infantil é o indicador clássico de saúde pública. Vamos cruzá-la com a cobertura de estabelecimentos SUS por município usando três fontes oficiais — DATASUS (SIM e CNES) e IBGE (estimativas populacionais).

## O que você vai produzir

Uma tabela municipal com:

- **Óbitos infantis** (< 1 ano) por município (SIM/DATASUS).
- **Nascidos vivos** por município (SINASC/DATASUS) — denominador.
- **População total** por município (IBGE).
- **Estabelecimentos SUS** por município (CNES/DATASUS).
- **Taxa por 1000 nascidos vivos** + densidade de equipamentos SUS por 10k habitantes.

## Setup

```bash
uv add "datasus-fetcher" "sidra-fetcher @ git+https://github.com/Quantilica/sidra-fetcher.git" polars pyreaddbc
```

## A receita

### 1. Baixar SIM, SINASC e CNES para um ano e região

```bash
# Óbitos
datasus-fetcher data --data-dir ./dados sim --start 2022 --end 2022 --regions sp

# Nascidos vivos
datasus-fetcher data --data-dir ./dados sinasc --start 2022 --end 2022 --regions sp

# Cadastro de estabelecimentos
datasus-fetcher data --data-dir ./dados cnes-st --start 2022-12 --end 2022-12 --regions sp
```

### 2. Baixar população do SIDRA

```python
from pathlib import Path
import polars as pl
import pyreaddbc
from sidra_fetcher.fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao


# Estimativas de população por município — agregado 6579, variável 9324
with SidraClient(timeout=60) as client:
    param = Parametro(
        agregado="6579",
        territorios={"6": ["all"]},      # todos os municípios
        variaveis=["9324"],
        periodos=["2022"],
        classificacoes={},
        formato=Formato.A,
        decimais={"": Precisao.M},
    )
    rows = client.get(param.url())

pop = pl.DataFrame(rows[1:]).select(
    pl.col("D1C").alias("codigo_municipio"),
    pl.col("V").cast(pl.Int64, strict=False).alias("populacao"),
).drop_nulls()
```

### 3. Ler os `.dbc` do DATASUS

```python
def read_dbc_dir(dir_path: Path, columns: list[str]) -> pl.DataFrame:
    frames = []
    for dbc in sorted(dir_path.glob("*.dbc")):
        df = pyreaddbc.read_dbc(str(dbc))
        frames.append(pl.from_pandas(df).select(columns))
    return pl.concat(frames)


sim = read_dbc_dir(Path("dados/sim"), ["IDADE", "CODMUNRES"])
sinasc = read_dbc_dir(Path("dados/sinasc"), ["CODMUNRES"])
cnes = read_dbc_dir(Path("dados/cnes-st"), ["CODUFMUN", "CO_CNES"])
```

### 4. Calcular o indicador

```python
obitos_infantis = (
    sim.filter(pl.col("IDADE").str.starts_with("4"))  # IDADE em SIM: 4xx = 0..364 dias
       .group_by("CODMUNRES")
       .len()
       .rename({"CODMUNRES": "codigo_municipio", "len": "obitos_infantis"})
)

nascidos = (
    sinasc.group_by("CODMUNRES")
          .len()
          .rename({"CODMUNRES": "codigo_municipio", "len": "nascidos_vivos"})
)

estabelecimentos = (
    cnes.group_by("CODUFMUN")
        .len()
        .rename({"CODUFMUN": "codigo_municipio", "len": "estabelecimentos_sus"})
)

painel = (
    pop.join(obitos_infantis, on="codigo_municipio", how="left")
       .join(nascidos,        on="codigo_municipio", how="left")
       .join(estabelecimentos, on="codigo_municipio", how="left")
       .with_columns(
           tmi_por_1000=pl.col("obitos_infantis") / pl.col("nascidos_vivos") * 1000,
           sus_per_10k=pl.col("estabelecimentos_sus") / pl.col("populacao") * 10_000,
       )
)

print(painel.sort("tmi_por_1000", descending=True).head(20))
```

## O que está acontecendo

- **SIM `IDADE`** começa com `4` para `0–364 dias` (`401` = 1 dia, `464` = 364 dias). Mortalidade infantil = óbitos com `IDADE` começando em `4`.
- **`CODMUNRES`** (SIM/SINASC) e **`CODUFMUN`** (CNES) são o **mesmo conceito** — código IBGE de 6 dígitos. A nomenclatura DATASUS varia entre sistemas.
- **População** do SIDRA usa o mesmo código IBGE — o join funciona naturalmente.
- O resultado já é uma tabela municipal pronta para mapa coroplético ou regressão.

## Pegadinhas

- **Códigos de município truncados.** SIM/SINASC usam 6 dígitos; SIDRA usa 7 (com dígito verificador). Você pode truncar ou expandir — escolha um lado.
- **`IDADE` em SIM é codificada.** Não é número direto. Consulte o dicionário (`datasus-fetcher docs sim`) antes de filtrar.
- **CNES é foto mensal.** O dataset `cnes-st` mostra o estabelecimento no mês específico. Para série, baixe vários meses e use `MAX(competencia)` por município.
- **Mortalidade infantil é volátil em municípios pequenos.** Para municípios com <100 nascidos/ano, a taxa flutua absurdamente. Agregue por microrregião ou suavize com média móvel trianual.

## Variações

- **Razão de mortalidade materna** — use óbitos `OBITOGRAV` no SIM dividido por nascidos do SINASC.
- **Cobertura vacinal × incidência** — junte com PNI (programa nacional de imunizações) via `datasus-fetcher`.
- **Equidade regional** — junte com o IDHM (atlas Brasil) e veja desigualdade.

## Veja também

- [datasus-fetcher](../saude/datasus-fetcher.md)
- [Cientista de dados de saúde pública](../personas/cientista-saude.md) — atalhos para o seu perfil.
- [Proveniência](../concepts/proveniencia.md) — fundamental para auditar quais versões dos `.dbc` você usou.
