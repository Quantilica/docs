---
title: Dados Educacionais (INEP)
description: Ferramentas para extração e análise de dados educacionais brasileiros do INEP (Censo Escolar, ENEM, etc).
---

# Educação (INEP)

Os dados do INEP (Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira) formam a base para entender o cenário educacional brasileiro. Suas principais bases (como o Censo Escolar e o ENEM) envolvem gigabytes de dados, muitas vezes distribuídos em formatos complexos ou arquivos CSV/TXT gigantescos.

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
