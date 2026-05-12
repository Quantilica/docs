# Visão Estratégica e Roadmap

Este documento detalha o roadmap para transformar a Quantilica de uma coleção de ferramentas de extração em uma infraestrutura de referência para dados abertos no Brasil.

---

## 🚀 Visão de Futuro

A Quantilica deve se posicionar como uma **Data Platform hospedada com SDK aberto**. O valor do projeto reside na conveniência de fornecer dados públicos prontos para consumo analítico, abstraindo a instabilidade das fontes oficiais.

---

## 🗺️ Roadmap de Execução Detalhado

O desenvolvimento da Quantilica está estruturado em ciclos incrementais que movem a organização de um conjunto de utilitários para uma plataforma de dados resiliente.

### Fase 1: Unificação e Experiência do Desenvolvedor (DX)
*Objetivo: Reduzir a fricção de entrada para novos usuários e padronizar o consumo das ferramentas.*

1.  **Template de Projeto (Boilerplate)**:
    *   Criar repositório template com `hatchling`, `ruff`, `pytest` e `quantilica-core` pré-configurados.
    *   Incluir GitHub Actions base para teste e lint automático.

### Fase 2: Confiança, Estabilidade e Qualidade
*Objetivo: Transformar a Quantilica na camada de confiança entre os usuários e a instabilidade das fontes oficiais.*

1.  **Sistema de Observabilidade Proativa (Health Checks)**:
    *   Implementar cron jobs semanais que testam a conectividade e integridade dos endpoints governamentais.
    *   Criar uma "Status Page" pública informando se uma fonte (ex: FTP do DATASUS) está instável.
    *   Alertas automáticos via GitHub Issues quando um fetcher falhar por mudança externa.
2.  **Padronização Rigorosa de CI/CD**:
    *   Matrix de testes em Python 3.12 e 3.13 para todos os pacotes.
    *   Obrigatoriedade de 80%+ de cobertura de testes para novos PRs.
    *   Bloqueio de PRs que não atendam às regras do `ruff`.
3.  **Distribuição via Container (Docker Oficiais)**:
    *   Publicar imagens Docker no GitHub Container Registry (GHCR) para cada fetcher.
    *   Suporte a arquiteturas múltiplas (amd64, arm64).
    *   Permitir execução via: `docker run quantilica/inmet-fetcher --year 2024`.

### Fase 3: Evolução Técnica (Data Access Layer)
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

### Fase 4: Produto e Plataforma
*Objetivo: Oferecer conveniência máxima e dados pré-processados.*

1.  **Unified Portal**:
    *   Interface web para busca global em todas as fontes, visualização de amostras de dados e download direto de arquivos Parquet processados.
2.  **Sustentabilidade**:
    *   Estabelecer modelos de apoio e governança comunitária para garantir a longevidade do projeto.

---

## 📣 Marketing e Branding

Transformar a Quantilica em referência para a comunidade analítica brasileira:

### Táticas de Social Proof
*   **Quantilica Cookbook:** Repositório de Jupyter Notebooks com cruzamentos de alto valor: *"Como o desemprego do CAGED se correlaciona com a inflação do IPCA em SP"*.
*   **Presença Técnica (Storytelling):** Artigos em blogs (Medium/LinkedIn) sobre os desafios técnicos de minerar FTPs do DATASUS e APIs obsoletas.
*   **GitHub Sponsors / Open Collective:** Sinalizar seriedade e buscar sustentabilidade para custos de infraestrutura.

---

## ⚖️ Governança e Comunidade
*   **Sustentabilidade:** Avaliar modelos de apoio (GitHub Sponsors) para custear a infraestrutura de hospedagem de dados.
*   **Open Collective:** Transparência financeira para possíveis contribuições futuras.

---
*Atualizado em: 12 de maio de 2026*
