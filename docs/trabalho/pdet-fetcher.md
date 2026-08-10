---
title: pdet-fetcher — Microdados RAIS e CAGED
description: Baixa e converte microdados RAIS (censo anual) e CAGED (fluxos mensais) do PDET. 59+ GB de histórico laboral brasileiro.
---

# Mercado de Trabalho Brasileiro (PDET)

**pdet-fetcher** busca, lê e converte microdados do PDET (Plataforma de Disseminação de Estatísticas do Trabalho), hospedada pelo Ministério do Trabalho. 

Cobre a **RAIS** (censo anual de emprego) e o **CAGED** (fluxos mensais de emprego), englobando tanto o formato legado (até 2019) quanto o novo (2020+).

!!! warning "Pegadinhas da fonte oficial"

    - **CAGED mudou em 2020.** Schema, separadores e colunas variam drasticamente entre o legado (`caged`) e o atual (`caged-2020`).
    - **CSVs são irregulares ("ragged").** Linhas com número variável de colunas, delimitador `;` falho, encoding `latin-1` mesclado com lixo invisível. O `read_csv` nativo do Pandas falhará silenciosamente ou quebrará. O fetcher possui tratativas robustas para varrer as impurezas.
    - **Formato `.7z` é nativo.** Os arquivos vêm em 7-Zip. Você *precisa* do binário `7z` instalado no sistema (`apt-get install p7zip-full` ou `brew install p7zip`), caso contrário as funções de conversão quebrarão com erro de subprocesso.
    - **Volumes Inviáveis em RAM.** Um único ano da RAIS pode ter mais de 50 milhões de vínculos (~5 GB descomprimido). **Nunca carregue tudo em memória** usando `pd.read_csv()`. Sempre converta para Parquet e use LazyFrames.
    - **Nulos como valores extremos.** O valor `-9999` frequentemente representa `NULL` em variáveis contínuas.

## Instalação

```bash
pip install pdet-fetcher
```

**Requisitos:** Python 3.12+ e o CLI `7z` no seu `PATH`.

## CLI Oficial (Ambiente Unificado)

Para operar a extração, prefira utilizar a CLI unificada `quantilica`:

```bash
# Sincroniza RAIS e CAGED por completo (download)
quantilica pdet sync -o ./data

# Pipeline completo: sincroniza os .7z brutos e já converte tudo para Parquet
quantilica pdet pipeline -o ./data --parquet-dir ./parquet

# Listar os schemas de colunas de um dataset específico
quantilica pdet columns rais-vinculos -i ./data -o ./schemas
```

---

## Datasets Disponíveis (Macro-Grupos)

Os argumentos do subcomando `sync` mapeiam para as verticais do Ministério do Trabalho:

- **`rais-vinculos`** — Vínculos empregatícios formais do censo anual.
- **`rais-estabelecimentos`** — Características do CNPJ empregador.
- **`caged`** — Fluxos de emprego mensais até 2019.
- **`caged-ajustes`** — Arquivos atrasados retroativos do CAGED legado.
- **`caged-2020`** — Novo sistema (2020+), que baixa autonomamente os movimentos (`caged-2020-mov`), os fora do prazo (`caged-2020-for`) e as exclusões (`caged-2020-exc`).

---

## Cookbook Analítico: Lendo a gigantesca RAIS sem estourar a memória

Uma vez que você baixou a base da RAIS e do CAGED usando o `quantilica pdet pipeline` (que já converte os 7z irregulares para Parquets tipados otimizados), você lidará com dezenas de gigabytes em disco.

A melhor maneira de analisar fluxos de trabalho é usar a API Lazy do Polars (ou DuckDB). O Polars criará um grafo de execução e enviará os filtros de agregação **diretamente para o motor de leitura do Parquet**, trazendo para a RAM apenas os poucos bytes necessários da tabela final.

```python
import polars as pl

# Mapeia todos os anos dos vínculos da RAIS (ex: mais de 2 bilhões de linhas ao todo)
df_rais = pl.scan_parquet("parquet/rais_vinculos_*.parquet")

# Qual foi o salário médio por gênero (coluna 'sexo_trabalhador') no setor 
# de Tecnologia da Informação (CNAE 6204-0)?
analise_ti = (
    df_rais
    .filter(pl.col("cnae_20_classe") == "62040") # Filtro executado direto no disco!
    .group_by(["ano", "sexo_trabalhador"])
    .agg(
        pl.col("vl_remun_media_nom").mean().alias("salario_medio"),
        pl.count().alias("total_trabalhadores")
    )
    .sort(["ano", "sexo_trabalhador"])
    .collect() # O processamento massivo só ocorre aqui
)

print(analise_ti)
```

## Uso sem o Ambiente Unificado (Isolado)

Para ambientes de container minimalistas onde o `quantilica-cli` não está presente, você pode invocar o pacote autônomo diretamente:

```bash
pdet-fetcher sync -o ./data
pdet-fetcher convert -i ./data -o ./parquet
```

Você também pode utilizar as rotinas de limpeza via Python, que já corrigem os encondings e os delimitadores defeituosos:

```python
from pathlib import Path
from pdet_fetcher.reader import read_rais, read_caged

# Isso aplicará auto-detect de schema, truncamento de colunas extra, e conversão de 0/1 para Boolean.
df_vinculos = read_rais(Path("data/rais_2023_vinculos.csv"), year=2023, dataset="vinculos")
df_mov_caged = read_caged(Path("data/cagedmov_202401.csv"), date=202401, dataset="caged-2020-mov")
```

## Saiba Mais

- **[Arquitetura do Ecossistema](../concepts/arquitetura.md)** — Design do sistema
- **[PDET Oficial](http://pdet.mte.gov.br/microdados-rais-e-caged)** — Fonte governamental
