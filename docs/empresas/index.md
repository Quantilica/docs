---
title: Dados de Empresas (Receita Federal)
description: Ferramentas para manipulação da base pública de CNPJs e dados corporativos da Receita Federal.
---

# Empresas (Receita Federal)

Toda empresa formal do Brasil — da multinacional ao MEI da esquina — está num único dataset público de cerca de 29 GB descompactados, fatiado em dezenas de ZIPs sem chave estrangeira pronta. A base de CNPJs da Receita Federal é o dataset aberto mais consultado do país para crédito, inteligência de mercado e B2B — e o maior teste de engenharia de dados do ecossistema: um `JOIN` ingênuo entre Estabelecimentos e Empresas derruba o Pandas antes do café esfriar.

## O problema

- **Escala massiva** — A base completa exige cerca de **8 GB** em ZIP e **29 GB** depois de extraída, o que inviabiliza o processamento ingênuo em memória.
- **Divisão em dezenas de arquivos** — Os dados vêm divididos em arquivos ZIP fragmentados (Empresas, Estabelecimentos, Sócios, Simples, etc).
- **Sem chaves estrangeiras prontas** — Relacionar os dados de `Estabelecimento` com `Empresa` exige cruzamentos pesados, que frequentemente derrubam ferramentas como Pandas.

## A solução

O pacote `rfb-cnpj-fetcher` coordena o download em lote de todos os arquivos do site oficial da Receita Federal, e registra um manifesto SHA-256 de cada ZIP. A extração e a modelagem (por exemplo, em Parquet ou DuckDB) ficam por conta de quem analisa.

---

| Ferramenta | O que faz |
|---|---|
| **[rfb-cnpj-fetcher](rfb-cnpj-fetcher.md)** | Baixa em paralelo os ZIPs da base de CNPJs, com manifestos SHA-256 e checagem de frescor. |
