# Conceitos Transversais

Quatro páginas formam a coluna conceitual da plataforma. Leia em ordem se você é novo; consulte por referência caso já conheça o sistema.

## [Arquitetura da Plataforma](arquitetura.md)

Como as partes se conectam: as quatro camadas (extração, processamento, armazenamento, análise), o modelo ELT, padrões de deployment (local, batch, streaming, multi-fonte) e características de performance.

**Leia primeiro** se você quer entender a forma do sistema.

## [Princípios de Design](principios.md)

Os cinco princípios que orientam toda decisão de projeto: **Modularidade**, **Resiliência**, **Performance**, **Reprodutibilidade** e **Sem Mágica**. Cada princípio inclui *por quê importa*, *como aplicamos* e exemplos anti-padrão vs. padrão.

**Leia depois da Arquitetura** para entender por que o sistema é assim.

## [Padrões Práticos](padroes.md)

Os oito padrões táticos que materializam os princípios em código: idempotência, concorrência explícita, Parquet em vez de CSV, lazy evaluation, auto-retry com backoff, validação de dados, gestão de memória, documentação inline.

**Consulte sob demanda** quando estiver implementando um pipeline.

## [Parquet + Polars](parquet-polars.md)

Tutorial dedicado ao formato e biblioteca centrais da plataforma. Mostra workflows eficientes para datasets de 100MB a 100GB+, com exemplos cobrindo SIDRA, RAIS e Tesouro.

**Leia quando** for processar volumes grandes ou converter CSVs herdados.

---

## Matriz de decisão rápida

| Necessidade | Ferramenta da plataforma |
|---|---|
| Dados macroeconômicos IBGE | `sidra-fetcher`, `sidra-sql` |
| Títulos do Tesouro brasileiro | `tddata`, `rtnpy` |
| Emprego e mercado de trabalho | `pdet-data` |
| Fluxos de comércio (import/export) | `comexdown` |
| Vigilância de saúde pública | `datasus-fetcher` |
| Clima e meio ambiente | `inmet-bdmep-data` |
| Processamento de arquivos grandes | Polars |
| Análise estatística | Pandas, NumPy, Statsmodels |
| Dashboarding | PostgreSQL + ferramenta de BI |
| Previsão de séries temporais | Prophet, ARIMA, ML |
