---
title: inep-fetcher — Microdados do INEP
description: Downloader dos microdados do INEP (ENEM, SAEB, ENADE e outros grupos do catálogo).
---

# `inep-fetcher`

O `inep-fetcher` baixa os microdados abertos do INEP, organizados em grupos (`enem`, `saeb`, `enade` e outros). O histórico completo passa de 20 GB. O pacote só baixa: não extrai nem converte os arquivos.

## Instalação

```bash
quantilica install inep
```

## Características

- **Catálogo por grupo:** `quantilica inep list` mostra os grupos disponíveis (ENEM, SAEB, ENADE, ANA, Encceja e outros).
- **Download concorrente:** `sync` baixa em paralelo (`--workers`) e pula os arquivos locais que já estão atualizados; `check` mostra o plano antes de baixar.
- **Manifestos SHA-256:** cada download grava um manifesto de proveniência.

## Como Usar

Baixando os microdados do ENEM (um grupo do catálogo; `quantilica inep list` mostra todos):

```bash
quantilica inep sync enem -o ./data/inep
```

Os arquivos são baixados no formato de origem (ZIP).
