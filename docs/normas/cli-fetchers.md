---
title: Padronização de CLI para Fetchers
description: Guia normativo para a interface de linha de comando de fetchers Quantilica — cli.py (wrapper fino do plugin, com import protegido; argparse apenas para fetchers customizados) e plugin.py (Typer + Rich), logging, barras de progresso, UX e entry points.
---

# Padronização de CLI para Fetchers

> Esta é a referência do **contribuidor**: como implementar convenções de CLI e armazenamento num fetcher. Para entender como os arquivos são organizados como **usuário final**, veja [Convenções de Armazenamento](../concepts/storage.md).
>
> Para o contexto conceitual por trás destas regras, veja [Arquitetura de CLI](../concepts/arquitetura.md#arquitetura-de-cli) (os dois níveis) e o padrão [UX de CLI: progresso vs. logs](../concepts/padroes.md#cli-ux).

Este documento é o guia normativo para a construção de interfaces de linha de comando nos pacotes fetcher do ecossistema Quantilica. Cobre os dois níveis de interface que cada fetcher implementa: o **wrapper da CLI standalone** (`cli.py`) e o **plugin para o hub unificado** (`plugin.py`, Typer + Rich). A estrutura canônica de `cli.py` segue o ADR `2026-10-08-fetcher-cli-wrapper-e-canal-de-distribuicao`: para fetchers baseados no `FetcherApp`, `cli.py` é apenas um **wrapper fino** do app Typer do `plugin.py`; `argparse` completo (§2) fica restrito a fetchers com comandos customizados fora do `FetcherApp` (hoje, `sidra-fetcher`).

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
- **Instalação mínima apenas como biblioteca**: um usuário que consome o fetcher como biblioteca (`import`) não precisa de Typer nem Rich. **Executar a CLI standalone sem o host não é objetivo** (ADR `2026-10-08-fetcher-cli-wrapper-e-canal-de-distribuicao`): a instalação canônica é `quantilica install <fonte>`, que já traz o host; sem ele, o wrapper imprime `instale via "quantilica install <fonte>"` e sai com código 1. Aqui, `<fonte>` é a chave do `SOURCES_REGISTRY` (ver §3.6) — não necessariamente o nome do pacote.

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
- **Exceção declarada: `bcb-sgs-fetcher`** (ADR `2026-10-07-check-obrigatorio-e-sidra-sync-rename.md`): API de séries temporais (SGS): um endpoint REST dinâmico, sem `Last-Modified`/`ETag`/`Content-Length` de arquivo estático para comparar contra o snapshot JSON local, então o padrão `check` não se aplica. A freshness por série usa o metadado de última atualização da própria API (mecanismo distinto). A carga no Postgres é responsabilidade do `bcb-sgs-sql`.
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
- **Agrupe quando houver mais de um eixo semântico.** Veja §3.5 — fetchers como
  o `bcb-sgs` separam operações por série (`series sync`, `series metadata`) das
  operações de catálogo (`catalogo sync`, `catalogo metadata-bulk`).

### 1.3 O Padrão FetcherApp (Recomendado)

> **Novo (Agosto/2026):** Para reduzir o boilerplate, o `quantilica-cli` exporta a classe `quantilica.cli.sdk.FetcherApp`.

Fetchers padrão (que fazem download de datasets estruturados via HTTP estático) devem instanciar o `FetcherApp` em `plugin.py` e passar seus metadados, estrutura de catálogos (ex: `GROUPS`, `GROUP_ALIASES`) e uma factory de rotas (`path_builder`). Com isso, a `cli.py` atua apenas como wrapper de execução, removendo totalmente a necessidade de escrever `argparse`, subcomandos manuais, e formatações Rich descritas nas seções 2 a 5.

Fetchers mais complexos (como os baseados em FTP ou APIs REST paginadas, ex: `datasus-fetcher` e `sidra-fetcher`) não estão isentos desta regra: eles **devem** herdar da `FetcherApp` ou sobrepor seus comandos canônicos via `aliases_dict` e composição (`_build_commands`), e aproveitar o `FtpClient` do `quantilica-core` para manter o plugin alinhado à SDK padrão. Ressalva: o `sidra-fetcher` instancia o `FetcherApp` no `plugin.py`, mas mantém uma `cli.py` com `argparse` dedicado (única exceção, conforme o ADR 2026-10-08); logo, sua `cli.py` não é um wrapper fino.

As seções a seguir (2 a 5) devem ser aplicadas **apenas** para o entendimento da engenharia por trás do `FetcherApp` ou quando, em último caso, um fetcher precisar estender a CLI nativamente e customizar intensamente.

!!! warning "Sobreposição de comandos do `FetcherApp` — paridade de flags"
    Um fetcher que re-registra `sync`/`list`/`check` por cima dos defaults do `FetcherApp` (caso `datasus-fetcher/plugin.py`, que re-registra `list` e `sync`; o `check` permanece o do SDK, com `check_entry` próprio) **deve** manter paridade de flags com o comando do SDK: o `sync` próprio inclui `--from-plan` (plano do `check`, já presente no `datasus-fetcher` desde 2026-10-08) e o `check` próprio inclui `--json`. No Typer, o último registro vence — a sobreposição substitui o default, não o estende; flags omitidas deixam de existir para o usuário.

### 1.4 Manifests de proveniência — o que é exigido de fetchers

- **`DownloadManifest` — obrigatório por arquivo baixado.** Todo arquivo baixado por um fetcher sai acompanhado do seu sidecar `DownloadManifest` (SHA-256, URL de origem, timestamps). O fetcher **não** o constrói manualmente: ele é provido por herança do `FetcherApp` — `FetcherApp._download_file` delega a `client.download_with_manifest` (`quantilica-cli/src/quantilica/cli/sdk.py`), implementado em `HttpClient.download_with_manifest` (`quantilica-core/src/quantilica/core/http.py`) e `FtpClient.download_with_manifest` (`quantilica-core/src/quantilica/core/ftp.py`), que faz freshness check, escrita atômica e emite o sidecar. Regra prática: baixe sempre via o caminho do `FetcherApp` (`download_entry`/`download_datasets`); nunca faça streaming próprio sem manifest.
- **`ExecutionManifest` — não exigido por download.** `ExecutionManifest` é apenas o alias de `RunManifest` (`quantilica-core/src/quantilica/core/manifests.py`), disponível no core e re-exportado em `quantilica.core`. O código não impõe sua produção a fetchers nem o SDK o emite no caminho de download — portanto **nenhum fetcher precisa produzi-lo por arquivo baixado**.

---

## 2. CLI nativa — `cli.py` (Apenas fetchers customizados)

> **Escopo restrito (ADR `2026-10-08`):** `argparse` completo aplica-se apenas a
> fetchers com **comandos customizados fora do `FetcherApp`** — hoje, somente o
> `sidra-fetcher`. Todo fetcher novo baseado no `FetcherApp` **não** escreve a
> CLI nesta seção: usa o wrapper fino (§1.3).

### 2.1 Esqueleto obrigatório

```python
"""CLI standalone para <nome>-fetcher."""

from __future__ import annotations

import argparse
import sys

from <pacote> import __version__
from <pacote>.<modulo_principal> import <funcao_principal>


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="<pacote>-fetcher",
        description="<Descrição curta do fetcher>.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    # Alternativa quando não há subcomando padrão óbvio:
    # parser.set_defaults(func=lambda _: parser.print_help())
    # (sem required=True; mostra ajuda se nenhum subcomando for passado)

    # --- subcomando: sync ---
    sync = subparsers.add_parser("sync", help="Baixar/atualizar dados.")
    sync.add_argument(
        "-o",
        "--output",
        metavar="DIR",
        default="/data/<fonte>",
        help="Diretório de saída (padrão: /data/<fonte>).",
    )
    sync.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Exibir logs detalhados em vez de barra de progresso.",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = get_parser()
    args = parser.parse_args(argv)

    from quantilica.core.logging import configure_cli_logging
    configure_cli_logging(verbose=args.verbose)

    if args.command == "sync":
        _cmd_sync(args)


def _cmd_sync(args: argparse.Namespace) -> None:
    ...


if __name__ == "__main__":
    main()
```

Regras:

- A função que constrói o parser deve se chamar **`get_parser()`** — não `set_parser()`, não `get_args()`. Isso permite que testes e outros módulos obtenham o parser sem parsear argv.
- `main()` deve aceitar `argv: list[str] | None = None` para testabilidade via `main(["sync", ...])`. É obrigatório em todos os fetchers — omitir impede testes unitários de CLI.

### 2.2 Opções padronizadas

Todas as CLIs nativas devem implementar as seguintes opções de forma consistente:

| Opção | Forma curta | Padrão | Tipo | Descrição |
|---|---|---|---|---|
| `--output` | `-o` | `/data/<fonte>` | `Path` | Diretório de saída |
| `--verbose` | (nenhuma) | `False` | `bool` | Logs detalhados |
| `--version` | (nenhuma) | — | ação | Exibe versão e encerra |

!!! warning "Sem `-v` como atalho de `--verbose`"
    Nunca use `-v` como atalho de `--verbose`. Wrappers e orquestradores (Makefile, scripts shell, quantilica-cli) podem reservar `-v` para outros fins. Um único `--verbose` sem ambiguidade é o padrão do ecossistema.

### 2.3 Subcomandos recomendados

Os subcomandos seguem o **vocabulário canônico** definido em §1.2. A `cli.py`
nativa deve expor exatamente os mesmos verbos que o `plugin.py` do fetcher:

| Subcomando | Quando usar |
|---|---|
| `sync` | Baixar o conjunto principal de dados (tudo por padrão) |
| `list` | Listar o que está disponível (datasets, anos, etc.) |
| `check` | Verificar remoto × local sem baixar; `--json` gera plano consumível por `sync --from-plan` |
| `convert` | Converter de formato bruto para Parquet/JSON |
| `export` | Exportar para formatos externos (Excel, SQLite) |
| `info` | Exibir metadados de uma entidade |
| `pipeline` | Executar fluxo completo (vários passos encadeados) |
| `search` | Busca livre em índice ou catálogo remoto |

### 2.4 Registro no `pyproject.toml`

```toml
[project.scripts]
<pacote>-fetcher = "<modulo>.cli:main"
```

Exemplo real (comex-fetcher):

```toml
[project.scripts]
comex-fetcher = "comex_fetcher.cli:main"
```

### 2.5 Tratamento de erros

- Use `parser.error(mensagem)` para erros de argumento — encerra com código 2 e exibe o help.
- Para erros de execução, escreva em `sys.stderr` e encerre com código 1:

```python
import sys

def _cmd_sync(args):
    if not args.output.parent.exists():
        print(f"Erro: diretório pai não existe: {args.output.parent}", file=sys.stderr)
        sys.exit(1)
```

- Nunca use `raise SystemExit(1)` diretamente em funções de negócio — reserve para o nível de CLI.
- Não suprima exceções silenciosamente. Se não souber o que fazer com uma exceção, deixe propagar.

### 2.6 Silenciar logs INFO quando exibindo progresso

> **Só se aplica a fetcher customizado** (hoje, apenas `sidra-fetcher`, ADR `2026-10-08`) — wrappers finos não exibem progresso próprio nem tocam em loggers (§1.3).

`configure_cli_logging(verbose=False)` define o nível raiz em `INFO`. Isso faz com que mensagens internas do core (como `log_step` em `quantilica.core.http`) apareçam no terminal e corrompam a saída de barras tqdm.

Quando `cli.py` exibe progresso (barra tqdm ou output limpo), adicione após `configure_cli_logging`:

```python
def main(argv: list[str] | None = None) -> None:
    parser = get_parser()
    args = parser.parse_args(argv)
    configure_cli_logging(verbose=args.verbose)
    if not args.verbose:
        # Suprime log_step (INFO) do core e logs de rastreamento do fetcher
        logging.getLogger("quantilica.core").setLevel(logging.WARNING)
        logging.getLogger("<pacote_fetcher>").setLevel(logging.WARNING)
    args.func(args)
```

Onde `<pacote_fetcher>` é o nome do pacote do fetcher (ex: `"comex_fetcher"`, `"pdet_fetcher"`). São necessários dois `setLevel` porque `quantilica.core.*` usa o namespace `"quantilica.core"` e cada fetcher usa o namespace do seu próprio pacote — `get_logger(__name__)` retorna `logging.getLogger(name)` sem prefixo adicional. Evite `logging.getLogger().setLevel(WARNING)` (raiz) pois suprime loggers de terceiros como `httpx2`.

---

## 3. Plugin para `quantilica-cli` — `plugin.py`

### 3.1 Por que `plugin.py` existe

O `quantilica-cli` monta uma árvore de comandos a partir de todos os fetchers instalados:

```
quantilica
├── bcb-sgs      ← bcb_sgs_fetcher.plugin:app
├── comex        ← comex_fetcher.plugin:app
├── datasus      ← datasus_fetcher.plugin:app
├── inmet        ← inmet_fetcher.plugin:app
├── pdet         ← pdet_fetcher.plugin:app
├── rtn          ← rtn_fetcher.plugin:app
├── sidra        ← sidra_fetcher.plugin:app
└── td           ← tesouro_direto_fetcher.plugin:app
```

Cada nó da árvore é um `typer.Typer` exportado por `plugin.py` e descoberto via entry point.

A lógica de negócio compartilhada vive em **módulo próprio** (ex: `bulk.py`, `catalog.py`, `storage.py`). Não confie em `plugin.py` importando helpers de `cli.py` no modelo wrapper: `cli.py` é que importa `plugin.py` (um `import` no sentido inverso feria o modelo e criaria potencial circularidade). O antigo padrão "reutilizar helpers de `cli.py` no `plugin.py`" mantém-se tolerado apenas em fetchers customizados com argparse.

### 3.2 Cabeçalho obrigatório

```python
"""Typer plugin for quantilica-cli integration."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from quantilica.cli.sdk import FetcherApp

fetcher = FetcherApp(
    name="<pacote>-fetcher",
    help="<Descrição curta do fetcher.>",
    ...
)

app = fetcher.app

# Apenas em plugins com comandos próprios (além do FetcherApp):
_DEFAULT_OUTPUT = Path("/data/<fonte>")
```

Regras:

- O docstring do módulo deve ser exatamente `"""Typer plugin for quantilica-cli integration."""`.
- `app` deve ser o nome do objeto `typer.Typer` exportado (é o que o entry point aponta).
- `console = get_console()` deve ser instanciado no topo do módulo — **somente quando o `plugin.py` define comandos próprios**. Todos os comandos próprios compartilham a mesma instância. `get_console()` retorna um console global compartilhado pelo processo, garantindo intercalamento correto entre logs e barras de progresso. Plugins 100% `FetcherApp` (ex.: `comex`, `rtn` — sem comandos próprios) **não** definem `console`: herdam o console do SDK (cada `_build_commands` do `FetcherApp` resolve o seu via `get_console()` — `quantilica-cli/src/quantilica/cli/sdk.py`).
- `_DEFAULT_OUTPUT` define o caminho padrão de saída do fetcher. Deve ser `/data/<fonte>` para consistência com a convenção de montagem Docker do ecossistema — **somente quando o `plugin.py` define comandos próprios** (é o default dos `typer.Option("-o", "--output")` desses comandos). Plugins 100% `FetcherApp` **não** definem `_DEFAULT_OUTPUT`: herdam o output default do SDK (`default_output or Path(f"/data/{name.replace('-fetcher', '')}")` — `sdk.py`).
- Não importe `typer` ou `rich` no `pyproject.toml` do fetcher — essas dependências são fornecidas pelo host `quantilica-cli`.

!!! info "Fronteira com `quantilica.cli` (ADR `2026-10-08`)"
    A única fronteira pela qual o fetcher consome o host é `plugin.py` — e `cli.py`, que apenas o referencia/delega. `plugin.py` importa `FetcherApp` (e demais helpers de SDK) de **`quantilica.cli.sdk`** e helpers de console/log/progresso (`get_console`, `setup_rich_logging`, `make_download_progress`, `expand_years_cli`) de **`quantilica.cli.ui`**. **Nenhum outro módulo do fetcher** (clientes HTTP, FTP, readers, storage, parsers) pode importar `quantilica.cli.sdk`/`quantilica.cli.ui` — nem mesmo com fallback `try/except`. `quantilica.core.cli` não existe: os helpers estão em `quantilica.cli.ui`/`sdk`.

### 3.3 `setup_rich_logging` — o ponto central de logging

Cada `plugin.py` que escreve comandos próprios deve chamar `setup_rich_logging` de `quantilica.cli.ui` como primeira linha de cada comando:

```python
@app.command("sync")
def cmd_sync(
    verbose: Annotated[bool, typer.Option("--verbose", help="Logs detalhados")] = False,
) -> None:
    """..."""
    setup_rich_logging(verbose, console=console)
    ...
```

`setup_rich_logging` configura o logging via `RichHandler` apontando para o mesmo `console` das barras de progresso, garantindo intercalamento correto:

| Situação | Comportamento |
|---|---|
| `verbose=False` (padrão) | Apenas `WARNING` e `ERROR`; terminal limpo para Rich renderizar |
| `verbose=True` | `DEBUG` completo, formatado pelo `RichHandler`, intercalado com `Progress` |

#### Por que não `configure_cli_logging`?

`configure_cli_logging(verbose=False)` configura o nível para `INFO` com um handler padrão de stderr. Isso faz com que mensagens internas (como `log_step` em `quantilica.core.http`) apareçam no terminal e **corrompam barras de progresso Rich**, pois escrevem diretamente no stderr sem coordenação com o `Console`.

`setup_rich_logging` resolve em duas frentes:

1. **Nível padrão = `WARNING`** — sem ruído de INFO no terminal.
2. **`RichHandler(console=console)`** — quando `--verbose`, logs passam pelo mesmo objeto `Console` que as barras de progresso.

### 3.4 Estrutura de um comando completo

```python
@app.command("sync")
def cmd_sync(
    output: Annotated[
        Path,
        typer.Option("-o", "--output", help="Diretório de saída"),
    ] = _DEFAULT_OUTPUT,
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Logs detalhados")
    ] = False,
) -> None:
    """Baixar dados do <fonte>."""
    setup_rich_logging(verbose, console=console)
    with console.status("[cyan]Baixando dados...[/cyan]"):
        resultado = _chamar_logica_de_negocio()
    console.print(f"[green]✓[/green] Concluído: [bold]{resultado}[/bold]")
```

Regras:

- O docstring do comando (após `def cmd_*`) é exibido como descrição na ajuda — seja preciso e use imperativo no infinitivo ("Baixar", "Listar", "Converter").
- Todo parâmetro usa `Annotated[tipo, typer.Argument(...)]` ou `Annotated[tipo, typer.Option(...)]`.
- A opção `-o`/`--output` deve existir em todo comando que produz arquivos em disco.
- A opção `--verbose` deve existir em todo comando que realiza I/O de rede.
- Nenhum tipo deve ser `Optional[X]` — use `X | None`.

### 3.5 Comandos Analíticos e Dependências Opcionais

Fetchers são, por definição, ferramentas de extração leve. Subcomandos que exigem processamento de dados denso (como `convert` ou `pipeline`, que utilizam bibliotecas como `polars` ou `quantilica-analytics`) **não devem** impor essas dependências aos usuários que apenas desejam fazer o download (`sync`).

Nesses casos, adote o seguinte padrão:

1. Registre as dependências pesadas em `[project.optional-dependencies]` sob o grupo `analysis` no `pyproject.toml` do fetcher.
2. Atrase as importações do módulo de conversão (ex: `from .reader import convert`) para o momento da execução do comando, isolando em um bloco `try...except ImportError`.
3. Avise graciosamente o usuário caso o módulo não esteja disponível:

```python
@app.command("convert")
def cmd_convert(
    input: Annotated[Path, typer.Option("-i", "--input")] = Path("/data/fonte"),
) -> None:
    """Converter dados brutos para Parquet (requer extra 'analysis')."""
    try:
        from .reader import converte_dados
    except ImportError:
        console.print(
            "[red]Erro:[/red] convert requer extras de análise: "
            "pip install <pacote-fetcher>[analysis]"
        )
        raise typer.Exit(1) from None

    converte_dados(input)
```

4. Módulos analíticos (`reader`, `contracts`, `wrangling` ou equivalentes) que importam `polars` (ou outra dependência do extra `analysis`) diretamente **devem** converter a ausência do extra num `ImportError` de mensagem acionável — nunca `ModuleNotFoundError` cru. Padrão: guarda no topo do módulo que re-levanta com a instrução de instalação:

```python
try:
    import polars as pl
except ImportError as exc:
    raise ImportError(
        "requer o extra 'analysis': pip install '<pacote-fetcher>[analysis]'"
    ) from exc
```

Teste canônico da condição (c) do ADR `2026-10-08-fetcher-cli-wrapper-e-canal-de-distribuicao`, num ambiente **sem** o extra `analysis` instalado:

- `python -c "import <pacote>"` deve funcionar (o pacote base nunca exige o extra);
- `python -c "from <pacote>.reader import <simbolo>"` (ou `contracts`/`wrangling` importados diretamente) deve falhar com o `ImportError` acionável acima — nunca `ModuleNotFoundError` cru.

### 3.6 Subcommands aninhados

Para fetchers com mais de um eixo semântico, use `typer.Typer` aninhado. O
`bcb-sgs` separa operações **por série** das operações de **catálogo**:

```python
app = typer.Typer(help="Dados do SGS/BCB (séries temporais).")
series_sub = typer.Typer(help="Operações por série.")
catalogo_sub = typer.Typer(help="Catálogo de metadados do SGS/BCB.")
app.add_typer(series_sub, name="series")
app.add_typer(catalogo_sub, name="catalogo")

@series_sub.command("sync")
def cmd_series_sync(...) -> None:
    """Baixar dados de uma série temporal."""
    ...

@catalogo_sub.command("sync")
def cmd_catalogo_sync(...) -> None:
    """Sincronizar o catálogo completo de metadados (vários passos)."""
    ...
```

Isso produz:

```
quantilica bcb-sgs series sync 433
quantilica bcb-sgs series metadata 433
quantilica bcb-sgs catalogo sync
quantilica bcb-sgs catalogo metadata-bulk
```

Note que o verbo `sync` se repete em cada grupo — sempre com o mesmo
significado ("trazer o local em linha com o remoto"), apenas em escopos
diferentes. Use subcommands aninhados quando há mais de um grupo semântico
distinto. Para fetchers simples (3-6 comandos), um único nível é suficiente.

### 3.6 Registro no `pyproject.toml`

```toml
[project.entry-points."quantilica.fetchers"]
<nome-curto> = "<modulo>.plugin:app"
```

Exemplos reais:

```toml
# comex-fetcher/pyproject.toml
[project.entry-points."quantilica.fetchers"]
comex = "comex_fetcher.plugin:app"

# bcb-sgs-fetcher/pyproject.toml
[project.entry-points."quantilica.fetchers"]
bcb-sgs = "bcb_sgs_fetcher.plugin:app"

# sidra-fetcher/pyproject.toml
[project.entry-points."quantilica.fetchers"]
sidra = "sidra_fetcher.plugin:app"
```

O `<nome-curto>` é o que o usuário digitará: `quantilica <nome-curto>`. Use kebab-case quando necessário (`bcb-sgs`), mas prefira nomes de uma palavra quando possível.

> **Nota sobre instalação sob demanda:** O `quantilica-cli` descobre os entry points registrados em `quantilica.fetchers` automaticamente assim que o pacote é instalado via `quantilica install <fonte>`. Aqui, `<fonte>` é a chave do `SOURCES_REGISTRY` local (`quantilica-cli/src/quantilica/cli/sources.py`) mesclada com o `sources.json` remoto do índice (o local tem precedência), que mapeia chave → distribuição — não necessariamente o nome do pacote (ex.: `td` → `tesouro-direto-fetcher`). Chaves remotas atuais: `anac`, `anp`, `bcb-sgs`, `bcb-sgs-sql`, `comex`, `cvm`, `datasus`, `inep`, `inmet`, `pdet`, `rfb-cnpj`, `rtn`, `sidra`, `sidra-sql`, `tesouro-direto`, `tse`, `quantilica-analytics`, `quantilica-catalog`; o registro local tem também `td`. O comando resolve via `registry.get(source, source)` — chave desconhecida é passada adiante como nome de distribuição.

---

## 4. Padrões visuais Rich

### 4.1 Paleta de cores e estilos

Todos os fetchers usam a seguinte paleta semântica:

| Markup | Significado | Quando usar |
|---|---|---|
| `[cyan]` | Ação em andamento, identificadores | Nome de grupos sendo processados, títulos de tabelas |
| `[green]` | Sucesso | Confirmações de download, checkmarks `✓` |
| `[red]` | Erro | Mensagens de erro, valores inválidos |
| `[yellow]` | Aviso | Itens pulados, validações não-fatais |
| `[bold]` | Ênfase | Números importantes, caminhos de arquivo |
| `[dim]` | Secundário | Caminhos longos, timestamps, contadores de baixa relevância |
| `[bold green]` | Sucesso com ênfase | Contadores finais positivos |
| `[bold red]` | Erro com ênfase | Contadores de falha |

### 4.2 `console.status` — operação única de rede

Use para operações que não têm progresso mensurável (uma única requisição HTTP, uma conexão FTP):

```python
with console.status("[cyan]Conectando ao FTP do DATASUS...[/cyan]"):
    ftp = fetcher.connect()

with console.status(f"[cyan]Baixando metadados da série {series_id}...[/cyan]"):
    htmls = scraper.request_metadata_html(series_id=series_id)

with console.status("[cyan]Buscando metadados RTN...[/cyan]"):
    metadata_html = fetch_publications_metadata()
```

O spinner aparece automaticamente enquanto o bloco `with` estiver ativo. Não use `console.status` para operações com progresso conhecido — use `Progress` nesse caso.

### 4.3 `Progress` — barras de progresso para operações bulk

Para operações com N itens conhecidos ou estimáveis:

```python
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

def _make_progress() -> Progress:
    """Cria uma Progress bar padronizada para operações bulk."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )
```

Sempre passe `console=console` para que o `Progress` use o mesmo objeto que o restante do plugin — sem isso, Rich pode abrir um novo console e o intercalamento com logs (`RichHandler`) fica incorreto.

#### Progresso com total conhecido

```python
with _make_progress() as progress:
    task = progress.add_task("[cyan]Baixando metadados...[/cyan]", total=len(ids))

    def on_progress(processed, total, ok, failed, skipped):
        progress.update(
            task,
            completed=processed,
            description=(
                f"[green]{ok}✓[/green]"
                f"  [red]{failed}✗[/red]"
                f"  [dim]{skipped} skip[/dim]"
            ),
        )

    resultado = bulk.fetch_metadata_bulk(..., on_progress=on_progress)
```

#### Progresso indeterminado (total desconhecido inicialmente)

Use `total=None` para iniciar indeterminado e atualize quando o total for descoberto:

```python
with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    MofNCompleteColumn(),
    TimeElapsedColumn(),
    console=console,
) as progress:
    task = progress.add_task("[cyan]Iniciando...[/cyan]", total=None)

    def on_grupo(nome: str, done: int, total: int) -> None:
        progress.update(
            task,
            completed=done,
            total=total,
            description=f"[cyan]{nome[:40]}[/cyan]",
        )

    bulk.fetch_arvore_grupos(..., on_grupo=on_grupo)
```

#### Downloads Paralelos e Progresso Concorrente

Para fetchers que baixam múltiplos arquivos onde é razoável paralelizá-los, adote o `concurrent.futures.ThreadPoolExecutor` e um **pool de barras concorrentes fixo** renderizadas via `make_download_progress`.
Este padrão evita a poluição do console (quando há centenas de arquivos) ao reciclar as barras de progresso ativas.
Exija um argumento `--workers` (padrão `4`) na CLI:

```python
import concurrent.futures
import threading
from quantilica.cli.ui import make_download_progress

# No comando:
lock = threading.Lock()

with make_download_progress(console=console) as progress:
    # 1. Pré-aloca exatamente `workers` barras invisíveis/inativas
    worker_task_ids = [
        progress.add_task("[dim]Inativo[/dim]", total=1) for _ in range(workers)
    ]
    available_tasks = worker_task_ids.copy()

    def _worker(entry: dict) -> bool:
        # 2. Worker adquire uma barra do pool ao iniciar
        with lock:
            task_id = available_tasks.pop(0)

        # Atualiza a barra imediatamente com o nome do arquivo
        progress.update(task_id, description=f"[cyan]{entry['id']}[/cyan]", completed=0, total=None)

        def on_bytes(downloaded: int, total: int) -> None:
            if downloaded == 0 and total == 0:
                progress.update(task_id, completed=0)
                return
            progress.update(
                task_id,
                completed=downloaded,
                total=total or None,
            )

        try:
            download_entry(entry, progress=on_bytes)
            return True
        finally:
            # 3. Limpa a barra e devolve ao pool
            with lock:
                progress.update(task_id, description="[dim]Inativo[/dim]", completed=0, total=1)
                available_tasks.append(task_id)

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
    futures = {}
    try:
        futures = {executor.submit(_worker, e): e for e in entries}
        for future in concurrent.futures.as_completed(futures):
            # atualizar barra geral, lidar com resultados, etc.
            pass
        executor.shutdown(wait=True)
    except KeyboardInterrupt:
        for future in futures:
            future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        raise
```

Isso garante o uso ótimo de rede e uma experiência interativa rica, sem poluir o terminal, enquanto os retornos globais (ok/falha) podem ser controlados por um `make_batch_progress` ou log à parte. Para casos nativamente assíncronos (`asyncio`), como o `tesouro-direto-fetcher` ou `rtn-fetcher`, aplique semáforos assíncronos e lógica similar de pop/append na lista `available_tasks`.

### 4.4 `Table` — exibição de dados tabulares

```python
from rich.table import Table

# Padrão mínimo
table = Table(show_header=True, header_style="bold")
table.add_column("ID", style="cyan", justify="right")
table.add_column("Nome", style="green")
table.add_column("Tamanho", justify="right")

for item in items:
    table.add_row(str(item.id), item.nome, f"{item.size / 2**20:.1f} MB")

console.print(table)
```

Convenções:

- `header_style="bold"` como padrão; use `"bold magenta"` ou `"bold yellow"` para tabelas secundárias.
- IDs numéricos: `style="cyan"`, `justify="right"`.
- Nomes e textos longos: `style="green"`, justificação padrão (left).
- Números e tamanhos: `justify="right"`.
- Metadados de baixa relevância: `style="dim"`.
- Totais em rodapé: imprimir separadamente com `console.print(f"[bold]Total:[/bold] ...")` após a tabela.

Exemplo completo do `datasus-fetcher`:

```python
t = Table(show_header=True, header_style="bold")
t.add_column("Dataset", style="cyan")
t.add_column("Arquivos", justify="right")
t.add_column("Tamanho", justify="right")

for dataset in sorted(targets):
    t.add_row(dataset, str(n), f"{size / 2**20:.1f} MB")

console.print(t)
console.print(f"[bold]Total:[/bold] {total_files} arquivos, {total_size / 2**30:.1f} GB")
```

### 4.5 `Panel` — metadados de uma entidade

Use para exibir informações detalhadas de um único item após busca:

```python
from rich.panel import Panel

lines = []
if basic.name:
    lines.append(f"[bold]{basic.name}[/bold]")
if basic.frequency:
    lines.append(f"Periodicidade: [cyan]{basic.frequency}[/cyan]")
if basic.unit:
    lines.append(f"Unidade: [cyan]{basic.unit}[/cyan]")
if basic.start_date or basic.end_date:
    lines.append(f"Período: [dim]{basic.start_date} → {basic.end_date}[/dim]")

console.print(Panel("\n".join(lines), title=f"Série {series_id}"))
```

Exemplo do `sidra-fetcher`:

```python
console.print(
    Panel(
        f"[bold cyan]{metadados.nome}[/bold cyan]\n[dim]{metadados.assunto}[/dim]",
        title=f"Agregado {metadados.id}",
    )
)
```

### 4.6 `Rule` — divisores de seção em pipelines

Use para separar visualmente passos de pipelines longos:

```python
from rich.rule import Rule

console.print(Rule("[bold]Passo 1/4: Árvore de grupos[/bold]"))
# ... execução do passo ...
console.print(Rule("[bold]Passo 2/4: Séries desativadas[/bold]"))
```

Substitui os antigos `typer.echo("=== Passo N/4 ===")`.

`console.rule("[bold]texto[/bold]")` é equivalente a `console.print(Rule("[bold]texto[/bold]"))` e pode ser preferido pela brevidade.

### 4.7 Mensagens de resultado padronizadas

Mensagem de sucesso simples:

```python
console.print(f"[green]✓[/green] Salvo em [dim]{outfile}[/dim]")
console.print(f"[green]✓[/green] [bold]{len(items)}[/bold] itens baixados.")
```

Sucesso com contadores (bulk):

```python
if failed_count:
    console.print(
        f"[yellow]⚠[/yellow]  {successful} OK · [red]{failed_count} falha(s)[/red]"
    )
else:
    console.print(
        f"[green]✓[/green]  [bold]{successful}[/bold] itens processados com sucesso."
    )
```

Erro fatal (antes de `raise typer.Exit(code=1)`):

```python
console.print(f"[red]Erro:[/red] {mensagem_de_erro}")
raise typer.Exit(code=1)
```

Aviso não-fatal:

```python
console.print(f"[yellow]Aviso:[/yellow] '{item}' não encontrado, pulando.")
```

Nenhum resultado:

```python
console.print("[yellow]Nenhum resultado encontrado.[/yellow]")
```

---

## 5. Padrão de callbacks para progresso em operações bulk

Quando a lógica de negócio (em `bulk.py` ou equivalente) executa N iterações e o plugin precisa mostrar progresso, use callbacks em vez de barras de progresso dentro da lógica de negócio.

### 5.1 Por que callbacks?

- A lógica de negócio não sabe se está sendo chamada por um CLI interativo, um script, um teste, ou outro contexto.
- Callbacks mantêm a lógica de negócio independente de Rich/tqdm.
- Permitem que o plugin controle 100% da apresentação.

### 5.2 Assinaturas padrão

O ecossistema usa três famílias de callback, escolhidas pelo tipo de operação:

| Família | Assinatura | Quando usar | Referência |
|---|---|---|---|
| **Bulk por item** | `on_progress(processed, total, ok, failed, skipped)` | N itens homogêneos com contadores ok/falha/skip | `bcb-sgs-fetcher bulk.py` |
| **Por grupo/página** | `on_grupo(nome, done, total)` / `on_page(page, n_pages)` | Operações com total descoberto ao vivo | `bcb-sgs-fetcher bulk.py` |
| **Por bytes de arquivo** | `ProgressCallback = (downloaded, total_bytes)` | Download de arquivo único; integra com `download_with_manifest(progress=cb)` | `comex-fetcher plugin.py` |
| **Pós-arquivo** | `on_done(filename, result)` com `result ∈ {"ok","skipped","failed"}` | N downloads paralelos onde cada arquivo reporta seu resultado ao terminar | `rtn-fetcher plugin.py` |

```python
from collections.abc import Callable
from quantilica.core.http import ProgressCallback  # Callable[[int, int], None]

# Bulk por item (N itens com total conhecido)
on_progress: Callable[[int, int, int, int, int], None] | None = None
# args: (processed, total, ok, failed, skipped)

# Por grupo (com total descoberto ao vivo)
on_grupo: Callable[[str, int, int], None] | None = None
# args: (nome_grupo, done, total)

# Por página
on_page: Callable[[int, int], None] | None = None
# args: (page, n_pages)

# Por bytes de arquivo (integra com HttpClient.download_with_manifest)
progress: ProgressCallback | None = None
# args: (downloaded_bytes, total_bytes); total_bytes=0 quando Content-Length ausente

# Pós-arquivo
on_done: Callable[[str, str], None] | None = None
# args: (filename, result) onde result ∈ {"ok", "skipped", "failed"}
```

### 5.3 Implementação na lógica de negócio

```python
def fetch_metadata_bulk(
    series_ids: list[int],
    scraper: ScraperClient,
    dest_dir: Path,
    sleeptime: float = 10,
    skip_existing: bool = False,
    on_progress: (
        Callable[[int, int, int, int, int], None] | None
    ) = None,
) -> tuple[int, int]:
    total = len(series_ids)
    successful = failed = skipped = processed = 0

    for series_id in sorted(series_ids):
        if skip_existing and (dest_dir / f"{series_id:06d}.json").exists():
            skipped += 1
            processed += 1
            if on_progress is not None:
                on_progress(processed, total, successful, failed, skipped)
            continue

        # ... lógica de fetch ...

        processed += 1
        if on_progress is not None:
            on_progress(processed, total, successful, failed, skipped)

    return successful, failed
```

Regras:

- Sempre guarde o callback em parâmetro com valor padrão `None` — a função deve funcionar sem callback.
- Chame o callback **após** atualizar os contadores, nunca antes.
- Chame o callback para **todos** os itens, incluindo pulados (skipped) — assim a barra de progresso avança corretamente.
- Não ponha lógica de display (print, tqdm, Rich) na lógica de negócio.

### 5.4 Consumo no `plugin.py`

```python
with _make_progress() as progress:
    task = progress.add_task("[cyan]0✓  0✗  0 skip[/cyan]", total=len(ids))

    def on_progress(
        processed: int,
        total: int,
        ok: int,
        failed: int,
        skipped: int,
    ) -> None:
        progress.update(
            task,
            completed=processed,
            description=(
                f"[green]{ok}✓[/green]"
                f"  [red]{failed}✗[/red]"
                f"  [dim]{skipped} skip[/dim]"
            ),
        )

    successful, failed_count = bulk.fetch_metadata_bulk(
        ids, scraper, dest_dir,
        sleeptime=sleeptime,
        skip_existing=skip_existing,
        on_progress=on_progress,
    )
```

---

## 6. Logging na lógica de negócio

### 6.1 Níveis permitidos por contexto

| Nível | Quando usar |
|---|---|
| `DEBUG` | Logs de rastreamento por item — "Fetching series 1234", "Skipping file X" |
| `INFO` | Marcos importantes de progresso com contexto amplo |
| `WARNING` | Situações anômalas mas recuperáveis — parse failure, ID mismatch |
| `ERROR` | Falhas que afetam um item mas não encerram o processamento |
| `CRITICAL` | Apenas para falhas que tornam impossível continuar |

### 6.2 O que demover para `DEBUG`

Logs que antes apareciam em `INFO` mas que constituem "barulho" em execuções normais devem ser demovidos para `DEBUG`. Exemplos reais do `bcb-sgs-fetcher`:

```python
# ❌ Antes — INFO emite uma linha por série, quebrando a barra de progresso
logger.info("Fetching metadata for series %d", series_id)

# ✅ Depois — DEBUG só aparece com --verbose
logger.debug("Fetching metadata for series %d", series_id)
```

Critério prático: se o log aparece N vezes dentro de um loop de N iterações, provavelmente deve ser `DEBUG`.

### 6.3 O que manter em `INFO` ou superior

- Marcos do início/fim de fases em pipelines de vários passos.
- Warnings de parsing — arquivos com dados inesperados.
- Session errors e retries.
- Mensagens de erro que identificam qual item falhou.

```python
# Manter em WARNING — o usuário precisa saber
logger.warning(
    "Series ID mismatch for %d (got %d), removing files",
    series_id,
    basic.series_id,
)

# Manter em ERROR — falha de sessão é relevante mesmo sem --verbose
logger.error("Session error for series %d: %s", series_id, exc)
```

---

## 7. Tratamento de erros e códigos de saída

### 7.1 Códigos de saída padronizados

| Código | Significado |
|---|---|
| `0` | Sucesso completo |
| `1` | Erro de execução (argumento inválido pós-parse, arquivo não encontrado, etc.) |
| `2` | Uso incorreto (argparse usa 2 automaticamente para erros de sintaxe) |

### 7.2 `typer.Exit` no `plugin.py`

```python
# Erro fatal com mensagem
console.print(f"[red]Erro:[/red] arquivo não encontrado: {ids_file}")
raise typer.Exit(code=1)

# Interrupção pelo usuário (Ctrl+C)
try:
    asyncio.run(_run())
except KeyboardInterrupt:
    console.print("[yellow]Download cancelado.[/yellow]")
    raise typer.Exit(code=130)
```

### 7.3 Confirmação antes de operações destrutivas ou muito longas

```python
@app.command("all")
def all_datasets(
    yes: Annotated[
        bool, typer.Option("-y", "--yes", help="Confirmar sem prompt")
    ] = False,
) -> None:
    """Baixar TUDO (todos os anos, todas as tabelas)."""
    if not yes:
        typer.confirm(
            "Isso pode demorar muito e usar vários GBs. Continuar?",
            abort=True,
        )
    download_all(...)
```

`abort=True` faz `typer.confirm` encerrar com `typer.Exit(code=1)` se o usuário responder "n".

### 7.4 Erros não-fatais em loops bulk

Erros que afetam um item dentro de um loop não devem encerrar toda a operação. Use logging e continue:

```python
for item in items:
    try:
        processar(item)
        successful += 1
    except Exception as exc:
        logger.error("Falha em %s: %s", item, exc)
        failed += 1
```

Ao final do loop, exiba o resumo:

```python
if failed:
    console.print(f"[yellow]⚠[/yellow]  {successful} OK · [red]{failed} falha(s)[/red]")
else:
    console.print(f"[green]✓[/green]  [bold]{successful}[/bold] itens processados.")
```

---

## 8. Pipelines de vários passos

Fetchers com fluxos de trabalho longos (ex: arvore-grupos → series-desativadas → extract-ids → metadata-bulk) devem implementar um comando `pipeline` que:

1. Exibe cabeçalhos de passo com `console.rule(...)`.
2. Executa cada passo com sua barra de progresso/spinner independente.
3. Captura exceções por passo para que o pipeline não encerre no primeiro erro.
4. Exibe uma tabela resumo ao final.

```python
@app.command("pipeline")
def pipeline_cmd(...) -> None:
    """Pipeline completo de metadados (4 passos)."""
    setup_rich_logging(verbose, console=console)
    results: dict[str, str] = {}

    # Passo 1
    console.print(Rule("[bold]Passo 1/4: Árvore de grupos[/bold]"))
    with Progress(..., console=console) as progress:
        task = progress.add_task("...", total=None)
        def on_grupo(nome, done, total):
            progress.update(task, completed=done, total=total,
                            description=f"[cyan]{nome[:40]}[/cyan]")
        try:
            bulk.fetch_arvore_grupos(..., on_grupo=on_grupo)
            results["Árvore de grupos"] = "[green]✓[/green]"
        except Exception as exc:
            results["Árvore de grupos"] = f"[red]✗ {exc}[/red]"

    # ... passos 2, 3, 4 ...

    # Resumo final
    console.print(Rule("[bold]Resumo do pipeline[/bold]"))
    summary = Table(show_header=True, header_style="bold")
    summary.add_column("Passo", style="cyan")
    summary.add_column("Resultado")
    for step, result in results.items():
        summary.add_row(step, result)
    console.print(summary)
```

---

## 9. Dry-run e listagem sem download

Fetchers com datasets grandes devem implementar `--dry-run` ou um subcomando `list`/`info` que exibe o que seria baixado sem fazer download efetivo:

```python
@app.command("sync")
def cmd_sync(
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Listar sem baixar")
    ] = False,
) -> None:
    """Baixar/atualizar dados da fonte."""
    if dry_run:
        # Mostra tabela de arquivos e tamanhos
        t = Table(show_header=True, header_style="bold")
        t.add_column("Dataset", style="cyan")
        t.add_column("Partição")
        t.add_column("Tamanho", justify="right")
        t.add_column("Path")
        # ... preenche a tabela ...
        console.print(t)
        console.print(f"\n[bold]Total:[/bold] {total_n} arquivos, {total_size / 2**30:.2f} GB")
        return

    # Download efetivo
    fetcher.download_data(...)
```

---

## 10. Expansão de anos e intervalos

Fetchers que aceitam anos como argumento devem suportar o formato de intervalo `INICIO:FIM`. Para evitar a duplicação manual de código, o ecossistema fornece utilitários no `quantilica-core` para lidar com essa expansão de maneira homogênea:

### 10.1 No Plugin Typer (`plugin.py`)

Use a função **`expand_years_cli`** importada de `quantilica.cli.ui`. Ela faz a expansão utilizando `expand_year_range` internamente e imprime avisos amigáveis no console compartilhado caso encontre algum formato inválido:

```python
from quantilica.cli.ui import expand_years_cli

@app.command("sync")
def cmd_sync(
    years: Annotated[
        list[str] | None,
        typer.Argument(help="Anos (ex: 2020) ou intervalos (2018:2020)"),
    ] = None,
) -> None:
    """Sincronizar dados."""
    # Retorna os anos informados ou expande a faixa padrão caso 'years' seja nulo
    years_list = expand_years_cli(years, default_range="2018:2026", console=console)
    for year in years_list:
        get_year(year=year, ...)
```

### 10.2 Na CLI nativa (`cli.py`)

> **Só se aplica a fetcher customizado** (hoje, apenas `sidra-fetcher`, ADR `2026-10-08`) — wrappers finos delegam anos/intervalos ao `plugin.py` e não usam `argparse` (§1.3).

Na CLI nativa standalone (que não depende de `rich`), utilize diretamente a função **`expand_year_range`** de `quantilica.core.dates`. Como ela pode lançar `ValueError` para intervalos ou anos inválidos, capture e trate a exceção exibindo uma mensagem no stderr:

```python
from quantilica.core.dates import expand_year_range

def _cmd_sync(args: argparse.Namespace) -> None:
    try:
        years = expand_year_range(*args.years) if args.years else expand_year_range("2018:2026")
    except ValueError as exc:
        print(f"Erro: formato de ano/intervalo inválido. {exc}", file=sys.stderr)
        sys.exit(1)

    for year in years:
        get_year(year=year, ...)
```

---

## 11. Anti-padrões a evitar

### 11.1 `typer.echo` no `plugin.py`

```python
# ❌ Não use — não integra com Rich
typer.echo(f"Salvo {len(points)} pontos em {outfile}")

# ✅ Use console.print
console.print(f"[green]✓[/green] Salvo [bold]{len(points)}[/bold] pontos em [dim]{outfile}[/dim]")
```

### 11.2 `print()` direto

```python
# ❌ Não usa Rich, quebra barras de progresso, sem cor
print(f"Erro: {exc}")

# ✅ Use console.print
console.print(f"[red]Erro:[/red] {exc}")
```

### 11.3 Logging INFO dentro de loops N itens

```python
# ❌ Gera N linhas de log, quebra a barra de progresso mesmo com RichHandler
for series_id in series_ids:
    logger.info("Fetching series %d", series_id)
    ...

# ✅ DEBUG — só aparece com --verbose; progresso via callback
for series_id in series_ids:
    logger.debug("Fetching series %d", series_id)
    ...
    if on_progress is not None:
        on_progress(processed, total, ok, failed, skipped)
```

### 11.4 Progress bar na lógica de negócio

```python
# ❌ lógica de negócio não deve saber sobre tqdm/Rich
from tqdm import tqdm

def fetch_bulk(ids):
    for id in tqdm(ids):  # ← acoplamento indevido
        ...

# ✅ Callbacks desacoplam display de lógica
def fetch_bulk(ids, on_progress=None):
    for i, id in enumerate(ids, 1):
        ...
        if on_progress:
            on_progress(i, len(ids), ok, failed, skipped)
```

!!! note "Padrão legado: `show_progress: bool`"
    Vários fetchers ainda passam `show_progress=not verbose` para funções internas que gerenciam sua própria barra tqdm. Isso é tolerável quando a função não expõe callback, mas é o padrão legado. Ao escrever nova lógica, prefira sempre a assinatura de callback (`on_progress`, `ProgressCallback`, `on_done`) — veja §5.2. Ao refatorar código legado, substitua o flag por callback antes de adicionar `plugin.py`.

### 11.5 `configure_cli_logging` no `plugin.py`

```python
# ❌ Nível INFO por padrão quebra barras de progresso Rich
from quantilica.core.logging import configure_cli_logging
configure_cli_logging(verbose=verbose)

# ✅ Use setup_rich_logging de quantilica.cli.ui
from quantilica.cli.ui import setup_rich_logging
setup_rich_logging(verbose, console=console)
```

### 11.6 Declarar `typer` ou `rich` nas dependências do fetcher

```toml
# ❌ Não declare — essas dependências são fornecidas pelo host quantilica-cli
[project]
dependencies = [
    "typer>=0.15.0",   # ← não fazer
    "rich>=13.0.0",    # ← não fazer
    "quantilica-core ...",
]

# ✅ Apenas dependências de negócio do fetcher
[project]
dependencies = [
    "beautifulsoup4>=4.12",
    "httpx2>=2.12.0",
    "quantilica-core ...",
]
```

### 11.7 `-v` como atalho de `--verbose`

```python
# ❌ Cria conflito com wrappers e scripts
typer.Option("-v", "--verbose", ...)

# ✅ Apenas --verbose, sem atalho
typer.Option("--verbose", ...)
```

---

## 12. Checklist para novos fetchers

Use esta lista ao implementar ou revisar a CLI de um fetcher:

### `cli.py` — wrapper fino (padrão `FetcherApp`)

- [ ] Import do plugin **protegido**: `try/except ImportError` → imprime `instale via "quantilica install <fonte>"` em `sys.stderr` e sai com código **1** — nunca `ModuleNotFoundError` (referência: `bcb-sgs-fetcher/src/bcb_sgs_fetcher/cli.py`).
- [ ] `main(argv: list[str] | None = None)` — aceita argv para testabilidade (obrigatório).
- [ ] `main()` delega ao app na forma canônica `app(argv)`, com `if argv is None: argv = sys.argv[1:]` (nenhuma gramática de subcomando duplicada aqui; referência: `bcb-sgs-fetcher/src/bcb_sgs_fetcher/cli.py`). A forma antiga (`sys.argv = [sys.argv[0]] + argv; app()`, ainda presente em `anac`, `anp`, `cvm`, `inep`, `inmet`, `pdet`, `rfb-cnpj` e `rtn`) é tolerada até a próxima revisão de cada fetcher — fetchers novos usam `app(argv)` (já adotada em `bcb-sgs`, `comex`, `datasus`, `tesouro-direto` e `tse`).
- [ ] `cli.py` não importa `quantilica.cli.sdk`/`quantilica.cli.ui` diretamente — apenas o `plugin.py` (§3.2).
- [ ] Entry point declarado em `[project.scripts]`.

### `cli.py` — argparse (apenas fetcher customizado, ex: `sidra-fetcher`)

- [ ] `argparse.ArgumentParser` com `prog` e `description` definidos.
- [ ] `--version` com `action="version"` lendo de `__version__`.
- [ ] `-o`/`--output` com padrão `/data/<fonte>`.
- [ ] `--verbose` sem atalho `-v`.
- [ ] Subcomandos com `add_subparsers(dest="command", required=True)` **ou** `parser.set_defaults(func=lambda _: parser.print_help())` (§2.1).
- [ ] Função de construção do parser nomeada **`get_parser()`** (não `set_parser`, não `get_args`).
- [ ] `main(argv: list[str] | None = None)` — aceita argv para testabilidade (obrigatório).
- [ ] `main()` chama `configure_cli_logging(verbose=args.verbose)` antes de qualquer I/O.
- [ ] Se exibir progresso: `logging.getLogger("quantilica.core").setLevel(logging.WARNING)` e `logging.getLogger("<pacote_fetcher>").setLevel(logging.WARNING)` quando `not verbose` (§2.6).
- [ ] Erros fatais escrevem em `stderr` e encerram com `sys.exit(1)`.
- [ ] Entry point declarado em `[project.scripts]`.

### `plugin.py` (Typer + Rich)

- [ ] Docstring `"""Typer plugin for quantilica-cli integration."""`.
- [ ] `app = typer.Typer(help="...")` no topo (ou `app = FetcherApp(...).app`).
- [ ] `console = get_console()` compartilhado por todos os comandos próprios (importado de `quantilica.cli.ui`) — **apenas se o plugin define comandos próprios**; plugins 100% `FetcherApp` (ex.: `comex`, `rtn`) herdam do SDK e não o definem (§3.2).
- [ ] `_DEFAULT_OUTPUT = Path("/data/<fonte>")` — **apenas se o plugin define comandos próprios**; plugins 100% `FetcherApp` herdam o default do SDK (§3.2).
- [ ] Cada comando chama `setup_rich_logging(verbose, console=console)` como primeira linha.
- [ ] Funções de comando nomeadas `cmd_<verbo>` (ex: `cmd_sync`, `cmd_list`).
- [ ] Nenhum `typer.echo()` — apenas `console.print()`.
- [ ] Nenhum `print()` direto.
- [ ] `-o`/`--output` presente em todo comando que salva arquivos.
- [ ] `--verbose` presente em todo comando que faz I/O de rede.
- [ ] Operações únicas de rede usam `console.status(...)`.
- [ ] Operações bulk usam `Progress` com `console=console` (ou `Live + Group` para dois níveis — §4.3).
- [ ] Callbacks (`on_progress`, `on_grupo`, `on_page`, `ProgressCallback`, `on_done`) separam display de lógica (§5.2).
- [ ] Mensagens de sucesso usam `[green]✓[/green]`.
- [ ] Erros usam `[red]Erro:[/red]` + `raise typer.Exit(code=1)`.
- [ ] Avisos usam `[yellow]Aviso:[/yellow]`.
- [ ] Entry point declarado em `[project.entry-points."quantilica.fetchers"]`.
- [ ] `typer` e `rich` **não** estão em `[project.dependencies]`.
- [ ] **Fronteira**: `quantilica.cli.sdk`/`quantilica.cli.ui` são importados **somente aqui** — nenhum outro módulo do fetcher os importa (§3.2).

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

- [Arquitetura de CLI e Estratégia de Dependências](../concepts/arquitetura.md#arquitetura-de-cli) — visão arquitetural de alto nível.
- [quantilica-cli](../fundacoes/quantilica-cli.md) — como o hub descobre e monta os plugins.
- [Padrões Práticos — UX de CLI](../concepts/padroes.md#cli-ux) — padrão progresso vs. logs.
- [Padronização de Versão](python.md) — como expor `__version__` em argparse e Typer.
