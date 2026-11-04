---
title: transparencia-sp-fetcher — Remuneração de servidores de SP
description: Coleta a remuneração dos servidores do Estado de São Paulo (arquivo corrente, série mensal e série antiga em RAR) e converte para o lake Hive em Parquet.
---

# `transparencia-sp-fetcher`

O `transparencia-sp-fetcher` coleta a remuneração dos servidores do Estado de São Paulo publicada no Portal da Transparência e converte os arquivos para o lake Hive em Parquet.

| | |
|---|---|
| **Fonte** | Portal da Transparência do Estado de São Paulo (`www.transparencia.sp.gov.br`), seção Remuneração |
| **Formato** | CSV corrente, ZIP mensal (série histórica), RAR mensal (série antiga) e dicionário em XLSX |
| **Organização** | 4 grupos: `corrente`, `historico`, `rar` e `dicionario` |
| **Escopo do pacote** | download e conversão para Parquet. A carga em banco não faz parte dele |

!!! note "Pacote ainda não publicado"

    O pacote está na branch `feat/r1` e ainda não tem release no índice. Os comandos abaixo valem a partir da primeira publicação.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install transparencia-sp --extra analysis

# Ou como biblioteca no seu projeto
uv add 'transparencia-sp-fetcher[analysis]' --index https://index.quantilica.com/simple/

# Para ler a série antiga em RAR é preciso também o extra rar (libarchive-c)
uv add 'transparencia-sp-fetcher[analysis,rar]' --index https://index.quantilica.com/simple/
```

**Requisitos:** Python 3.12+. O extra `rar` depende da biblioteca `libarchive` instalada no sistema; sem ela, a conversão da série antiga falha com `RarUnavailableError`.

## Primeiro dado

```bash
quantilica transparencia-sp sync corrente -o ./data/transparencia-sp
```

## Comandos

| Comando | O que faz |
|---|---|
| `quantilica transparencia-sp list` | Lista os arquivos dos grupos |
| `quantilica transparencia-sp check` | Compara o disco com o remoto, sem baixar |
| `quantilica transparencia-sp sync` | Baixa os grupos pedidos. Padrão de saída: `/data/transparencia-sp` |
| `quantilica transparencia-sp convert <entrada> <lake>` | Converte o acervo bruto para o lake Hive |

## Conjuntos

| Grupo | O que é | Aliases |
|---|---|---|
| `corrente` | Arquivo consolidado corrente (`Remuneracao.csv`) | `padrao`, `remuneracao`, `sp_remuneracao`, `servidores`, `folha` |
| `historico` | Série histórica mensal, um ZIP por mês | `serie`, `historico_mensal` |
| `rar` | Série antiga em RAR, 130 meses (jun/2012 a mar/2023) | `serie_antiga`, `historico_rar` |
| `dicionario` | Dicionário de dados de remuneração (XLSX) | |

Os arquivos da série histórica usam os `id` numéricos publicados na página (`downloadhistorico?id=...&f=zip`), não ano e mês. A descoberta sonda os cabeçalhos e ignora meses ainda não publicados (404) ou bloqueados (405). Na série em RAR o nome do mês é por extenso (`Março` até 2016, `Marco` de 2017 em diante).

## Particionamento no lake

O dataset `remuneracao` é particionado por `ano` e `mes`. O período vem do nome do arquivo; só o arquivo corrente (sem mês de referência no conteúdo) usa o mês do carimbo `@AAAAMMDD`. Sem nenhum dos dois, o arquivo não é convertido e o erro é contado (não há mais default `2024-01`).

Cada membro (ZIP, RAR ou CSV solto) é uma origem própria (`composite_file_key`, chave `arquivo__membro`), com leitura em streaming e decodificação estrita (`latin-1` no RAR; `utf-8-sig` e depois `cp1252` no resto). As colunas monetárias das eras antigas (`TOTMES_FINAL`, `TOTBRUTO`, `TOTLIQ` e outras) também são numéricas.

## Política de frescor

**F2 (`HEAD_FALLBACK_GET`)**: HEAD com `ETag`/`Last-Modified`/`Content-Length`, com fallback para `GET` com `Range: bytes=0-0` quando o servidor devolve 403/405 ou não envia cabeçalhos.

## Limitações conhecidas

- A série em RAR exige a `libarchive` no sistema (extra `rar`).
- Meses ainda não publicados são ignorados na descoberta, sem alerta.

## Reconversão necessária

Reconverta com `--force` o lake gerado por versão anterior: só o primeiro membro de cada arquivo chegava ao lake e, sem período identificável, o dado caía em `2024-01`.

## Saiba mais

- [Changelog do pacote](https://github.com/Quantilica/transparencia-sp-fetcher/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/transparencia-sp-fetcher)
- [Proveniência e manifestos](../../conceitos/proveniencia.md) e [Parquet + Polars](../../conceitos/parquet-polars.md)
