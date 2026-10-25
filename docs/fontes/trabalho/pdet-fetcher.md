---
title: pdet-fetcher — Microdados RAIS e CAGED
description: Baixa e converte microdados RAIS (censo anual) e CAGED (fluxos mensais) do PDET. Mais de 60 GB de histórico laboral brasileiro.
---

# Mercado de Trabalho Brasileiro (PDET)

**pdet-fetcher** busca, lê e converte microdados do PDET (Plataforma de Disseminação de Estatísticas do Trabalho), hospedada pelo Ministério do Trabalho.

Cobre a **RAIS** (censo anual de emprego) e o **CAGED** (fluxos mensais de emprego), englobando tanto o formato legado (até 2019) quanto o novo (2020+).

!!! warning "Pegadinhas da fonte oficial"

    - **CAGED mudou em 2020.** Schema, separadores e colunas variam drasticamente entre o legado (`caged`) e o atual (`caged-2020`).
    - **CSVs são irregulares ("ragged").** Linhas com número variável de colunas, delimitador `;` falho, encoding `latin-1` mesclado com lixo invisível. O `read_csv` nativo do Pandas falhará silenciosamente ou quebrará. O fetcher possui tratativas robustas para varrer as impurezas.
    - **Formato `.7z` é nativo.** Os arquivos vêm em 7-Zip. Você *precisa* do binário `7z` instalado no sistema (`apt-get install p7zip-full` ou `brew install p7zip`), caso contrário as funções de conversão quebrarão com erro de subprocesso.
    - **Volumes Inviáveis em RAM.** Um único ano da RAIS tem dezenas de milhões de vínculos, e o arquivo compactado de 2023 no FTP já passa de 3 GB. **Nunca carregue tudo em memória** usando `pd.read_csv()`. Sempre converta para Parquet e use LazyFrames.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install pdet

# Ou como biblioteca no seu projeto
uv add pdet-fetcher --index https://index.quantilica.com/simple/
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

# Mapeia todos os anos dos vínculos da RAIS (ex: todos os anos disponíveis)
df_rais = pl.scan_parquet("parquet/rais-vinculos/rais-vinculos_*.parquet", include_file_paths="arquivo")

# Qual foi o salário médio por gênero (coluna 'sexo') no setor
# de Tecnologia da Informação (CNAE 6204-0)?
analise_ti = (
    df_rais
    .filter(pl.col("cnae_2_subclasse").cast(pl.String).str.starts_with("62040")) # Filtro executado direto no disco!
    .with_columns(pl.col("arquivo").str.extract(r"_(\d{4})@", 1).alias("ano"))  # o ano está no nome do arquivo
    .group_by(["ano", "sexo"])
    .agg(
        pl.col("valor_remuneracao_media").mean().alias("salario_medio"),
        pl.len().alias("total_trabalhadores")
    )
    .sort(["ano", "sexo_trabalhador"])
    .collect() # O processamento massivo só ocorre aqui
)

print(analise_ti)
```

## Binário `pdet-fetcher`

O pacote também instala o comando `pdet-fetcher`, equivalente a `quantilica pdet`. Ele não dispensa o host: depende do `quantilica-cli` e, sem ele, imprime `Instale via "quantilica install pdet"` e sai com código 1.

```bash
pdet-fetcher sync -o ./data
pdet-fetcher convert -i ./data -o ./parquet
```

Você também pode utilizar as rotinas de limpeza via Python, que já corrigem os encondings e os delimitadores defeituosos:

```python
from pathlib import Path
from pdet_fetcher.reader import read_rais, read_caged

# Isso aplicará o mapeamento de colunas do ano, a detecção do separador e a conversão de 0/1 para Boolean.
df_vinculos = read_rais(Path("data/rais_2023_vinculos.csv"), year=2023, dataset="vinculos")
df_mov_caged = read_caged(Path("data/cagedmov_202401.csv"), date=202401, dataset="caged-2020-mov")
```

## Saiba Mais

- **[Arquitetura do Ecossistema](../../conceitos/arquitetura.md)** — Design do sistema
- **[PDET Oficial](http://pdet.mte.gov.br/microdados-rais-e-caged)** — Fonte governamental
