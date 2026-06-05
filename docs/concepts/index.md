# Conceitos Transversais

Esta seção explica o **porquê** e o **como funciona** do ecossistema — a forma do sistema e
as ideias que a sustentam. Para as **regras que o contribuidor segue** (versão, escrita,
CLI, `pyproject`, `.gitignore`), veja a seção [Desenvolvimento](../normas/python.md).

Quatro páginas formam a coluna conceitual. Leia em ordem se você é novo; consulte por referência caso já conheça o sistema.

## [Arquitetura do Ecossistema](arquitetura.md)

Como as partes se conectam: as quatro camadas (extração, processamento, armazenamento, análise), o modelo ELT, padrões de deployment (local, batch, streaming, multi-fonte) e características de performance.

**Leia primeiro** se você quer entender a forma do sistema.

## [Princípios de Design](principios.md)

Os cinco princípios que orientam toda decisão de projeto: **Modularidade**, **Resiliência**, **Performance**, **Reprodutibilidade** e **Sem Mágica**. Cada princípio inclui *por quê importa*, *como aplicamos* e exemplos anti-padrão vs. padrão.

**Leia depois da Arquitetura** para entender por que o sistema é assim.

## [Padrões Práticos](padroes.md)

Os oito padrões táticos que materializam os princípios em código: idempotência, concorrência explícita, Parquet em vez de CSV, lazy evaluation, auto-retry com backoff, validação de dados, gestão de memória, documentação inline.

**Consulte sob demanda** quando estiver implementando um pipeline.

## [Parquet + Polars](parquet-polars.md)

Tutorial dedicado ao formato e biblioteca centrais do ecossistema. Mostra workflows eficientes para datasets de 100MB a 100GB+, com exemplos cobrindo SIDRA, RAIS e Tesouro.

**Leia quando** for processar volumes grandes ou converter CSVs herdados.

## Aprofundamentos

Páginas conceituais focadas em um tema específico:

- **[Convenções de Armazenamento](storage.md)** — como os arquivos são nomeados e organizados.
- **[Proveniência & Manifestos](proveniencia.md)** — checksums SHA-256 e reprodução *time-travel*.
- **[Bulk Load & Versionamento de Revisões](bulk-load.md)** — ingestão via COPY e histórico de revisões nos warehouses SQL.
- **[Cálculo de Retornos de Renda Fixa](calculo-retornos-renda-fixa.md)** — a matemática de YTM, duration e retorno real.

---

## Matriz de decisão rápida

| Necessidade | Ferramenta do ecossistema |
|---|---|
| Dados macroeconômicos IBGE | `sidra-fetcher`, `sidra-sql` |
| Indicadores macroeconômicos BCB (SGS) | `bcb-sgs-fetcher`, `bcb-sgs-sql` |
| Títulos do Tesouro brasileiro | `tesouro-direto-fetcher`, `rtn-fetcher` |
| Emprego e mercado de trabalho | `pdet-fetcher` |
| Fluxos de comércio (import/export) | `comex-fetcher` |
| Vigilância de saúde pública | `datasus-fetcher` |
| Clima e meio ambiente | `inmet-fetcher` |
| Processamento de arquivos grandes | Polars |
| Análise estatística | Pandas, NumPy, Statsmodels |
| Dashboarding | PostgreSQL + ferramenta de BI |
| Previsão de séries temporais | Prophet, ARIMA, ML |
