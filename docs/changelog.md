---
title: Changelog do ecossistema Quantilica
description: Marcos importantes do ecossistema Quantilica — novos pacotes, mudanças de API, migrações de nomenclatura e marcos de documentação.
---

# Changelog

Marcos importantes do ecossistema como um todo. Cada pacote mantém seu próprio `CHANGELOG.md` no repositório do GitHub — este aqui é o resumo cross-pacote.

## 2026-07 — Primeiros pacotes do núcleo publicados no PyPI

**`quantilica-core`, `sidra-fetcher` e `sidra-sql` agora estão no PyPI.** O maior
bloqueador de adoção do ecossistema Sidra — a dependência `git+https` de
`quantilica-core` — foi removido. `pip install sidra-sql` passa a resolver toda a
cadeia (`sidra-sql` → `sidra-fetcher` → `quantilica-core`) direto do índice, sem
clonar o monorepo.

- **Instalação simplificada:** os três pacotes trocaram `pip install git+https://…`
  por `pip install <pacote>` / `uv add <pacote>`.
- **Dependências por versão de registro:** `sidra-fetcher` passa a depender de
  `quantilica-core>=0.3.1` e `sidra-sql` de `sidra-fetcher>=0.7.2` — ambos antes
  fixados via `git+https`. (`typer`/`rich` continuam fornecidos pelo host
  `quantilica-cli`, não pelos fetchers — ver [Arquitetura de CLI](concepts/arquitetura.md#arquitetura-de-cli).)
- **Publicação automatizada:** cada repositório ganhou um workflow de CI com
  **Trusted Publishing (OIDC)** via GitHub Actions, sem tokens de API de longa
  duração — TestPyPI primeiro, PyPI em seguida, a cada tag `v*`.
- Versões publicadas: `quantilica-core` 0.3.1, `sidra-fetcher` 0.7.3,
  `sidra-sql` 1.3.0.

## 2026-06 — Configuração global unificada sob `~/.config/quantilica/`

Todos os pacotes SQL do ecossistema passam a guardar configuração global sob um
namespace compartilhado, em vez de diretórios isolados por ferramenta.

- **`bcb-sgs-sql`** e **`sidra-sql`** moveram o arquivo de config de
  `~/.config/<pacote>/config.ini` para
  `~/.config/quantilica/<pacote>/config.ini`.
- Na primeira execução após a atualização, a ferramenta detecta o arquivo antigo
  e o **migra automaticamente**, emitindo um `UserWarning`. O arquivo antigo
  não é removido — exclusão manual após confirmação.
- No Windows o caminho raiz é `%APPDATA%\quantilica\`, via `platformdirs`.
- Norma documentada em [Configuração Global das Ferramentas](normas/configuracao.md).

## 2026-05 — `sidra-pipelines` 3.0/3.1: consolidação e expansão de pipelines IBGE

**Mudança incompatível de IDs de pipeline (2.0 → 3.0).** Scripts e workflows
que referenciam IDs de pipeline pelo nome antigo precisam ser atualizados.

- **Fusão de pipelines similares com `UNION`:** séries antes separadas em
  múltiplos pipelines foram unificadas — `inpc`/`ipca`/`ipca15` (inflação),
  `pim-pf-brasil`/`pim-pf-regional`, `sinapi custo_medio`/`custo_projeto`,
  `ipp` por categoria/cnae/grupo, `ppm` rebanhos/produção/exploração,
  `populacao` censo/contagem/estimativas.
- **3.1:** novos pipelines SNIPC — índice de difusão e série de número-índice
  geral da inflação.
- Catálogo do README sincronizado com todos os pipelines ativos.

## 2026-05 — `bcb-sgs-pipelines` lançado: catálogo de pipelines macro BCB

Novo repositório de pipelines declarativos para séries do BCB SGS.

- **Seed inicial:** 6 pipelines macro — preços, juros, câmbio, atividade,
  crédito e monetário.
- **Expansão posterior:** pipelines de commodities e fluxo cambial adicionados,
  colunas em português legível por humanos.
- Segue o mesmo padrão declarativo do `sidra-pipelines` (`fetch.toml` +
  `transform.sql`), consumindo `bcb-sgs-sql` como motor de carga.

## 2026-05 — `sidra-sql` 1.3.0: export CSV com snapshot as-of e vintage storage

- **Vintage storage** na tabela `dados`: versionamento por modificação —
  cada carga preserva a revisão anterior em vez de sobrescrever, permitindo
  reconstruir o dado "como estava em" qualquer data.
- **Novo comando `export`**: exporta os dados para CSV com semântica
  *snapshot as-of* — o usuário escolhe a data de referência e recebe o
  dado válido naquele momento.
- `ensure_vintage_schema` virou no-op real após a migração (sem regressão em
  bases já atualizadas).

## 2026-05 — `bcb-sgs-sql` lançado (v0.1.1)

Novo pacote para carregar séries temporais do BCB SGS no PostgreSQL.

- Consome os dados baixados pelo `bcb-sgs-fetcher` (Via B: JSON-only) e os
  insere em schema PostgreSQL com tipo correto por série.
- **Cache com TTL configurável** (`cache_ttl_hours`): dados recentes não são
  re-baixados em execuções consecutivas do dia.
- **Barras de progresso** no fluxo de `run`: etapas de metadados, download e
  carga exibidas em tempo real.
- Carrega **metadados combinados** (nomes, unidades, periodicidade) dos arquivos
  mesclados do fetcher.
- Remove temas sem séries na subárvore ao carregar metadados (sem entradas
  órfãs).

## 2026-05 — `quantilica-core` 0.3.0: helpers de CLI, FTP monitorado e proveniência expandida

- **`expand_years_cli`** em `quantilica.core.cli`: expande intervalos `INICIO:FIM`
  com mensagens amigáveis via console Rich — adotado por todos os fetchers com
  argumento de anos.
- **`MonitoredFTP`**: cliente FTP com idle-timeout e interrupção de transferência
  — resolve travamentos silenciosos em servidores DATASUS.
- **`progress_callback`** em `download_with_manifest`: permite que plugins
  alimentem barras de progresso de bytes sem acoplamento ao Rich.
- **`manifest_version`** e grupos de proveniência rica nos manifestos: rastreamento
  de versão do schema de manifesto e campos de contexto detalhados.
- **`head_or_get` fallback**: resiliência para servidores que não suportam `HEAD`
  na verificação de `Last-Modified`.

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

- **`quantilica-catalog`** lançado: modelo de observação canônico (star schema) com adaptadores para BCB-SGS, RTN, INMET, Tesouro Direto e SIDRA. Resolve o cruzamento multi-fonte com um único `JOIN` em `indicator_id + geo_id + date`. O modelo geográfico foi posteriormente generalizado (breaking change interna) para suportar múltiplas granularidades geográficas.
- **`quantilica-analytics` 0.2.0** acrescentou `read_brazilian_csv`: leitura robusta de CSV com encoding CP-1252/Latin-1, separadores `;`, datas em DD/MM/AAAA e notação decimal brasileira — em uso pelos fetchers que consomem planilhas do governo.
- **`quantilica-analytics` integrado nos fetchers**: `bcb-sgs-fetcher`, `rtn-fetcher` e `inmet-fetcher` agora exportam Parquet tipado via `save_parquet` / `write_to_parquet` com `DataContract` e manifesto embutido no header.
- **`bcb-sgs-fetcher` padronizado** para as convenções do workspace: logging estruturado, `HttpClient` em `data.py`, `ScraperClient` mantido com httpx direto por precisar de sessão stateful.

## 2026-05 — Reescrita do portal de documentação

- Portal reestruturado com narrativa de três atos no `index.md`.
- Nova seção **Fundações** elevando `quantilica-core` e `quantilica-analytics` à navegação principal.
- Página **Proveniência & Manifestos** explicando o desenho de reprodutibilidade.
- Cookbook expandido para 6+ receitas cobrindo macro, finanças, saúde, clima, engenharia de dados e time travel.
- Páginas por persona: analista macro, cientista de saúde, engenheiro de dados, pesquisador acadêmico.
- Open Graph + Twitter Cards via `overrides/main.html` (sem dep extra).

## 2026-Q1 — `quantilica-analytics` lançado

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

- [bcb-sgs-fetcher](https://github.com/Quantilica/bcb-sgs-fetcher/releases)
- [bcb-sgs-sql](https://github.com/Quantilica/bcb-sgs-sql/releases)
- [bcb-sgs-pipelines](https://github.com/Quantilica/bcb-sgs-pipelines/releases)
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
- [quantilica-analytics](https://github.com/Quantilica/quantilica-analytics/releases)
- [quantilica-cli](https://github.com/Quantilica/quantilica-cli/releases)
- [quantilica-catalog](https://github.com/Quantilica/quantilica-catalog/releases)
