---
title: Dados Eleitorais (TSE)
description: Candidaturas, bens declarados, prestação de contas e votação nominal publicados pelo Tribunal Superior Eleitoral.
---

# Política (TSE)

## O desafio

O Tribunal Superior Eleitoral publica os dados abertos das eleições no ODSele, em arquivos por dataset e por ano de eleição. Cada dataset começa em um ano diferente (candidatos em 1994, votação em 1996, bens em 2006, prestação de contas em 2020), então montar uma série exige saber o que existe em cada ano. O `tse-fetcher` coleta os datasets desse portal e permite baixar só os anos de interesse.

## Pacotes

| Ferramenta | O que faz |
|---|---|
| **[tse-fetcher](tse-fetcher.md)** | Coleta os datasets eleitorais do ODSele (candidatos, bens, prestação de contas e votação por município e zona), por ano. |

## Próximos passos

- Para baixar candidaturas, bens, prestação de contas e votação: vá para **[tse-fetcher](tse-fetcher.md)**.
- O portal do TSE já respondeu 403 a clientes sem navegador. Confira o [estado das fontes](../../status.md) antes de tratar uma falha como indisponibilidade.
