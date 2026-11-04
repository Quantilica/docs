---
title: ipeadata-fetcher — Séries do Ipeadata
description: Coleta séries macroeconômicas, sociais e regionais do Ipeadata pela API OData, com carga histórica incremental, e converte para o lake Hive em Parquet.
---

# `ipeadata-fetcher`

O `ipeadata-fetcher` coleta as séries do Ipeadata (Instituto de Pesquisa Econômica Aplicada) pela API OData e converte os dados para o lake Hive em Parquet.

| | |
|---|---|
| **Fonte** | Ipeadata, API OData (`www.ipeadata.gov.br/api/odata4`) |
| **Formato** | JSON (uma série por arquivo, mais as tabelas de metadados) |
| **Organização** | grupos `macro`, `social`, `regional` e `dimensoes`, mais grupos dinâmicos por base (`all`, `macro_all`, `social_all`, `regional_all`) |
| **Escopo do pacote** | download e conversão para Parquet. A carga em banco não faz parte dele |

!!! note "Pacote ainda não publicado"

    O pacote está na branch `feat/r1` e ainda não tem release no índice. Os comandos abaixo valem a partir da primeira publicação.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install ipeadata --extra analysis

# Ou como biblioteca no seu projeto
uv add 'ipeadata-fetcher[analysis]' --index https://index.quantilica.com/simple/
```

O extra `analysis` é necessário para a conversão ao lake.

**Requisitos:** Python 3.12+

## Primeiro dado

```bash
quantilica ipeadata sync macro -o ./data/ipeadata
```

## Comandos

| Comando | O que faz |
|---|---|
| `quantilica ipeadata list` | Lista os datasets dos grupos |
| `quantilica ipeadata check` | Compara o disco com o remoto, sem baixar |
| `quantilica ipeadata sync` | Baixa os grupos pedidos. Padrão de saída: `/data/ipeadata` |
| `quantilica ipeadata backfill` | Carga histórica exaustiva das séries. Filtros `--regional`, `--base`, `--theme`, `--source`, `--all-bases`; `--resume` (padrão) ou `--restart`; `--workers` (padrão 3) |
| `quantilica ipeadata convert <entrada> <lake>` | Converte o acervo bruto para o lake Hive |

## Conjuntos

O catálogo completo tem cerca de 4.000 séries. Os grupos fixos trazem um núcleo pequeno, e o `backfill` cobre o restante:

| Grupo | Conteúdo | Séries no núcleo |
|---|---|---:|
| `macro` | IPCA, Selic, câmbio, PIB, IGP-M, INPC, PIB mensal (alias `padrao`, `macroeconomico`) | 7 |
| `social` | IDHM, esperança de vida, PNAD (alias `sociais`) | 4 |
| `regional` | despesas e crédito de municípios (alias `regioes`) | 3 |
| `dimensoes` | tabelas de metadados: metadados das séries, temas, territórios e países (alias `metadados`) | 4 arquivos |

Os grupos dinâmicos (`all`, `macro_all`, `social_all`, `regional_all`; `todas` é alias de `all`) consultam o OData e incluem todas as séries da base. O `backfill`, sem nenhum filtro, baixa só as séries do núcleo.

## Particionamento no lake

| Dataset | Partição |
|---|---|
| `series`, `temas`, `territorios`, `paises` (dimensões) | sem partição |
| `valores` | `base`, `periodicidade` |
| `valores_regional` | `nivel`, `periodicidade` |

A `periodicidade` vem do `PERNOME` do metadado da série e o `nivel`, do `NIVNOME` de cada linha, então uma série que mistura Municípios, AMC, Estados e Brasil gera uma partição por nível. Sem metadado ou nível, o dado vai para `__HIVE_DEFAULT_PARTITION__`, com aviso.

## Política de frescor

**F3 (`REMOTE_ONLY`)**: o OData não expõe validadores de arquivo. A atualização incremental é feita pelo campo `SERATUALIZACAO` de cada série: o estado (`SERCODIGO` para `SERATUALIZACAO` da última carga válida) fica em `series/_seratualizacao.json`; `--resume` só rebaixa as séries cuja data mudou (série sem data é sempre rebaixada) e `--restart` rebaixa tudo.

## Limitações conhecidas

- Séries vazias (`value: []`), respostas inválidas e falhas de rede contam como erro no resumo do `backfill`, que sai com código 1. Cerca de 2.300 séries com `SERSTATUS != A` podem ser legitimamente vazias e contar como erro; a decisão de filtrar por status está em aberto.
- O pool de download aplica `HostPolicy` ao host do OData (`max_concurrency=N`, intervalo mínimo de 0,25 s e prazo de 900 s).

## Reconversão necessária

Reconverta o lake para corrigir as partições antigas: antes, `periodicidade` era `mensal` fixo e `nivel` era `Municipios` fixo.

## Saiba mais

- [Changelog do pacote](https://github.com/Quantilica/ipeadata-fetcher/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/ipeadata-fetcher)
- [Proveniência e manifestos](../../conceitos/proveniencia.md) e [Parquet + Polars](../../conceitos/parquet-polars.md)
