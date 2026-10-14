---
title: datasus-fetcher — Microdados do SUS via FTP, em paralelo
description: Crawler multithread para os 113 datasets do DATASUS (SIM, SINASC, SIH, SIA, CNES, SINAN). Mais de 400 GB cobrindo 1979 até hoje, com retomada e versionamento.
---

# Saúde Pública (Saúde)

Dados de vigilância de saúde brasileira do DATASUS (Departamento de Dados de Saúde).

**datasus-fetcher** é um crawler concorrente multithreaded projetado para os microdados massivos do Sistema Único de Saúde (SUS) do Brasil hospedados em servidores FTP legados.

!!! warning "Pegadinhas da fonte oficial"

    - **`.dbc` não é `.dbf`.** É um formato proprietário compactado do DATASUS. Para abrir em Python, use `pyreaddbc` ou converta em massa com os pipelines da Quantilica.
    - **Nome de arquivo carrega significado.** `RDSP2001.dbc` = AIH Reduzido, SP, 2020, mês 01. O fetcher parseia isso para filtrar antes de baixar — não tente regex manual.
    - **FTP cai. Muito.** O servidor `ftp.datasus.gov.br` tem janelas de instabilidade quase diárias, especialmente em horário comercial. A CLI fará retries automáticos silenciosos.
    - **Volume é colossal.** Baixar tudo são mais de 400 GB e centenas de milhares de arquivos (o catálogo lista mais de 184 mil). Sempre filtre por `--start`/`--end` e/ou `--regions` no primeiro recorte.
    - **Atualizações retroativas acontecem.** O DATASUS republica arquivos antigos quando há correção. Os arquivos antigos ficam com a data da fonte no próprio nome (`@AAAAMMDD`), e `quantilica datasus archive --archive-data-dir <dir>` move os que deixaram de ser os mais recentes para `<dir>`.
    - **Dicionário de dados está em PDFs.** Sem os manuais baixados via `--docs`, códigos numéricos como `RACACOR=4` são opacos e intraduzíveis.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install datasus

# Ou como biblioteca no seu projeto
uv add datasus-fetcher --index https://index.quantilica.com/simple/
```

**Requisitos:** Python 3.12+

## CLI Oficial (Ambiente Unificado)

A forma recomendada de interagir com os dados de saúde é através do executável central `quantilica`:

```bash
# Baixar Admissões Hospitalares (SIH-RD) para o Sudeste, de 2020 a 2023
quantilica datasus sync sih-rd -o /caminho/para/dados \
    --start 2020-01 \
    --end 2023-12 \
    --regions sp --regions rj --regions mg --regions es

# Baixar notificações de dengue (todos os anos, todos os estados)
quantilica datasus sync sinan-deng -o ./data

# Inspecionar datasets disponíveis (traz a contagem e tamanho de todos os 113 datasets)
quantilica datasus list
```

---

## Datasets Disponíveis (Macro-Grupos)

A biblioteca agrupa as dezenas de siglas crípticas do DATASUS em 113 *datasets* lógicos. Os principais incluem:

- **`sih-rd`** — AIH Reduzida (admissões hospitalares)
- **`sim-do-cid10`** — Registros de mortalidade (ICD-10)
- **`sim-do-cid09`** — Registros de mortalidade (ICD-9, séries históricas)
- **`sinasc-dn`** — Registros de nascimento
- **`sia-pa`** — Produção ambulatorial
- **`cnes-st`** / **`cnes-pf`** — Estabelecimentos de saúde e profissionais do CNES
- **`sinan-deng`** / **`sinan-zika`** — Notificações de doenças

Execute `quantilica datasus list` para o catálogo completo atualizado em tempo real.

Os nomes `sim`, `sinasc` ou `sih` identificam *sistemas*, não datasets. Para baixar todos os datasets de um sistema, use `--system`:

```bash
quantilica datasus sync --system sim --start 2022 -o ./data
```

Passar um sistema como argumento posicional, onde se espera um dataset, encerra com erro de uso (código 2) antes de qualquer conexão.

!!! note "Arquivos grandes e o SIA"
    `read_dbc` e `convert` leem o `.dbf` em pedaços de 32 MiB e tipam cada pedaço antes de juntá-los. Num `.dbc` de 166 MB do SIA-PA (4,7 milhões de linhas, 62 colunas), o pico de memória foi de 18,8 GB para 4,7 GB, com o mesmo resultado. Os arquivos do SIA têm campos numéricos com lixo que o `fastdbf` recusa; nesses, cada pedaço cai para o `dbfread`, mais lento (cerca de 3,5 s por pedaço), e o arquivo acima levou cerca de 4,5 min. Evite `--workers` alto na conversão de SIA grande.

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
    .agg(pl.len().alias("Total_Obitos"))
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
    │   ├── sih-rd_202001-sp@20210405.dbc
    │   └── sih-rd_202001-rj@20210405.dbc
    └── 202312/
        └── sih-rd_202312-mg@20250105.dbc
```

## Binário `datasus-fetcher`

O pacote também instala o comando `datasus-fetcher`, equivalente a `quantilica datasus`. Ele não dispensa o host: depende do `quantilica-cli` e, sem ele, imprime `Instale via "quantilica install datasus"` e sai com código 1.

```bash
datasus-fetcher sync sim-do-cid10 -o /data --threads 4
datasus-fetcher list
datasus-fetcher archive -o /data --archive-data-dir /archive
```

## Saiba Mais

- **[Pesquisas de Saúde IBGE](../ibge/index.md)** — Estatísticas de saúde populacional
- **[Arquitetura do Ecossistema](../concepts/arquitetura.md)** — Design do sistema
- **[DATASUS Oficial (Português)](https://datasus.saude.gov.br/)** — Fonte governamental
