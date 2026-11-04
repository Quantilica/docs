---
title: loterias-fetcher — Resultados das loterias da Caixa
description: Baixa resultados históricos e o último concurso das 11 modalidades das Loterias Caixa e converte para o lake Hive em Parquet, particionado por modalidade.
---

# `loterias-fetcher`

O `loterias-fetcher` baixa os resultados das Loterias Caixa (planilha histórica por modalidade e JSON do último concurso) e converte para o lake Hive em Parquet.

| | |
|---|---|
| **Fonte** | Caixa Econômica Federal, portal de loterias (API de resultados) |
| **Formato** | XLSX (histórico) e JSON (detalhe do último concurso) |
| **Organização** | 2 grupos (`concursos` e `detalhe`) com 11 modalidades cada, 22 arquivos |
| **Escopo do pacote** | download e conversão para Parquet. A carga em banco não faz parte dele |

!!! note "Pacote ainda não publicado"

    O pacote está na branch `feat/r1` e ainda não tem release no índice. Os comandos abaixo valem a partir da primeira publicação.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install loterias --extra analysis

# Ou como biblioteca no seu projeto
uv add 'loterias-fetcher[analysis]' --index https://index.quantilica.com/simple/
```

O extra `analysis` é necessário para a conversão ao lake.

**Requisitos:** Python 3.12+

## Primeiro dado

```bash
quantilica loterias sync concursos -o ./data/loterias
```

## Comandos

| Comando | O que faz |
|---|---|
| `quantilica loterias list` | Lista os arquivos dos grupos |
| `quantilica loterias check` | Compara o disco com o remoto, sem baixar |
| `quantilica loterias sync` | Baixa os grupos pedidos. Padrão de saída: `/data/loterias` |
| `quantilica loterias convert <entrada> <lake>` | Converte o acervo bruto para o lake Hive |

## Conjuntos

| Grupo | O que é | Arquivos | Aliases |
|---|---|---:|---|
| `concursos` | Resultados históricos consolidados (XLSX) por modalidade | 11 | `resultados`, `historico`, `xlsx` |
| `detalhe` | JSON do último concurso por modalidade | 11 | `json` |

Modalidades (com o ano inicial): Mega-Sena (1996), Lotofácil (2003), Quina (1994), Lotomania (1999), Timemania (2008), Dupla Sena (2001), Dia de Sorte (2018), Super Sete (2020), +Milionária (2022), Federal (1962) e Loteca (2002). Não há conjuntos apenas listados.

## Particionamento no lake

Três datasets, todos particionados por `modalidade`:

| Dataset | Origem | Conteúdo |
|---|---|---|
| `concursos` | XLSX histórico | um registro por concurso (data, dezenas, arrecadação, acumulado, estimativa) |
| `rateio` | JSON do concurso | faixas de premiação e ganhadores |
| `ganhadores_municipio` | JSON do concurso | ganhadores por município e UF |

`rateio` e `ganhadores_municipio` gravam cada concurso como membro do arquivo agrupado `<modalidade>.parquet`. Reconverter depois de um concurso novo adiciona as linhas dele sem perder as dos demais. JSON ilegível ou sem número de concurso vira erro contado.

## Política de frescor

**F3 (`REMOTE_ONLY`)**: a API de resultados não expõe validadores, então o pacote valida o conteúdo em stream e deduplica por `sha256` local. O `check` indica "download" sempre, o que é verdade nessas fontes.

## Limitações conhecidas

- O grupo `detalhe` traz só o último concurso de cada modalidade; o histórico de rateio e de ganhadores por município se acumula conforme as execuções passam.

## Reconversão necessária

Se o lake tiver `rateio` ou `ganhadores_municipio` convertidos por versão anterior, reconverta com `--force`: antes, a modalidade inteira era escrita com o primeiro JSON como origem e as linhas de concursos novos eram puladas por `sha256`.

## Saiba mais

- [Changelog do pacote](https://github.com/Quantilica/loterias-fetcher/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/loterias-fetcher)
- [Proveniência e manifestos](../../conceitos/proveniencia.md) e [Parquet + Polars](../../conceitos/parquet-polars.md)
