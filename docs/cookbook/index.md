---
title: Cookbook — Receitas analíticas com dados públicos brasileiros
description: Recipes prontas em Python combinando IBGE, Tesouro, DATASUS, INMET, CAGED, RAIS e Comex em pipelines analíticos coerentes.
---

# Cookbook

Receitas que combinam múltiplos domínios da plataforma para resolver problemas analíticos reais. Cada receita é auto-contida, com código executável e referências cruzadas aos pacotes e conceitos relevantes.

O Cookbook é o lugar onde **Modularidade** sai do princípio abstrato para a prática: ferramentas independentes, sem acoplamento, compostas em pipelines analíticos coerentes.

## Receitas

### Macroeconomia

- **[A Curva de Phillips brasileira em 30 linhas](curva-phillips.md)** — IPCA × Desemprego mensal, regressão e visualização. Só `sidra-fetcher`.
- **[Análise Econômica Multi-Fonte](analise-economica-multi-fonte.md)** — IPCA + yields do Tesouro + emprego: o painel macro completo. Combina três `-fetcher`.

### Finanças

- **[Yield Curve em 10 linhas](yield-curve.md)** — DI, Selic, IPCA+ — a curva inteira com Altair. Só `tesouro-direto-fetcher`.

### Saúde pública

- **[Mortalidade infantil × cobertura SUS por município](mortalidade-sus.md)** — SIM, SINASC, CNES e população do SIDRA em uma única tabela municipal. `datasus-fetcher` + `sidra-fetcher`.

### Clima

- **[Estiagem no Nordeste — 30 anos de INMET](estiagem-nordeste.md)** — série climática histórica, tendência por UF. Só `inmet-fetcher`.

### Engenharia de dados

- **[Balança comercial em uma query DuckDB](balanca-duckdb.md)** — `comex-fetcher` baixa GBs, DuckDB consulta direto o Parquet sem carregar em memória.

### Reprodutibilidade

- **[Reproduzir um paper de 2019 — Time Travel](time-travel.md)** — usar manifesto SHA-256 + SCD Type II do `sidra-sql` para defender um número exato anos depois.

---

Quer ver uma receita específica? Abra issue no repositório de docs.
