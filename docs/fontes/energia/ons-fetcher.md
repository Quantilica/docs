---
title: ons-fetcher — Dados abertos do ONS
description: Coleta os conjuntos do Operador Nacional do Sistema Elétrico (carga, geração, hidrologia, preços, intercâmbio) e converte para o lake Hive em Parquet.
---

# `ons-fetcher`

O `ons-fetcher` coleta os dados abertos do ONS (Operador Nacional do Sistema Elétrico) e converte os arquivos brutos para o lake Hive em Parquet.

| | |
|---|---|
| **Fonte** | ONS, portal de dados abertos (catálogo CKAN) e o bucket S3 público que guarda os arquivos |
| **Formato** | Parquet e CSV (um formato por arquivo, na ordem parquet > csv > zip > xlsx) |
| **Organização** | 8 grupos, 87 conjuntos catalogados e 4 macro-aliases |
| **Escopo do pacote** | download e conversão para Parquet. A carga em banco não faz parte dele |

!!! note "Pacote ainda não publicado"

    O pacote está na branch `feat/r1` e ainda não tem release no índice. Os comandos abaixo valem a partir da primeira publicação.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install ons --extra analysis

# Ou como biblioteca no seu projeto
uv add 'ons-fetcher[analysis]' --index https://index.quantilica.com/simple/
```

O extra `analysis` é necessário para a conversão ao lake.

**Requisitos:** Python 3.12+

## Primeiro dado

```bash
quantilica ons list
quantilica ons sync -o ./data/ons
```

## Comandos

| Comando | O que faz |
|---|---|
| `quantilica ons list` | Lista os arquivos dos conjuntos R1 (os que baixam hoje) |
| `quantilica ons catalogo [grupo] [--tier r1\|listed] [--json]` | Catálogo estático completo (R1 e listados), sem rede |
| `quantilica ons discover [--json] [--fail-on-change]` | Compara o catálogo com o CKAN: pacotes novos ou removidos, diretórios S3 movidos e períodos posteriores ao snapshot |
| `quantilica ons check` | Compara o disco com o remoto, sem baixar |
| `quantilica ons sync` | Baixa os grupos pedidos. Padrão de saída: `/data/ons` |
| `quantilica ons convert <entrada> <lake>` | Converte o acervo bruto para o lake Hive |

## Conjuntos: R1 e listados

O CKAN do ONS publicava 88 pacotes em 2026-11-03. O catálogo cobre os 88: 87 conjuntos em 8 grupos mais 1 link externo, que fica excluído.

| Grupo | Conjuntos | R1 (baixa) | Listado |
|---|---:|---:|---:|
| carga | 8 | 3 | 5 |
| hidrologia | 17 | 9 | 8 |
| geracao | 13 | 2 | 11 |
| precos | 4 | 3 | 1 |
| intercambio | 6 | 3 | 3 |
| cadastros | 9 | 3 | 6 |
| programacao | 7 | 0 | 7 |
| indicadores | 23 | 0 | 23 |

`list` e `sync` operam só nos **23 conjuntos R1**. Os outros 64 estão catalogados (`catalogo`) e têm download previsto para releases futuras. Macro-aliases: `avaliacao-da-operacao`, `programacao-da-operacao`, `integracao-de-instalacoes` e `energia`.

## Particionamento no lake

A conversão cobre os 23 conjuntos R1. A granularidade de cada conjunto define a partição Hive:

| Granularidade | Partição |
|---|---|
| anual | `ano` |
| mensal | `ano`, `mes` |
| mista (`geracao-usina-2`, `fator-capacidade-2`) | `ano`, `mes`, com `mes=0` para os arquivos anuais e coluna `periodicidade` (`anual`/`mensal`) |

## Política de frescor

**F1 (`HEAD_OR_MANIFEST`)**: HEAD com `ETag`, `Last-Modified` e `Content-Length`, comparado com o manifesto local. A F3 (`REMOTE_ONLY`) foi descartada para este pacote porque descartava o `Last-Modified` e fazia o `sync` rebaixar, todo dia, fontes que têm validadores.

## Limitações conhecidas

- Só os 23 conjuntos R1 são baixados; `programacao` e `indicadores` (30 conjuntos) estão apenas catalogados.
- Os diretórios e nomes do bucket S3 mudaram ao longo do tempo (`curva-carga-ho`, `EAR_DIARIO_BACIAS`, `GERACAO_USINA-2`, `RELACIONAMENTO_USINA_CONJUNTO`); o catálogo foi refeito a partir da listagem real do bucket. Use `discover` para detectar novas mudanças.
- Quando há parquet e csv do mesmo período, vale só um formato por arquivo.

## Reconversão necessária

Se o seu lake já tem `geracao-usina-2` ou `fator-capacidade-2` convertidos antes desta versão, reconverta os dois com `--force`: o lake anterior só continha a faixa mensal.

## Saiba mais

- [Changelog do pacote](https://github.com/Quantilica/ons-fetcher/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/ons-fetcher)
- [Proveniência e manifestos](../../conceitos/proveniencia.md) e [Parquet + Polars](../../conceitos/parquet-polars.md)
