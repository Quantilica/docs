---
title: b3-fetcher — Cotações históricas da B3 (COTAHIST)
description: Baixa os arquivos anuais COTAHIST da B3 desde 1986 e lê os registros de cotação em Polars, com preços em Decimal exato.
---

# `b3-fetcher`

O `b3-fetcher` baixa a série histórica de cotações da B3 (Brasil, Bolsa, Balcão), o **COTAHIST**, e lê os registros de cotação em um DataFrame do Polars.

| | |
|---|---|
| **Fonte** | B3, série histórica de cotações (`bvmf.bmfbovespa.com.br/InstDados/SerHist`) |
| **Cobertura** | de 1986 até o ano corrente, sem ajuste de proventos |
| **Formato** | um ZIP por ano (`COTAHIST_A<ano>.zip`) com um TXT de largura fixa |
| **Grupo** | `cotacaohistorica`, particionado por ano |
| **Escopo do pacote** | download, leitura e manifest. A carga em banco não faz parte do fetcher |

!!! warning "Pegadinhas da fonte"

    - **Largura fixa, não CSV.** Cada linha tem exatamente 245 bytes em `latin-1`. O primeiro par de caracteres é o tipo do registro: `00` (cabeçalho), `01` (cotação) e `99` (rodapé).
    - **Vírgula implícita.** Preços e volumes não trazem separador decimal. `(11)V99` em 13 posições significa 2 casas decimais. O `reader` aplica isso lendo o layout, e entrega `Decimal` exato, nunca `float`.
    - **Preços sem ajuste.** Desdobramentos, grupamentos e proventos não são aplicados. Uma série longa de um papel tem saltos que não são movimento de mercado.
    - **Extensão do membro do ZIP muda.** Os arquivos recentes trazem um `.TXT`; os antigos, um único membro sem extensão. O `reader` trata os dois.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install b3

# Ou como biblioteca no seu projeto
uv add b3-fetcher --index https://index.quantilica.com/simple/
```

A leitura dos registros (`b3_fetcher.reader`) exige o extra `analysis`, que traz o Polars:

```bash
quantilica install b3 --extra analysis
# ou, no seu projeto:
uv add 'b3-fetcher[analysis]' --index https://index.quantilica.com/simple/
```

**Requisitos:** Python 3.12+

## Primeiro dado

```bash
quantilica b3 sync cotacaohistorica -o ./data/b3
```

Isso baixa todos os anos disponíveis, um arquivo por ano, com um manifest SHA-256 ao lado de cada ZIP. Para ver o que seria baixado, sem baixar:

```bash
quantilica b3 sync --dry-run -o ./data/b3
```

!!! note "Volume"

    O ZIP de 1986 tem cerca de 8 MB e traz 177.981 registros de cotação. Os anos recentes são bem maiores. Para um primeiro teste, use `--dry-run`.

## Comandos

| Comando | O que faz |
|---|---|
| `quantilica b3 list` | Lista as partições (uma por ano, de 1986 ao ano corrente) com a URL de cada uma |
| `quantilica b3 check` | Compara o disco com o remoto e diz o que está desatualizado, sem baixar. `--json` imprime o plano e `--out` o grava |
| `quantilica b3 sync` | Baixa os grupos pedidos (padrão: todos). `--output`/`-o` define o diretório, `--workers` os downloads paralelos (padrão 4), `--dry-run` só lista e `--force` ignora a checagem de frescor |

O fluxo recomendado é `check --out plano.json` seguido de `sync --from-plan plano.json`: baixa só o que mudou.

### Onde os arquivos ficam

```text
data/b3/
└── cotacaohistorica/
    └── 2025/
        ├── cotacaohistorica_2025@<data>.zip
        └── cotacaohistorica_2025@<data>.zip.manifest.json
```

A data no nome vem do `Last-Modified` do servidor. Uma nova versão remota do mesmo ano vira um arquivo novo, sem sobrescrever o anterior.

## Lendo os registros

```python
from pathlib import Path

from b3_fetcher.reader import read_dimension, read_records

df = read_records(Path("data/b3/cotacaohistorica/1986/cotacaohistorica_1986@<data>.zip"))
print(df.schema)
```

`read_records` aceita o `.zip` baixado ou o `.txt` já extraído e devolve só os registros `01`. As conversões são estritas: um campo em branco vira nulo, mas um valor que não cabe no tipo do layout levanta erro em vez de virar nulo em silêncio.

Colunas principais:

| Coluna | Tipo | Significado |
|---|---|---|
| `data` | `Date` | Data do pregão |
| `simbolo` | `String` | Código de negociação do papel |
| `nome_resumido` | `String` | Nome resumido da empresa emissora |
| `tipo_mercado_id` | `Int64` | Tipo de mercado (ver `read_dimension("tpmerc")`) |
| `bdi_id` | `String` | Código BDI (ver `read_dimension("codbdi")`) |
| `especificacao_id` | `String` | Especificação do papel (ver `read_dimension("especi")`) |
| `preco_abertura`, `preco_maximo`, `preco_minimo`, `preco_medio`, `preco_ultimo_negocio` | `Decimal(13, 2)` | Preços do pregão |
| `quantidade_negocios`, `quantidade_titulos_negociados` | `Int64` | Número de negócios e de títulos negociados |
| `volume_negociado` | `Decimal(18, 2)` | Volume financeiro |
| `data_vencimento` | `Date` | Vencimento (opções e termo) |
| `fator_cotacao` | `Int64` | Fator de cotação do papel |

As 26 colunas completas seguem o layout oficial do registro `01`.

### Tabelas auxiliares

```python
read_dimension("tpmerc")   # tipo de mercado
read_dimension("codbdi")   # código BDI
read_dimension("especi")   # especificação do papel
read_dimension("indopc")   # índice de correção de opções
```

Cada tabela vem com nomes de coluna canônicos (`tipo_mercado_id`/`tipo_mercado`, `bdi_id`/`bdi` e assim por diante), prontos para `join` com `read_records`.

### Salvando em Parquet

```python
from b3_fetcher.reader import write_parquet

write_parquet(df, Path("data/b3/parquet/1986.parquet"), source_path=zip_path)
```

Com `source_path`, o manifest do ZIP original é copiado para os metadados do Parquet, preservando a proveniência. A escrita é atômica e usa compressão zstd.

## Particularidades

- **Primeiro ano:** `COTAHIST_A1985.zip` responde `404`. A série começa em 1986.
- **Outras granularidades:** a B3 também publica arquivos mensais e diários. O pacote expõe `build_monthly_url` e `build_daily_url` para montar essas URLs, mas o `sync` trabalha com os arquivos anuais.
- **Validação:** na primeira publicação, os 40 arquivos anuais de 1986 a 2025 foram lidos sem erro nem nulo inesperado.

## Saiba mais

- [Changelog do pacote](https://github.com/Quantilica/b3-fetcher/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/b3-fetcher)
- [Convenções de armazenamento](../../conceitos/storage.md) e [proveniência e manifestos](../../conceitos/proveniencia.md)
