---
title: bcb-microdados-fetcher — SCR.data, ESTBAN e COSIF do BCB
description: Baixa os microdados de crédito (SCR.data), a estatística bancária (ESTBAN) e os balancetes (COSIF) do Banco Central e converte para o lake Hive em Parquet.
---

# `bcb-microdados-fetcher`

O `bcb-microdados-fetcher` baixa os microdados publicados pelo Banco Central (crédito SCR.data, estatística bancária ESTBAN e balancetes COSIF) e converte os ZIPs para o lake Hive em Parquet.

| | |
|---|---|
| **Fonte** | Banco Central do Brasil (`www.bcb.gov.br`): ZIPs do SCR.data e a listagem JSON interna do site para ESTBAN e COSIF |
| **Formato** | ZIP com CSVs (SCR em UTF-8, ESTBAN em latin-1, COSIF em cp1252) |
| **Organização** | grupos `scr`, `estban` (`municipio`, `agencia`) e `cosif` (8 segmentos) |
| **Escopo do pacote** | download e conversão para Parquet. A carga em banco não faz parte dele |

!!! note "Pacote ainda não publicado"

    O pacote está na branch `feat/r1` e ainda não tem release no índice. Os comandos abaixo valem a partir da primeira publicação.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install bcb-microdados --extra analysis

# Ou como biblioteca no seu projeto
uv add 'bcb-microdados-fetcher[analysis]' --index https://index.quantilica.com/simple/
```

O extra `analysis` é necessário para a conversão ao lake.

**Requisitos:** Python 3.12+

## Primeiro dado

```bash
quantilica bcb-microdados sync scr -o ./data/bcb-microdados
```

## Comandos

| Comando | O que faz |
|---|---|
| `quantilica bcb-microdados list` | Lista os arquivos dos grupos |
| `quantilica bcb-microdados check` | Compara o disco com o remoto, sem baixar |
| `quantilica bcb-microdados sync` | Baixa os grupos pedidos. Padrão de saída: `/data/bcb-microdados` |
| `quantilica bcb-microdados convert <entrada> <lake>` | Converte o acervo bruto para o lake Hive |

## Conjuntos

| Grupo | Conteúdo | Descoberta |
|---|---|---|
| `scr` | SCR.data, um ZIP por ano desde 2012 (`scrdata_AAAA.zip`) | HEAD por ano: só entram os anos cujo ZIP existe (inclui o ano seguinte, quando o BCB o publica) |
| `estban` | ESTBAN por município e por agência | listagem JSON interna do BCB |
| `cosif` | COSIF em 8 segmentos (`bancos`, `cooperativas`, `consorcios`, `sociedades`, `conglomerados` e outros) | listagem JSON interna do BCB |

Aliases: `padrao`, `credito` e `scr_data` apontam para `scr`; `estatistica_bancaria`, para `estban`; `bancos`, `balancetes` e `balancos`, para `cosif`.

Para ESTBAN e COSIF o catálogo usa sempre a `Url` da listagem do BCB (nunca monta o nome do arquivo), deduplica por período (2025-12 tem `X.csv.zip` e `X.zip.csv.zip`) e guarda tamanho, data de publicação e duplicatas em `extra`. Os caminhos antigos `/estban/...` e `/cosif/...` passaram a devolver a SPA do site (HTML); a listagem JSON segue respondendo. Listagem que falha é erro contado (`DiscoveryReport.listing_errors`), sem derrubar as demais pastas. `BCB_DISCOVER=0` desliga a descoberta (testes offline).

## Particionamento no lake

| Dataset | Partição |
|---|---|
| `scr` | `ano`, `mes` |
| `estban_municipio`, `estban_agencia` | `ano`, `mes` |
| `cosif` | `segmento`, `ano` |

Cada membro de ZIP é uma origem própria (`composite_file_key`, zip mais membro). A leitura é em streaming, com decodificação estrita: byte inválido é erro contado do membro, nunca `U+FFFD`.

## Política de frescor

**F2 (`HEAD_FALLBACK_GET`)**: HEAD com `ETag`/`Last-Modified`/`Content-Length`, com fallback para `GET` com `Range: bytes=0-0` quando o servidor devolve 403/405 ou não envia cabeçalhos.

## Limitações conhecidas

- O BCB não expõe listagem JSON dos ZIPs do SCR.data (a pasta `scr` traz só PDFs e a inadimplência por coorte); por isso os anos são descobertos por HEAD, e um HEAD inconclusivo mantém o ano e é contado.
- ESTBAN e COSIF dependem de uma listagem interna do site, não de uma API pública documentada.

## Reconversão necessária

Reconverta com `--force` os parquets de `scr`, `estban_*` e `cosif` gerados por versão anterior a partir de ZIPs com vários membros: só o primeiro membro chegava ao lake.

## Saiba mais

- [Changelog do pacote](https://github.com/Quantilica/bcb-microdados-fetcher/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/bcb-microdados-fetcher)
- [Proveniência e manifestos](../../conceitos/proveniencia.md) e [Parquet + Polars](../../conceitos/parquet-polars.md)
