---
title: Changelog do ecossistema Quantilica
description: Marcos importantes do ecossistema Quantilica — novos pacotes, mudanças de API, migrações de nomenclatura e marcos de documentação.
---

# Changelog

Marcos importantes do ecossistema como um todo. Cada pacote mantém seu próprio `CHANGELOG.md` no repositório do GitHub — este aqui é o resumo cross-pacote.

## 2026-05 — Reescrita do portal de documentação

- Portal reestruturado com narrativa de três atos no `index.md`.
- Nova seção **Fundações** elevando `quantilica-core` e `quantilica-io` à navegação principal.
- Página **Proveniência & Manifestos** explicando o desenho de reprodutibilidade.
- Cookbook expandido para 6+ receitas cobrindo macro, finanças, saúde, clima, engenharia de dados e time travel.
- Páginas por persona: analista macro, cientista de saúde, engenheiro de dados, pesquisador acadêmico.
- Open Graph + Twitter Cards via `overrides/main.html` (sem dep extra).

## 2026-Q1 — `quantilica-io` lançado

- Camada analítica iniciada: reader multi-formato, writer Parquet com proveniência embarcada.
- Plano completo em [`QUANTILICA_IO_PLAN.md`](https://github.com/Quantilica/.github/blob/main/QUANTILICA_IO_PLAN.md).

## 2025-Q4 — Harmonização de nomenclatura

Renomeação dos repositórios para o padrão `<fonte>-fetcher`:

| Nome anterior | Nome atual |
|---|---|
| `comexdown` | **`comex-fetcher`** |
| `rtnpy` | **`rtn-fetcher`** |
| `tddata` | **`tesouro-direto-fetcher`** |
| `inmet-bdmep-data` | **`inmet-fetcher`** |
| `pdet-data` | **`pdet-fetcher`** |

Detalhes do racional em [Roadmap](roadmap.md).

## 2025 — `quantilica-core` lançado

- Pacote de fundação domain-neutral: `http`, `ftp`, `storage`, `manifests`, `metadata`, `logging`, `exceptions`.
- Adoção progressiva pelos coletores de domínio.

---

## Releases por pacote

Para releases granulares (PATCH/MINOR/MAJOR), consulte o `CHANGELOG.md` ou as releases do GitHub em cada repositório:

- [comex-fetcher](https://github.com/Quantilica/comex-fetcher/releases)
- [datasus-fetcher](https://github.com/Quantilica/datasus-fetcher/releases)
- [inmet-fetcher](https://github.com/Quantilica/inmet-fetcher/releases)
- [pdet-fetcher](https://github.com/Quantilica/pdet-fetcher/releases)
- [rtn-fetcher](https://github.com/Quantilica/rtn-fetcher/releases)
- [sidra-fetcher](https://github.com/Quantilica/sidra-fetcher/releases)
- [sidra-sql](https://github.com/Quantilica/sidra-sql/releases)
- [sidra-pipelines](https://github.com/Quantilica/sidra-pipelines/releases)
- [tesouro-direto-fetcher](https://github.com/Quantilica/tesouro-direto-fetcher/releases)
- [quantilica-core](https://github.com/Quantilica/quantilica-core/releases)
- [quantilica-io](https://github.com/Quantilica/quantilica-io/releases)
