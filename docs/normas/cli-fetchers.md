---
title: Padronização de CLI para Fetchers
description: "Norma da interface de linha de comando dos fetchers: cli.py (wrapper fino), plugin.py (Typer + Rich), logging, progresso, UX e entry points."
---

# Padronização de CLI para Fetchers

> Esta é a referência do **contribuidor**: como implementar convenções de CLI e armazenamento num fetcher. Para entender como os arquivos são organizados como **usuário final**, veja [Convenções de Armazenamento](../conceitos/storage.md).
>
> Para o contexto conceitual por trás destas regras, veja [Arquitetura de CLI](../conceitos/arquitetura.md#arquitetura-de-cli) (os dois níveis) e o padrão [UX de CLI: progresso vs. logs](../conceitos/padroes.md#cli-ux).

Este documento é o guia normativo para a construção de interfaces de linha de comando nos pacotes fetcher do ecossistema Quantilica. Cobre os dois níveis de interface que cada fetcher implementa: o **wrapper da CLI standalone** (`cli.py`) e o **plugin para o hub unificado** (`plugin.py`, Typer + Rich). A estrutura canônica de `cli.py` segue o ADR `2026-10-08-fetcher-cli-wrapper-e-canal-de-distribuicao`: para fetchers baseados no `FetcherApp`, `cli.py` é apenas um **wrapper fino** do app Typer do `plugin.py`; `argparse` completo ([§2](cli-fetchers/cli-nativa.md)) fica restrito a fetchers com comandos customizados fora do `FetcherApp` (hoje, `sidra-fetcher`).

Seguir este guia garante comportamento consistente entre fetchers, integração correta com `quantilica-cli` e UX homogênea para o usuário final.

---

## 1. Visão geral da arquitetura de dois níveis

Todo fetcher Quantilica expõe **dois pontos de entrada CLI** com responsabilidades distintas:

```
<pacote>/
├── src/<pacote>/
│   ├── cli.py       ← Wrapper fino do Typer do plugin (padrão) ou argparse (fetcher customizado)
│   └── plugin.py    ← Plugin para quantilica-cli (Typer + Rich)
```

| Dimensão | `cli.py` | `plugin.py` |
|---|---|---|
| Framework | Wrapper do app Typer do `plugin.py` (padrão) ou `argparse` (fetcher customizado) | `typer` + `rich` |
| Dependências extras | Nenhuma | `typer`, `rich` (fornecidos pelo host) |
| Ativado por | `<pacote>-fetcher [comando]` | `quantilica <fonte> [comando]` |
| Propósito | Exposição como script, automação | Experiência interativa, UX rica |
| Registro | `[project.scripts]` | `[project.entry-points."quantilica.fetchers"]` |
| Colorido / progresso | Rich (via `plugin.py`, no wrapper); tqdm: opcional em fetcher customizado (via core) | Sim |

**Import protegido é obrigatório** em todo `cli.py` wrapper de `FetcherApp`: `try/except ImportError` que imprime `instale via "quantilica install <fonte>"` e encerra com código **1** — nunca `ModuleNotFoundError` cru. Referência canônica: `bcb-sgs-fetcher/src/bcb_sgs_fetcher/cli.py`.

O `quantilica-cli` descobre plugins dinamicamente via entry points — nunca declara fetchers como dependências diretas. Isso mantém o hub leve e desacoplado.

### 1.1 Por que dois níveis?

- **UX superior no hub**: quando carregado via `quantilica-cli`, o ambiente já tem Typer e Rich disponíveis. O `plugin.py` usa isso sem declarar dependência.
- **Implementação única**: com o `FetcherApp`, a gramática de subcomandos (`sync`, `check`, `--from-plan`, ...) vive uma vez só em `plugin.py`; a `cli.py` apenas delega a ela, sem duplicar a lógica de CLI.
- **Instalação mínima apenas como biblioteca**: um usuário que consome o fetcher como biblioteca (`import`) não precisa de Typer nem Rich. **Executar a CLI standalone sem o host não é objetivo** (ADR `2026-10-08-fetcher-cli-wrapper-e-canal-de-distribuicao`): a instalação canônica é `quantilica install <fonte>`, que já traz o host; sem ele, o wrapper imprime `instale via "quantilica install <fonte>"` e sai com código 1. Aqui, `<fonte>` é a chave do `SOURCES_REGISTRY` (ver [§3.6](cli-fetchers/plugin.md)) — não necessariamente o nome do pacote.

### 1.2 Vocabulário canônico de subcomandos

Para que a CLis sejam previsíveis, todo fetcher usa o **mesmo verbo** para a
mesma intenção. Cada fetcher implementa apenas o subconjunto que faz sentido
para sua fonte, mas nunca inventa um nome alternativo para um verbo já
existente nesta tabela:

| Verbo | Significado | Default |
|---|---|---|
| `sync` | Baixar/atualizar os dados da fonte; idempotente (pula o que já está atualizado) | baixa **tudo**; aceita seleção opcional via argumento posicional ou `--dataset`; aceita `--from-plan` (plano do `check`) |
| `check` | **Obrigatório** (fetchers de arquivo estático): verificar remoto × local (HEAD por entrada) e emitir plano de freshness, **sem baixar**; `--json` gera plano consumível por `sync --from-plan` | — |
| `list` | Listar o que está disponível remotamente (datasets, tabelas, pesquisas) | — |
| `info` | Exibir metadados de **uma** entidade específica | — |
| `convert` | Converter dados brutos para Parquet/formato analítico | — |
| `export` | Exportar para formatos externos (Excel, SQLite) | — |
| `pipeline` | Encadear `sync` → `convert`/`export` com cabeçalhos de passo e resumo | — |
| `search` | Busca livre em índice ou catálogo remoto | — |
| `archive` | Mover arquivos desatualizados para diretório de histórico | — |
| `periods` | Listar os períodos disponíveis para uma entidade específica | — |

!!! note "Verbos de domínio"
    Verbos específicos do pacote são permitidos além desta tabela (ex: `archive` no `datasus-fetcher`, `periods` no `sidra-fetcher`). A regra é nunca reutilizar um verbo da tabela com semântica diferente.

Regras de ouro:

- **`sync` é o verbo de download.** Nunca use `download`, `fetch`, `trade`,
  `data` ou outro sinônimo para "baixar os dados da fonte".
- **`sync` baixa tudo por padrão.** A seleção de datasets é sempre opcional —
  omitir o argumento significa "sincronizar o conjunto completo".
- **Pré-visualização é uma flag, não um comando.** Use `--dry-run` no `sync`
  para listar o que seria baixado **sem tocar a rede**; não crie um comando
  `info`/`status` separado só para listar. `info` é reservado para metadados
  de uma entidade. Exceção: `check` (ADR 2026-10-07) não é listagem — é
  verificação remoto × local com plano consumível (`--json` →
  `sync --from-plan`), etapa operacional distinta do download.
- **Exceção declarada: `bcb-sgs-fetcher`** (ADR `2026-10-07-check-obrigatorio-e-sidra-sync-rename.md`): o SGS é uma API de séries temporais, consultada por janela de datas num endpoint REST dinâmico (`/dados/serie/bcdata.sgs.<n>/dados`), e não uma URL estável por arquivo. O fetcher grava um snapshot JSON por série e por dia (`--skip-existing` pula as séries cujo snapshot do dia já existe), sem o plano remoto × local do `check`. A carga no Postgres é responsabilidade do `bcb-sgs-sql`.

    !!! note "O que a API oferece (verificado em 2026-10-13, série 11)"
        A API aceita `HEAD`, não envia `Last-Modified` e devolve um `ETag` fraco que acompanha o corpo da resposta (muda com a janela pedida), com `304` para `If-None-Match`. Um `check` baseado nesse `ETag` seria viável; o ADR de 2026-10-07 o descartou por outro motivo e a exceção continua em vigor até que alguém o implemente.
- **Fetchers FTP (`pdet-fetcher`, `datasus-fetcher`) — `check` herdado é conforme.** Servidores
  FTP não provêm `HEAD` nem `Last-Modified` confiável; o `check` canônico do
  `FetcherApp` (HEAD sobre os mesmos URLs do `download_entry`) pressupõe
  HTTP estático. Ambos usam o `FetcherApp` com `FtpClient`. O `pdet-fetcher` herda o `check`,
  que devolve o veredito `metadata-unavailable` por não haver
  `HEAD`/`Last-Modified` no cliente FTP; o `datasus-fetcher` substitui o
  `check_entry` por uma sonda local (arquivo já presente = `skip`/atualizado,
  sem consultar o servidor) e serializa as entradas para que `check --json`
  alimente `sync --from-plan`. Ambos os comportamentos **são conformes para
  fins de obrigatoriedade** do `check` (§1.2). A checagem real para FTP via listagem
  remota (tamanho/mtime do diretório FTP) segue pendência registrada no plano
  `2026-10-08-conformidade-fetchers-auditoria-2026-10`. Fetchers FTP não devem
  simular um plano de freshness com dados que o protocolo não garante.
- **Agrupe quando houver mais de um eixo semântico.** Veja [§3.5](cli-fetchers/plugin.md) — fetchers como
  o `bcb-sgs` separam operações por série (`series sync`, `series metadata`) das
  operações de catálogo (`catalogo sync`, `catalogo metadata-bulk`).

### 1.3 O Padrão FetcherApp (Recomendado)

> **Novo (Agosto/2026):** Para reduzir o boilerplate, o `quantilica-cli` exporta a classe `quantilica.cli.sdk.FetcherApp`.

Fetchers padrão (que fazem download de datasets estruturados via HTTP estático) devem instanciar o `FetcherApp` em `plugin.py` e passar seus metadados, estrutura de catálogos (ex: `GROUPS`, `GROUP_ALIASES`) e uma factory de rotas (`path_builder`). Com isso, a `cli.py` atua apenas como wrapper de execução, removendo totalmente a necessidade de escrever `argparse`, subcomandos manuais, e formatações Rich descritas nas seções 2 a 5.

Fetchers mais complexos (como os baseados em FTP ou APIs REST paginadas, ex: `datasus-fetcher` e `sidra-fetcher`) não estão isentos desta regra: eles **devem** herdar da `FetcherApp` ou sobrepor seus comandos canônicos via `aliases_dict` e composição (`_build_commands`), e aproveitar o `FtpClient` do `quantilica-core` para manter o plugin alinhado à SDK padrão. Ressalva: o `sidra-fetcher` instancia o `FetcherApp` no `plugin.py`, mas mantém uma `cli.py` com `argparse` dedicado (única exceção, conforme o ADR 2026-10-08); logo, sua `cli.py` não é um wrapper fino.

As seções a seguir (2 a 5) devem ser aplicadas **apenas** para o entendimento da engenharia por trás do `FetcherApp` ou quando, em último caso, um fetcher precisar estender a CLI nativamente e customizar intensamente.

#### 1.3.1 Suporte a Lake Hive: `command_convert` e `command_pipeline`

Coletores que oferecem transformação de seus microdados para Parquet particionado em Hive utilizam os decorators do `FetcherApp`:

- **`fetcher.command_convert(func)`**: Registra o subcomando canônico `convert`. Expõe opções padronizadas (`-i/--input`, `--lake` / `-o/--output`, `--dataset`, `--force`, `--verbose`), delega para `func(input, lake, dataset=..., force=...)` e intercepta ausência de dependências analíticas.
- **`fetcher.command_pipeline(func)`**: Registra o subcomando canônico `pipeline`, encadeando o passo 1/2 (`sync`) e o passo 2/2 (`convert`). Suporta `--dry-run` para inspecionar os planos antes da execução.

```python
# plugin.py
from pathlib import Path
from typing import Any
from quantilica.cli.sdk import FetcherApp

fetcher = FetcherApp(name="pdet-fetcher", help="Microdados do PDET.")

def convert(input_dir: Path, lake_dir: Path, dataset: list[str] | None = None, force: bool = False) -> Any:
    from pdet_fetcher import lake
    return lake.converter.convert(input_dir, lake_dir, datasets=dataset, force=force)

fetcher.command_convert(convert)
fetcher.command_pipeline(convert)
```

#### 1.3.2 Fronteira autorizada do Lake Hive: `lake.py`

A escrita e conversão de dados para o lake analítico seguem estritamente a norma [Padronização de Lake Hive (Parquet)](lake.md).

- O módulo **`lake.py`** (ou submódulo `lake/`) dentro do coletor é a **única fronteira autorizada** para ingestão e gravação no lake.
- Dependências pesadas (`polars`, `duckdb`, `quantilica-analytics`) residem exclusivamente sob o extra opcional `[project.optional-dependencies]` no grupo `analysis`.
- Os coletores registram seus conversores no grupo de entry points **`quantilica.lake`** do `pyproject.toml` (ex.: `pdet = "pdet_fetcher.lake:converter"`), ao lado do entry point de comandos **`quantilica.fetchers`**.

!!! warning "Sobreposição de comandos do `FetcherApp` — paridade de flags"
    Um fetcher que re-registra `sync`/`list`/`check` por cima dos defaults do `FetcherApp` (caso `datasus-fetcher/plugin.py`, que re-registra `list` e `sync`; o `check` permanece o do SDK, com `check_entry` próprio) **deve** manter paridade de flags com o comando do SDK: o `sync` próprio inclui `--from-plan` (plano do `check`, já presente no `datasus-fetcher` desde 2026-10-08) e o `check` próprio inclui `--json`. No Typer, o último registro vence — a sobreposição substitui o default, não o estende; flags omitidas deixam de existir para o usuário.

### 1.4 Manifests de proveniência — o que é exigido de fetchers

- **`DownloadManifest` — obrigatório por arquivo baixado.** Todo arquivo baixado por um fetcher sai acompanhado do seu sidecar `DownloadManifest` (SHA-256, URL de origem, timestamps). O fetcher **não** o constrói manualmente: ele é provido por herança do `FetcherApp` — `FetcherApp._download_file` delega a `client.download_with_manifest` (`quantilica-cli/src/quantilica/cli/sdk.py`), implementado em `HttpClient.download_with_manifest` (`quantilica-core/src/quantilica/core/http.py`) e `FtpClient.download_with_manifest` (`quantilica-core/src/quantilica/core/ftp.py`), que faz freshness check, escrita atômica e emite o sidecar. Regra prática: baixe sempre via o caminho do `FetcherApp` (`download_entry`/`download_datasets`); nunca faça streaming próprio sem manifest.
- **`ExecutionManifest` — não exigido por download.** `ExecutionManifest` é apenas o alias de `RunManifest` (`quantilica-core/src/quantilica/core/manifests.py`), disponível no core e re-exportado em `quantilica.core`. O código não impõe sua produção a fetchers nem o SDK o emite no caminho de download — portanto **nenhum fetcher precisa produzi-lo por arquivo baixado**.

### 1.5 Arquétipos de coleta e cenários especiais

As fontes públicas brasileiras distribuem-se em **7 arquétipos canônicos de transporte e descoberta**, documentados em detalhe em [Cenários, arquétipos de fonte e casos especiais](cli-fetchers/cenarios-e-casos.md):

| Arquétipo | Protocolo / Descoberta | Exemplos de referência | Estratégia padrão |
|---|---|---|---|
| **1. Diretórios estáticos / FTP / WebDAV** | Autoindex HTML, `FtpClient` (`MLSD`/`LIST`) ou `PROPFIND` | `cvm-fetcher`, `rfb-cnpj-fetcher`, `pdet-fetcher`, `datasus-fetcher` | `FetcherApp` + `DataRepository`, `FreshnessPolicy` `head_or_manifest` |
| **2. Portais CKAN v3 + Storage S3/HTTP** | `GET /api/3/action/package_show?id=<slug>` | `tesouro-direto-fetcher`, `anp-fetcher`, `anac-fetcher` | Metadados extraídos do JSON CKAN (`last_modified`) propagados ao download |
| **3. APIs OData v4 (Olinda) e REST paginado** | Paginação `$top` / `$skip` com `$orderby` determinístico | `bcb-sgs-fetcher`, APIs Olinda, PNCP, SICONFI | Coleta particionada por janela temporal com snapshots JSON/CSV |
| **4. Handshake / Tokens efêmeros / Base64** | Parâmetros Base64 na rota ou token de curta duração | `b3-fetcher` | Resolução tardia (*lazy*) do token dentro de `download_entry` |
| **5. Elasticsearch POST (`search_after`)** | `POST /_search` com `sort` determinístico e cursor `search_after` | Buscadores processuais (ex.: DataJud) | Chave pública da API documentada + lotes `.jsonl` por partição |
| **6. Serviços geoespaciais OGC WFS 2.0** | `GetFeature` paginado (`count`, `startIndex`, `sortBy`) | GeoServer fundiário/ambiental (INCRA, CAR, ANA) | Fatiamento por UF/`BBOX` + conversão para `geom_wkb` (WKB) no Lake |
| **7. Endpoints dinâmicos sem `HEAD`** | `GET`/`POST` sem `Content-Length` ou `Last-Modified` | `anp-fetcher`, `inep-fetcher`, exportadores legados | `head_fallback_get` (`Range: bytes=0-0`) ou deduplicação SHA-256 + `check_payload` |

---

## Mapa da norma

A norma é dividida por assunto. Os números de seção (§) se mantêm em todas as páginas.

| Página | Seções | Quando consultar |
|---|---|---|
| Esta página | §1, §12, §13 | Arquitetura de dois níveis, vocabulário de subcomandos, `FetcherApp`, checklist e exemplos de referência |
| [CLI nativa](cli-fetchers/cli-nativa.md) | [§2](cli-fetchers/cli-nativa.md) | Fetcher customizado com `cli.py` em `argparse` |
| [Plugin](cli-fetchers/plugin.md) | [§3](cli-fetchers/plugin.md) | `plugin.py`, `setup_rich_logging`, comandos, extras opcionais, entry points |
| [Padrões visuais Rich](cli-fetchers/rich.md) | [§4](cli-fetchers/rich.md) | Status, barras de progresso, tabelas, painéis e mensagens |
| [Progresso e logging](cli-fetchers/progresso-e-logging.md) | [§5](cli-fetchers/progresso-e-logging.md), [§6](cli-fetchers/progresso-e-logging.md) | Callbacks de progresso e níveis de log |
| [Erros, fluxos e anti-padrões](cli-fetchers/erros-e-fluxos.md) | [§7](cli-fetchers/erros-e-fluxos.md) a [§11](cli-fetchers/erros-e-fluxos.md) | Códigos de saída, pipelines, dry-run, anos, contornos HTTP e o que evitar |
| [Cenários e casos especiais](cli-fetchers/cenarios-e-casos.md) | [§14](cli-fetchers/cenarios-e-casos.md) a [§18](cli-fetchers/cenarios-e-casos.md) | Arquétipos de fonte (HTTP, FTP, CKAN, OData, WFS), políticas de freshness, Soft-200 e casos especiais do Lake |

---

## 12. Checklist para novos fetchers

Use esta lista ao implementar ou revisar a CLI de um fetcher:

### `cli.py` — wrapper fino (padrão `FetcherApp`)

- [ ] Import do plugin **protegido**: `try/except ImportError` → imprime `instale via "quantilica install <fonte>"` em `sys.stderr` e sai com código **1** — nunca `ModuleNotFoundError` (referência: `bcb-sgs-fetcher/src/bcb_sgs_fetcher/cli.py`).
- [ ] `main(argv: list[str] | None = None)` — aceita argv para testabilidade (obrigatório).
- [ ] `main()` delega ao app na forma canônica `app(argv)`, com `if argv is None: argv = sys.argv[1:]` (nenhuma gramática de subcomando duplicada aqui; referência: `bcb-sgs-fetcher/src/bcb_sgs_fetcher/cli.py`). A forma antiga (`sys.argv = [sys.argv[0]] + argv; app()`, ainda presente em `anac`, `anp`, `cvm`, `inep`, `inmet`, `pdet`, `rfb-cnpj` e `rtn`) é tolerada até a próxima revisão de cada fetcher — fetchers novos usam `app(argv)` (já adotada em `bcb-sgs`, `comex`, `datasus`, `tesouro-direto` e `tse`).
- [ ] `cli.py` não importa `quantilica.cli.sdk`/`quantilica.cli.ui` diretamente — apenas o `plugin.py` ([§3.2](cli-fetchers/plugin.md)).
- [ ] Entry point declarado em `[project.scripts]`.

### `cli.py` — argparse (apenas fetcher customizado, ex: `sidra-fetcher`)

- [ ] `argparse.ArgumentParser` com `prog` e `description` definidos.
- [ ] `--version` com `action="version"` lendo de `__version__`.
- [ ] `-o`/`--output` com padrão `/data/<fonte>`.
- [ ] `--verbose` sem atalho `-v`.
- [ ] Subcomandos com `add_subparsers(dest="command", required=True)` **ou** `parser.set_defaults(func=lambda _: parser.print_help())` ([§2.1](cli-fetchers/cli-nativa.md)).
- [ ] Função de construção do parser nomeada **`get_parser()`** (não `set_parser`, não `get_args`).
- [ ] `main(argv: list[str] | None = None)` — aceita argv para testabilidade (obrigatório).
- [ ] `main()` chama `configure_cli_logging(verbose=args.verbose)` antes de qualquer I/O.
- [ ] Se exibir progresso: `logging.getLogger("quantilica.core").setLevel(logging.WARNING)` e `logging.getLogger("<pacote_fetcher>").setLevel(logging.WARNING)` quando `not verbose` ([§2.6](cli-fetchers/cli-nativa.md)).
- [ ] Erros fatais escrevem em `stderr` e encerram com `sys.exit(1)`.
- [ ] Entry point declarado em `[project.scripts]`.

### `plugin.py` (Typer + Rich)

- [ ] Docstring `"""Typer plugin for quantilica-cli integration."""`.
- [ ] `app = typer.Typer(help="...")` no topo (ou `app = FetcherApp(...).app`).
- [ ] `console = get_console()` compartilhado por todos os comandos próprios (importado de `quantilica.cli.ui`) — **apenas se o plugin define comandos próprios**; plugins 100% `FetcherApp` (ex.: `comex`, `rtn`) herdam do SDK e não o definem ([§3.2](cli-fetchers/plugin.md)).
- [ ] `_DEFAULT_OUTPUT = Path("/data/<fonte>")` — **apenas se o plugin define comandos próprios**; plugins 100% `FetcherApp` herdam o default do SDK ([§3.2](cli-fetchers/plugin.md)).
- [ ] Cada comando chama `setup_rich_logging(verbose, console=console)` como primeira linha.
- [ ] Funções de comando nomeadas `cmd_<verbo>` (ex: `cmd_sync`, `cmd_list`).
- [ ] Nenhum `typer.echo()` — apenas `console.print()`.
- [ ] Nenhum `print()` direto.
- [ ] `-o`/`--output` presente em todo comando que salva arquivos.
- [ ] `--verbose` presente em todo comando que faz I/O de rede.
- [ ] Operações únicas de rede usam `console.status(...)`.
- [ ] Operações bulk usam `Progress` com `console=console` (ou `Live + Group` para dois níveis — [§4.3](cli-fetchers/rich.md)).
- [ ] Callbacks (`on_progress`, `on_grupo`, `on_page`, `ProgressCallback`, `on_done`) separam display de lógica ([§5.2](cli-fetchers/progresso-e-logging.md)).
- [ ] Mensagens de sucesso usam `[green]✓[/green]`.
- [ ] Erros usam `[red]Erro:[/red]` + `raise typer.Exit(code=1)`.
- [ ] Avisos usam `[yellow]Aviso:[/yellow]`.
- [ ] Entry point declarado em `[project.entry-points."quantilica.fetchers"]`.
- [ ] Entry point de conversão declarado em `[project.entry-points."quantilica.lake"]` (quando houver suporte a conversão para lake Hive).
- [ ] `typer` e `rich` **não** estão em `[project.dependencies]`.
- [ ] **Fronteira**: `quantilica.cli.sdk`/`quantilica.cli.ui` são importados **somente aqui** — nenhum outro módulo do fetcher os importa ([§3.2](cli-fetchers/plugin.md)).
- [ ] **Fronteira do Lake**: a conversão para Parquet Hive vive exclusivamente em `lake.py` sob o extra `[analysis]`, exposta via `fetcher.command_convert()` e `fetcher.command_pipeline()` ([Padronização de Lake Hive](lake.md)).

---

## 13. Exemplos de referência no ecossistema

| Padrão | Fetcher de referência | Arquivo |
|---|---|---|
| Pipeline completo com Rule + Progress + resumo | `bcb-sgs-fetcher` | `plugin.py :: pipeline_cmd` (comando `catalogo sync`) |
| Callbacks `on_progress` / `on_grupo` / `on_page` | `bcb-sgs-fetcher` | `bulk.py` |
| `setup_rich_logging` — logging sem quebrar barras de progresso | `bcb-sgs-fetcher` | `plugin.py :: fetch` (qualquer comando) |
| `Live + Group` — duas barras simultâneas (itens + bytes) | `comex-fetcher` | `plugin.py :: sync` |
| `ProgressCallback` per-file + `_file_callback` | `comex-fetcher` | `plugin.py` |
| `on_done(filename, result)` callback pós-arquivo | `rtn-fetcher` | `plugin.py :: _sync_publications` |
| `console.status` + `asyncio.run()` para downloads async | `tesouro-direto-fetcher` | `plugin.py :: cmd_sync` |
| `getLogger("quantilica.core"/"<pacote>").setLevel(WARNING)` em cli.py | `sidra-fetcher` | `src/sidra_fetcher/cli.py :: main` |
| Wrapper fino de `plugin.py` com import protegido | `bcb-sgs-fetcher` | `cli.py` |
| Table com totais em rodapé | `datasus-fetcher` | `plugin.py :: cmd_list` |
| `console.status` em conexão FTP | `datasus-fetcher` | `plugin.py :: cmd_list` |
| Subcommands aninhados (`series_sub`, `catalogo_sub`) | `bcb-sgs-fetcher` | `plugin.py` |
| Expansão de intervalos de anos `2018:2020` | `comex-fetcher` | `plugin.py :: expand_years_cli` |
| Panel com metadados de entidade | `sidra-fetcher` | `plugin.py :: cmd_info` |
| `--dry-run` com tabela de pré-visualização | `datasus-fetcher` | `plugin.py :: cmd_sync` |
| Pipeline `sync` → `export`/`convert` | `rtn-fetcher` | `plugin.py :: cmd_pipeline` |
| `_print_info` como helper de tabela reutilizável | `tesouro-direto-fetcher` | `plugin.py :: _print_info` |
| `console.rule` / `console.print(Rule(...))` para seção | `tesouro-direto-fetcher` | `plugin.py :: cmd_pipeline` |

---

## Saiba mais

- [Arquitetura de CLI e Estratégia de Dependências](../conceitos/arquitetura.md#arquitetura-de-cli) — visão arquitetural de alto nível.
- [quantilica-cli](../fundacoes/quantilica-cli.md) — como o hub descobre e monta os plugins.
- [Padrões Práticos — UX de CLI](../conceitos/padroes.md#cli-ux) — padrão progresso vs. logs.
- [Padronização de Versão](python.md) — como expor `__version__` em argparse e Typer.