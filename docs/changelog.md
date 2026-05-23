---
title: Changelog do ecossistema Quantilica
description: Marcos importantes do ecossistema Quantilica — novos pacotes, mudanças de API, migrações de nomenclatura e marcos de documentação.
---

# Changelog

Marcos importantes do ecossistema como um todo. Cada pacote mantém seu próprio `CHANGELOG.md` no repositório do GitHub — este aqui é o resumo cross-pacote.

## 2026-05 — bcb-sgs-fetcher: remoção do suporte a Parquet (breaking change)

Reforço da separação de camadas: o fetcher volta a ser um **adaptador de fonte puro**.

- **`bcb-sgs-fetcher` (v0.4.0)** removeu `save_parquet`, `points_to_dataframe` e
  `SGS_CONTRACT` (módulos `writer`/`schema` deletados) e o extra `[parquet]`. A saída passa
  a ser apenas JSON/dataclasses; deps base só `quantilica-core` + scraping.
- **`bcb-sgs-sql`** continua lendo Parquet na Via B (papel da camada de ETL) e passou a
  declarar `polars` como dependência direta (depende do `bcb-sgs-fetcher` base, @v0.4.0).
- `rtn-fetcher` e `inmet-fetcher` **não** foram afetados — seguem exportando Parquet tipado.

## 2026-05 — Padronização das CLIs dos fetchers (breaking change)

Unificação do vocabulário de subcomandos das CLIs dos fetchers. **Mudança
incompatível**: scripts, cron jobs e contêineres que chamam os comandos
antigos precisam ser atualizados.

- **`sync` é o verbo único de download.** Substitui `trade` (comex), `fetch`
  (bcb-sgs, pdet), `data` (datasus) e `download` (tesouro-direto). `rtn` e
  `inmet` já usavam `sync`. Por padrão o `sync` baixa **tudo**, com seleção
  opcional de datasets.
- **Comandos fundidos.** Pré-visualização agora é a flag `--dry-run` do `sync`
  (substitui o comando `info` do tesouro-direto); o `all` do comex foi
  absorvido pelo `sync` sem argumentos; `docs`/`aux` do datasus viraram flags
  `--docs`/`--aux` do `sync`; o `latest` do rtn virou `sync --latest`.
- **Grupos aninhados.** `bcb-sgs` reorganizado em `series` (operações por
  série) e `catalogo` (catálogo de metadados — `catalogo sync` é o antigo
  `pipeline`); `sidra` agrupa `list pesquisas` / `list agregados`.
- **Novo subcomando `pipeline`** (`sync` → `convert`/`export`) em `rtn`,
  `pdet` e `tesouro-direto`.
- **`pdet-fetcher`** passou a ter `cli.py` próprio (antes a CLI nativa vivia
  em `__main__.py`).
- Norma atualizada em [Padronização de CLI para Fetchers](normas/cli-fetchers.md)
  com o vocabulário canônico de subcomandos.

## 2026-05 — Novos pacotes de infraestrutura e integração analítica

- **`quantilica-cloud`** lançado: plugin CLI para sincronizar manifestos de download com o catálogo na nuvem. Registrado via `quantilica.commands`; acessível como `quantilica cloud login/sync/status`. Offline-first por design.
- **`quantilica-catalog`** lançado: modelo de observação canônico (star schema) com adaptadores para BCB-SGS, RTN, INMET, Tesouro Direto e SIDRA. Resolve o cruzamento multi-fonte com um único `JOIN` em `indicator_id + geo_id + date`.
- **`quantilica-io` integrado nos fetchers**: `bcb-sgs-fetcher`, `rtn-fetcher` e `inmet-fetcher` agora exportam Parquet tipado via `save_parquet` / `write_to_parquet` com `DataContract` e manifesto embutido no header.
- **`bcb-sgs-fetcher` padronizado** para as convenções do workspace: logging estruturado, `HttpClient` em `data.py`, `ScraperClient` mantido com httpx direto por precisar de sessão stateful.

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
