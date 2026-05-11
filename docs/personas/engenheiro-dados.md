---
title: Engenheiro de dados — caminho rápido na Quantilica
description: Pipelines, warehouse, data contracts e proveniência criptográfica. A stack Quantilica para quem constrói a infraestrutura.
---

# Engenheiro de dados / ETL

Você é responsável pela infraestrutura que serve os analistas. Constrói pipelines reprodutíveis, atende SLAs de freshness, e responde quando o dashboard mostra valor errado. Não tem paciência para coletor frágil ou formato proprietário.

## Suas três dores

| Dor | A ferramenta |
|---|---|
| Cada nova fonte exigia retry, manifesto, logging e exceção customizada | **[`quantilica-core`](../fundacoes/quantilica-core.md)** |
| Encoding inconsistente, schemas mutantes, falta de tipagem na ingestão | **[`quantilica-io`](../fundacoes/quantilica-io.md)** (Data Contracts) |
| Carregar SIDRA em PostgreSQL com revisões preservadas (SCD II) | **[`sidra-sql`](../ibge/sidra-sql.md)** |

## Por onde começar

1. **5 minutos:** leia a [Arquitetura](../concepts/arquitetura.md). Entenda como `-fetcher`, `-sql` e `-pipelines` se conectam.
2. **15 minutos:** rode um pipeline declarativo via `sidra-sql plugin install ... --alias std && sidra-sql run std ipca`. Isso é o "fim do túnel" — pipelines como TOML versionado.
3. **30 minutos:** monte a receita **[Balança comercial em DuckDB](../cookbook/balanca-duckdb.md)** — `comex-fetcher` para baixar, DuckDB para consultar Parquet sem RAM.

## Os conceitos que importam para você

- **[Modularidade](../concepts/principios.md#modularidade)** — cada fetcher tem suas próprias deps e retry. Sem mega-fetcher.
- **[Resiliência](../concepts/principios.md#resiliência)** — backoff exponencial, retomada, idempotência.
- **[Proveniência & Manifestos](../concepts/proveniencia.md)** — SHA-256 ao lado de cada artefato, embarcado em Parquet.
- **[Parquet + Polars](../concepts/parquet-polars.md)** — o formato analítico padrão da plataforma.

## Padrões que escalam

- **Manifestos no git, dados fora.** Versionar `.manifest.json` no repositório do projeto, manter os arquivos em S3/MinIO. O manifesto é a fonte de verdade.
- **TOML > código Python para pipelines repetitivos.** O `sidra-sql` aceita pipelines declarativos. Versionados, lintáveis, lidos por não-devs.
- **`COPY FROM STDIN` em vez de `INSERT`.** 400k linhas/s vs horas para 10M linhas. O `sidra-sql` já faz isso.
- **SCD Type II sempre.** Nunca sobrescreva dado oficial; marque `ativo=FALSE` e insira nova versão. Auditoria gratuita.
- **DuckDB sobre Parquet.** Para queries ad-hoc em bilhões de linhas sem provisionar warehouse.

## Caminho de aprofundamento

- [`quantilica-core` — anatomia de um download](../fundacoes/quantilica-core.md)
- [`quantilica-io` — Parquet com proveniência embarcada](../fundacoes/quantilica-io.md)
- [`sidra-sql` — warehouse + SCD II](../ibge/sidra-sql.md)
- [Padrões Práticos](../concepts/padroes.md) — receitas táticas para casos comuns.
