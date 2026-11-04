---
title: Governo e transparência — remuneração de servidores de SP
description: Dados de transparência do setor público, começando pela remuneração dos servidores do Estado de São Paulo, de 2012 até hoje.
---

# Governo e transparência

## O desafio

O Portal da Transparência de São Paulo publica a remuneração dos servidores em três formatos ao longo do tempo: um CSV corrente, um ZIP por mês na série histórica e, para jun/2012 a mar/2023, um RAR por mês com nomes de arquivo irregulares. O `transparencia-sp-fetcher` junta as três gerações em um único dataset no lake.

## Pacotes

| Ferramenta | O que faz |
|---|---|
| **[transparencia-sp-fetcher](transparencia-sp-fetcher.md)** | Coleta o arquivo corrente, a série histórica mensal e a série antiga em RAR (130 meses) e converte para Parquet por `ano` e `mes`. |

## Próximos passos

- Para baixar e converter: vá para **[transparencia-sp-fetcher](transparencia-sp-fetcher.md)**.
- Antes de rodar um download grande, confira o [estado das fontes](../../status.md).
