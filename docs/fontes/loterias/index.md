---
title: Loterias — resultados das Loterias Caixa
description: Resultados históricos e do último concurso das Loterias Caixa (Mega-Sena, Lotofácil, Quina e outras 8 modalidades), prontos para análise.
---

# Loterias

## O desafio

Os resultados das Loterias Caixa estão em planilhas por modalidade e em um JSON por concurso, com a premiação por faixa e por município. O `loterias-fetcher` baixa as duas formas e as junta no lake, particionadas por modalidade.

## Pacotes

| Ferramenta | O que faz |
|---|---|
| **[loterias-fetcher](loterias-fetcher.md)** | Coleta resultados históricos e o último concurso de 11 modalidades e converte para Parquet (`concursos`, `rateio`, `ganhadores_municipio`). |

## Próximos passos

- Para baixar e converter: vá para **[loterias-fetcher](loterias-fetcher.md)**.
- Antes de rodar um download grande, confira o [estado das fontes](../../status.md).
