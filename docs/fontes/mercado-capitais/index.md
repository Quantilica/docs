---
title: Dados do Mercado de Capitais (CVM e B3)
description: Cadastros, demonstrações financeiras e informes da CVM, mais as cotações históricas da B3 desde 1986.
---

# Mercado de Capitais (CVM e B3)

## O desafio

Duas fontes públicas, dois formatos. A CVM disponibiliza os cadastros de companhias, fundos e intermediários, além das demonstrações financeiras, dos informes periódicos e das ofertas públicas. Esses conjuntos são atualizados em ritmos diferentes, e o `cvm-fetcher` os organiza por grupo para que cada um seja baixado de forma independente. A B3 publica a série histórica de cotações (COTAHIST) em arquivos de largura fixa, e o `b3-fetcher` os baixa por ano e lê em Polars, com preços em `Decimal` exato.

## Pacotes

| Ferramenta | O que faz |
|---|---|
| **[cvm-fetcher](cvm-fetcher.md)** | Coleta os conjuntos abertos da CVM (cadastros, companhias, fundos, FII/FIDC/FIAGRO/FIP, ofertas e securitização) e converte os arquivos brutos com `convert`. |
| **[b3-fetcher](b3-fetcher.md)** | Baixa os arquivos anuais COTAHIST (1986 até hoje) e lê os registros de cotação com preços em `Decimal` exato. |

## Próximos passos

- Para baixar dados cadastrais, financeiros e de fundos: vá para **[cvm-fetcher](cvm-fetcher.md)**.
- Para a série histórica de preços das ações: vá para **[b3-fetcher](b3-fetcher.md)**.
- Antes de rodar um download grande, confira o [estado das fontes](../../status.md).
