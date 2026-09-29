---
title: Dados de Empresas (Receita Federal)
description: Ferramentas para manipulação da base pública de CNPJs e dados corporativos da Receita Federal.
---

# Empresas (Receita Federal)

Toda empresa formal do Brasil — da multinacional ao MEI da esquina — está num único dataset público de 245 GB, fatiado em dezenas de ZIPs sem chave estrangeira pronta. A base de CNPJs da Receita Federal é o dataset aberto mais consultado do país para crédito, inteligência de mercado e B2B — e o maior teste de engenharia de dados do ecossistema: um `JOIN` ingênuo entre Estabelecimentos e Empresas derruba o Pandas antes do café esfriar.

## O problema

- **Escala massiva** — A base completa descompactada exige cerca de **245 GB** de armazenamento, inviabilizando processamento ingênuo.
- **Divisão em dezenas de arquivos** — Os dados vêm divididos em arquivos ZIP fragmentados (Empresas, Estabelecimentos, Sócios, Simples, etc).
- **Sem chaves estrangeiras prontas** — Relacionar os dados de `Estabelecimento` com `Empresa` exige cruzamentos pesados, que frequentemente derrubam ferramentas como Pandas.

## A solução

O pacote `rfb-cnpj-fetcher` coordena o download em lote de todos os arquivos do site oficial da Receita Federal, realiza verificações SHA-256 e extrai tudo para um modelo normalizado em Parquet ou DuckDB diretamente, viabilizando consultas relampâgo sem precisar hospedar um banco de dados gigante.

---

| Ferramenta | O que faz |
|---|---|
| **[rfb-cnpj-fetcher](rfb-cnpj-fetcher.md)** | Baixa, descompacta e converte todos os fragmentos da base de CNPJs em Parquet altamente comprimido. |
