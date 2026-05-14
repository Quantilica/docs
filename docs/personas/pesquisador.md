---
title: Pesquisador acadêmico — caminho rápido na Quantilica
description: Séries longas, snapshots versionados, reprodutibilidade defensável em peer review. A stack Quantilica para ciência rigorosa.
---

# Pesquisador acadêmico

Você publica em journals, defende tese, ou produz nota técnica que será lida em audiência pública. Reprodutibilidade não é luxo — é requisito de defesa. Sua dor é específica: provar, três anos depois, que o número da Tabela 4 veio de uma versão exata do dado oficial que, na época, era diferente da atual.

## Suas três dores

| Dor | A ferramenta |
|---|---|
| Provar com qual versão de dado uma análise foi feita | **[Proveniência & Manifestos](../concepts/proveniencia.md)** |
| Reproduzir um paper de 2019 com dados de 2019, não de 2026 | **[`sidra-sql`](../ibge/sidra-sql.md)** (SCD Type II) |
| Séries longas com revisões silenciosas do IBGE/DATASUS | **[`quantilica-core`](../fundacoes/quantilica-core.md)** (manifestos SHA-256) |

## Por onde começar

1. **5 minutos:** leia [Proveniência & Manifestos](../concepts/proveniencia.md). É o coração metodológico do ecossistema para o seu caso de uso.
2. **15 minutos:** baixe um dataset (Quickstart [IBGE](../quickstart.md) ou [Saúde](../quickstart.md)) e abra o `.manifest.json` que ficou ao lado. É exatamente isso que você anexa ao apêndice de replicação.
3. **30 minutos:** se você trabalha com IBGE, suba `sidra-sql` em PostgreSQL e familiarize-se com o padrão SCD II — `WHERE modificacao <= '2024-01-15' AND ativo = TRUE` reproduz um snapshot histórico exato.

## O conceito que importa para você

> **[Reprodutibilidade](../concepts/principios.md#reprodutibilidade)** — toda transformação é determinística e auditável. Manifesto SHA-256, hash embarcado no Parquet, dimensão `modificacao` preservada no warehouse. É a infraestrutura mínima para que outro pesquisador, em outra década, refaça seus números sem chamar você.

## Padrões para defesa de tese

- **Versione manifestos no git do paper.** O arquivo bruto pode estar no Zenodo, em S3, no HD externo. Mas o `.manifest.json` (SHA-256 + URL + timestamp) entra no repositório de replicação. É leve e suficiente.
- **Anexe a query SQL com `modificacao <= snapshot_date`.** Se você usa `sidra-sql`, deixe explícito a data de corte. O grupo do referee consegue reproduzir mesmo se o IBGE revisar a série amanhã.
- **Sempre cite a versão do producer.** O manifesto guarda `producer` e `producer_version`. Reportar isso na metodologia é o mínimo defensável.
- **Cuidado com agregações pré-pandemia.** Vários datasets têm quebras estruturais em 2020. Sinalize datas de corte ou use dummies — não esconda.

## Caminho de aprofundamento

- [Proveniência & Manifestos](../concepts/proveniencia.md) — time travel real.
- [Princípios de Design](../concepts/principios.md) — todos os cinco; reprodutibilidade só funciona se os outros quatro também.
- [`sidra-sql` — Governança de Dados](../ibge/sidra-sql.md) — SCD II e snapshots históricos em SQL.
