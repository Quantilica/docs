---
title: Dados do Mercado de Capitais (CVM e B3)
description: Cadastros, demonstrações financeiras e informes da CVM, mais as cotações históricas da B3 desde 1986.
---

# Mercado de Capitais (CVM e B3)

A Comissão de Valores Mobiliários e a B3 publicam em dados abertos A CVM disponibiliza os cadastros de companhias, fundos e intermediários, além das demonstrações financeiras, dos informes periódicos e das ofertas públicas. Esses conjuntos são atualizados em ritmos diferentes, e o `cvm-fetcher` os organiza por grupo para que cada um seja baixado de forma independente. A B3 publica a série histórica de cotações (COTAHIST), que o `b3-fetcher` baixa por ano e lê em Polars.

---

| Ferramenta | O que faz |
|---|---|
| **[cvm-fetcher](cvm-fetcher.md)** | Coleta os conjuntos abertos da CVM (cadastros, companhias, fundos, FII/FIDC/FIAGRO/FIP, ofertas e securitização) e converte os arquivos brutos com `convert`. |
| **[b3-fetcher](b3-fetcher.md)** | Baixa os arquivos anuais COTAHIST (1986 até hoje) e lê os registros de cotação com preços em `Decimal` exato. |
