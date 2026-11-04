---
title: Energia Elétrica — dados abertos do ONS
description: Carga, geração, hidrologia, preços e intercâmbio do sistema elétrico brasileiro, do Operador Nacional do Sistema Elétrico (ONS).
---

# Energia Elétrica (ONS)

## O desafio

O ONS publica seus dados abertos em um catálogo CKAN que aponta para um bucket S3 público. Os diretórios e os nomes dos arquivos mudaram com o tempo, alguns conjuntos têm uma faixa anual antiga e uma faixa mensal recente, e há dezenas de conjuntos em oito áreas. O `ons-fetcher` mantém o catálogo declarativo, detecta mudanças na fonte com `discover` e converte o acervo para o lake.

## Pacotes

| Ferramenta | O que faz |
|---|---|
| **[ons-fetcher](ons-fetcher.md)** | Coleta 23 conjuntos R1 dos 87 catalogados (carga, hidrologia, geração, preços, intercâmbio, cadastros) e converte para Parquet particionado por `ano` e `mes`. |

## Próximos passos

- Para baixar e converter: vá para **[ons-fetcher](ons-fetcher.md)**.
- Antes de rodar um download grande, confira o [estado das fontes](../../status.md).
