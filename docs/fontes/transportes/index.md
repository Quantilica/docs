---
title: Transportes — ANTT e Infosiga-SP
description: Dados abertos de transporte terrestre da ANTT (rodovias, cargas, passageiros, ferrovias) e de sinistros de trânsito do Infosiga-SP.
---

# Transportes

## O desafio

A ANTT publica mais de cem pacotes de dados abertos em um portal protegido por WAF, com arquivos multi-ano e nomes que mudam. O Infosiga-SP entrega, em um único ZIP, várias tabelas de sinistros de trânsito divididas em faixas de anos. Os dois coletores tratam cada membro de arquivo como origem própria no lake, para não perder linhas.

## Pacotes

| Ferramenta | O que faz |
|---|---|
| **[antt-fetcher](antt-fetcher.md)** | Coleta 35 pacotes R1 do CKAN da ANTT (mais um XLSX do gov.br) dos 106 catalogados e converte 5 conjuntos para Parquet por `ano`. |
| **[infosiga-fetcher](infosiga-fetcher.md)** | Baixa sinistros, pessoas e veículos do Infosiga-SP e converte para Parquet por `ano`. |

## Próximos passos

- Para dados de rodovias, ferrovias e transporte de cargas e passageiros: **[antt-fetcher](antt-fetcher.md)**.
- Para sinistros de trânsito no Estado de São Paulo: **[infosiga-fetcher](infosiga-fetcher.md)**.
- Antes de rodar um download grande, confira o [estado das fontes](../../status.md).
