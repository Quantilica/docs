---
title: tse-fetcher — Dados eleitorais do TSE
description: Coletor dos datasets eleitorais do TSE publicados no ODSele, com seleção por ano.
---

# `tse-fetcher`

O `tse-fetcher` coleta os datasets eleitorais do ODSele, o portal de dados abertos do TSE.

## Instalação

```bash
quantilica install tse
```

## Datasets

| Dataset | Conteúdo | Primeiro ano | Por UF |
|---|---|---|---|
| `candidatos` | Candidatos (consulta de candidaturas) | 1994 | não |
| `bens` | Bens declarados pelos candidatos | 2006 | não |
| `prestacao_contas` | Prestação de contas eleitorais (receitas e despesas de candidatos) | 2020 | não |
| `votacao` | Votação nominal por município e zona | 1996 | não |

Os nomes `despesas` e `receitas` ainda são aceitos, mas estão descontinuados: ambos resolvem para `prestacao_contas`.

Liste os datasets com `quantilica tse list` e veja os metadados de um deles com `quantilica tse info <dataset>`.

## Como usar

Verificar o remoto contra o local, sem baixar:

```bash
quantilica tse check --years 2022
```

Baixar datasets de um ano, ou de um intervalo de anos:

```bash
quantilica tse sync candidatos votacao --years 2022 -o ./data/tse
quantilica tse sync prestacao_contas --years 2020:2024 -o ./data/tse
```

Sem `--years` nem nomes de dataset, `sync` baixa todos os datasets de todos os anos. O padrão de saída é `/data/tse`.
