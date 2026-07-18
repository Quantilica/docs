# Visão Estratégica e Roadmap

Visão estratégica do Ecossistema Quantilica para dados abertos brasileiros.

---

## Visão de Futuro

A Quantilica é um **ecossistema de dados aberto com SDK** — a camada de confiança entre o
analista e a instabilidade das fontes oficiais brasileiras. A direção de longo prazo se
apoia em três pilares:

- **Cobertura** — uma ferramenta resiliente por fonte pública relevante, todas sob os mesmos princípios.
- **Ativos analíticos prontos** — sair de "arquivos brutos" para Parquet tipado, com proveniência e *time travel* embarcados.
- **Confiabilidade observável** — saúde das fontes monitorada e visível, para que quebras externas virem alertas, não surpresas.

---

## Quick wins (DX)

Melhorias de baixo custo e alto impacto na experiência do desenvolvedor, fora da trilha das fases estratégicas:

- **Template de Projeto (Boilerplate)** — repositório template com `hatchling`, `ruff`, `pytest` e `quantilica-core` pré-configurados, mais GitHub Actions base para teste e lint automático. *(Parcialmente entregue: o padrão de empacotamento e o processo de release já estão documentados em [Publicação e Release](normas/publicacao.md), com workflows `test.yml`/`publish.yml` em uso nos 6 pacotes publicados; falta o repositório-template em si.)*

## Roadmap de Execução Detalhado

O desenvolvimento da Quantilica está estruturado em ciclos incrementais que definem a direção técnica e de produto do ecossistema.

### Fase 1: Confiança, Estabilidade e Qualidade
*Objetivo: Transformar a Quantilica na camada de confiança entre os usuários e a instabilidade das fontes oficiais.*

1.  **Sistema de Observabilidade Proativa (Health Checks)**:
    *   Implementar cron jobs semanais que testam a conectividade e integridade dos endpoints governamentais.
    *   Criar uma "Status Page" pública informando se uma fonte (ex: FTP do DATASUS) está instável.
    *   Alertas automáticos via GitHub Issues quando um fetcher falhar por mudança externa.
2.  **Padronização Rigorosa de CI/CD** *(parcialmente entregue)*:
    *   ✅ Matrix de testes em Python 3.12 e 3.13 para todos os pacotes (workflow `test.yml`).
    *   ✅ Bloqueio de PRs que não atendam às regras do `ruff` (`ruff check` + `ruff format --check` no CI).
    *   ✅ Publicação automatizada no PyPI via Trusted Publishing (workflow `publish.yml`) — ver [Publicação e Release](normas/publicacao.md).
    *   ⏳ Obrigatoriedade de 80%+ de cobertura de testes para novos PRs.
3.  **Distribuição via Container (Docker Oficiais)**:
    *   Publicar imagens Docker no GitHub Container Registry (GHCR) para cada fetcher.
    *   Suporte a arquiteturas múltiplas (amd64, arm64).
    *   Permitir execução via: `docker run quantilica/inmet-fetcher --year 2024`.

### Fase 2: Evolução Técnica (Data Access Layer)
*Objetivo: Mover o processamento de "arquivos brutos" para "ativos analíticos prontos".*

1.  **Analytical-Ready (Foco em Parquet)**:
    *   Garantir que todo download possa ser automaticamente convertido em Parquet tipado.
    *   Injeção de hashes de proveniência no header dos arquivos Parquet.
2.  **Governança via Contratos de Dados (Data Contracts)**:
    *   Implementar validação de schema no momento da leitura (`ParseError` preventivo).
    *   Detectar se a fonte oficial removeu colunas ou alterou tipos de dados silenciosamente.
    *   Versionamento de schemas no `catalog.json`.
3.  **Proveniência Avançada e Imutabilidade**:
    *   Integrar os hashes SHA256 dos manifestos em um sistema de armazenamento endereçável por conteúdo (CAS).
    *   Habilitar o "Time Travel": capacidade de referenciar exatamente o conjunto de dados usado em uma pesquisa científica passada.
4.  **Ingestão Inteligente (Smart Sync)**:
    *   Desenvolver o `State Store` para rastrear fatias (partições) já baixadas.
    *   Lógica de download incremental (delta) para economizar banda e tempo em datasets volumosos.

### Fase 3: Produto e Ecossistema
*Objetivo: Oferecer conveniência máxima e dados pré-processados.*

1.  **Sustentabilidade**:
    *   Estabelecer modelos de apoio e governança comunitária para garantir a longevidade do projeto.

---

## Comunidade e Sustentabilidade

Transformar a Quantilica em referência para a comunidade analítica brasileira e garantir sua longevidade:

*   **Quantilica Cookbook:** notebooks com cruzamentos de alto valor (ex.: *"como o desemprego do CAGED se correlaciona com a inflação do IPCA em SP"*).
*   **Presença técnica (storytelling):** artigos sobre os desafios de minerar FTPs do DATASUS e APIs obsoletas.
*   **GitHub Sponsors / Open Collective:** sustentabilidade e transparência financeira para os custos de infraestrutura.

---
*Atualizado em: 18 de julho de 2026*
