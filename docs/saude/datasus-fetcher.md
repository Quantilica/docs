---
title: datasus-fetcher — Microdados do SUS via FTP, em paralelo
description: Crawler multithread para os 113 datasets do DATASUS (SIM, SINASC, SIH, SIA, CNES, SINAN). 383+ GB cobrindo 1979 até hoje, com retomada e versionamento.
---

# Saúde Pública (Saúde)

Dados de vigilância de saúde brasileira do DATASUS (Departamento de Dados de Saúde).

**datasus-fetcher** é um crawler concorrente multithreaded projetado para os microdados massivos do Sistema Único de Saúde (SUS) do Brasil hospedados em servidores FTP legados.

!!! warning "Pegadinhas da fonte oficial"

    - **`.dbc` não é `.dbf`.** É um formato proprietário compactado do DATASUS. Para abrir em Python, use `pyreaddbc` ou converta em massa com os pipelines da Quantilica.
    - **Nome de arquivo carrega significado.** `RDSP2001.dbc` = AIH Reduzido, SP, 2020, mês 01. O fetcher parseia isso para filtrar antes de baixar — não tente regex manual.
    - **FTP cai. Muito.** O servidor `ftp.datasus.gov.br` tem janelas de instabilidade quase diárias, especialmente em horário comercial. A CLI fará retries automáticos silenciosos.
    - **Volume é colossal.** Baixar tudo são 383+ GB e milhares de arquivos minúsculos. Sempre filtre por `--start`/`--end` e/ou `--regions` no primeiro recorte.
    - **Atualizações retroativas acontecem.** O DATASUS republica arquivos antigos quando há correção. O versionamento do fetcher arquiva os antigos no diretório `archive/`.
    - **Dicionário de dados está em PDFs.** Sem os manuais baixados via `--docs`, códigos numéricos como `RACACOR=4` são opacos e intraduzíveis.

## Instalação

```bash
pip install datasus-fetcher
```

**Requisitos:** Python 3.12+

## CLI Oficial (Ambiente Unificado)

A forma recomendada de interagir com os dados de saúde é através do executável central `quantilica`:

```bash
# Baixar Admissões Hospitalares (SIH-RD) para o Sudeste, de 2020 a 2023
quantilica datasus sync sih-rd -o /caminho/para/dados \
    --start 2020-01 \
    --end 2023-12 \
    --regions sp rj mg es

# Baixar notificações de dengue (todos os anos, todos os estados)
quantilica datasus sync sinan-deng -o ./data

# Inspecionar datasets disponíveis (traz a contagem e tamanho de todos os 113 datasets)
quantilica datasus list
```

---

## Datasets Disponíveis (Macro-Grupos)

A biblioteca agrupa as dezenas de siglas crípticas do DATASUS em 113 *datasets* lógicos. Os principais incluem:

- **`sih-rd`** — Admissões hospitalares (SIHSUS Reduzido)
- **`sim-do-cid10`** — Registros de mortalidade (ICD-10)
- **`sim-do-cid9`** — Registros de mortalidade (ICD-9, séries históricas)
- **`sinasc`** — Registros de nascimento
- **`sia-pa`** — Produção ambulatorial
- **`cnes-st`** / **`cnes-pf`** — Estabelecimentos de saúde e profissionais do CNES
- **`sinan-deng`** / **`sinan-zika`** — Notificações de doenças

Execute `quantilica datasus list` para o catálogo completo atualizado em tempo real.

---

## Cookbook Analítico: Processando o DATASUS com Polars

O DATASUS pulveriza os dados. Por exemplo, o SIM (Mortalidade) cria um arquivo separado por estado por ano. Se você baixar 20 anos para 27 UFs, terá 540 arquivos. Tentar concatenar tudo no Pandas consumirá gigabytes de RAM desnecessariamente.

Assumindo que você já converteu os `.dbc` originais para `.parquet`, eis a forma idiomática de processar centenas de arquivos com o `Polars`:

```python
import polars as pl
import plotly.express as px

# 1. Cria um LazyFrame apontando para o diretório inteiro do SIM
# A leitura só ocorre de fato quando chamamos o .collect() no final
df_sim = pl.scan_parquet("data/sim-do-cid10/**/*.parquet")

# 2. Descobrir a evolução das mortes por doenças isquêmicas do coração (I20-I25)
tendencia_mortalidade = (
    df_sim
    # Filtra direto no disco, economizando GBs de memória!
    .filter(pl.col("CAUSABAS").str.starts_with("I2"))
    # Agrega por ano e unidade federativa
    .group_by(["DTOBITO_ANO", "SIGLA_UF"])
    .agg(pl.count().alias("Total_Obitos"))
    .collect()
)

# 3. Agora o dataset está pequeno e pronto para visualização
fig = px.line(
    tendencia_mortalidade.to_pandas(), 
    x="DTOBITO_ANO", y="Total_Obitos", color="SIGLA_UF"
)
fig.show()
```

---

## Estrutura de Armazenamento

Arquivos baixados são organizados hierarquicamente para evitar estouros de limite de arquivos por pasta no sistema de arquivos:

```text
data/
└── sih-rd/
    ├── 202001/
    │   ├── sih-rd_sp_202001_20250218.dbc
    │   └── sih-rd_rj_202001_20250218.dbc
    └── 202312/
        └── sih-rd_mg_202312_20250218.dbc
```

## Uso sem o Ambiente Unificado (Isolado)

Caso você esteja construindo uma pipeline em Docker apenas para baixar saúde, sem depender do `quantilica-cli`, o pacote expõe o executável nativo:

```bash
datasus-fetcher sync sim-do-cid10 -o /data --threads 4
datasus-fetcher list
datasus-fetcher archive -o /data --archive-data-dir /archive
```

## Saiba Mais

- **[Pesquisas de Saúde IBGE](../ibge/index.md)** — Estatísticas de saúde populacional
- **[Arquitetura do Ecossistema](../concepts/arquitetura.md)** — Design do sistema
- **[DATASUS Oficial (Português)](https://datasus.saude.gov.br/)** — Fonte governamental
