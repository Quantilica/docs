---
title: Dados Educacionais (INEP)
description: Ferramentas para extração e análise de dados educacionais brasileiros do INEP (Censo Escolar, ENEM, etc).
---

# Educação (INEP)

Atrás de cada ponto no IDEB há milhões de provas, questionários e matrículas — 39 GB de microdados que o INEP (Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira) distribui em CSVs gigantescos com delimitador que muda de ano para ano e dicionários espalhados. Censo Escolar, ENEM e companhia: a base para entender a educação brasileira, empacotada do jeito mais difícil possível.

## O problema

- **Volume de dados** — A base histórica completa ultrapassa **39 GB** de microdados, com arquivos CSV de milhões de linhas.
- **Nomenclatura e dicionários dispersos** — Metadados mudam entre os anos, exigindo uma unificação complexa.
- **Formatação instável** — Delimitadores diferentes (como `;` vs `,`), encodings inconsistentes e quebras de linha irregulares ao longo dos anos.

## A solução

O pacote `inep-fetcher` baixa, normaliza e converte os arquivos gigantescos do INEP diretamente para Parquet, reduzindo drasticamente o uso de memória e viabilizando a análise em tempo hábil com Polars ou DuckDB.

---

| Ferramenta | O que faz |
|---|---|
| **[inep-fetcher](inep-fetcher.md)** | Baixa microdados educacionais, unifica metadados e converte bases massivas em arquivos Parquet tipados |
