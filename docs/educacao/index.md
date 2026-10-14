---
title: Dados Educacionais (INEP)
description: Ferramentas para extração e análise de dados educacionais brasileiros do INEP (ENEM, SAEB, ENADE, etc).
---

# Educação (INEP)

Atrás de cada ponto no IDEB há milhões de provas, questionários e matrículas — mais de 20 GB de microdados que o INEP (Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira) distribui em CSVs gigantescos com delimitador que muda de ano para ano e dicionários espalhados. ENEM, SAEB e companhia: a base para entender a educação brasileira, empacotada do jeito mais difícil possível.

## O problema

- **Volume de dados** — A base histórica completa passa de **20 GB** de microdados, com arquivos CSV de milhões de linhas.
- **Nomenclatura e dicionários dispersos** — Metadados mudam entre os anos, exigindo uma unificação complexa.
- **Formatação instável** — Delimitadores diferentes (como `;` vs `,`), encodings inconsistentes e quebras de linha irregulares ao longo dos anos.

## A solução

O pacote `inep-fetcher` baixa os arquivos do INEP por grupo, em paralelo e com manifestos de proveniência. A leitura e a conversão para Parquet ficam por conta de quem analisa, por exemplo com Polars ou DuckDB.

---

| Ferramenta | O que faz |
|---|---|
| **[inep-fetcher](inep-fetcher.md)** | Baixa microdados educacionais por grupo (ENEM, SAEB, ENADE e outros), com download concorrente e manifestos SHA-256 |
