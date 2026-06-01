---
title: Padronização de CLI para Fetchers
description: Guia completo e normativo para escrever a interface de linha de comando de fetchers Quantilica — cobrindo cli.py (argparse), plugin.py (Typer + Rich), logging, barras de progresso, UX e registro de entry points.
---

# Padronização de CLI para Fetchers

> Esta é a referência do **contribuidor**: como implementar convenções de CLI e armazenamento num fetcher. Para entender como os arquivos são organizados como **usuário final**, veja [Convenções de Armazenamento](../concepts/storage.md).

Este documento é o guia normativo para a construção de interfaces de linha de comando nos pacotes fetcher do ecossistema Quantilica. Cobre os dois níveis de interface que cada fetcher deve implementar: a **CLI nativa leve** (`cli.py`, argparse) e o **plugin para o hub unificado** (`plugin.py`, Typer + Rich).

Seguir este guia garante comportamento consistente entre fetchers, integração correta com `quantilica-cli` e UX homogênea para o usuário final.

---

## 1. Visão geral da arquitetura de dois níveis

Todo fetcher Quantilica expõe **dois pontos de entrada CLI** com responsabilidades distintas:

```
<pacote>/
├── src/<pacote>/
│   ├── cli.py       ← CLI nativa (argparse, sem Typer/Rich)
│   └── plugin.py    ← Plugin para quantilica-cli (Typer + Rich)
```

| Dimensão | `cli.py` | `plugin.py` |
|---|---|---|
| Framework | `argparse` (stdlib) | `typer` + `rich` |
| Dependências extras | Nenhuma | `typer`, `rich` (fornecidos pelo host) |
| Ativado por | `<pacote>-fetcher [comando]` | `quantilica fetch <fonte> [comando]` |
| Propósito | Instalação leve, scripting, pipelines | Experiência interativa, UX rica |
| Registro | `[project.scripts]` | `[project.entry-points."quantilica.fetchers"]` |
| Colorido / progresso | Rich: Não; tqdm: opcional (via core) | Sim |

O `quantilica-cli` descobre plugins dinamicamente via entry points — nunca declara fetchers como dependências diretas. Isso mantém o hub leve e desacoplado.

### 1.1 Por que dois níveis?

- **Instalação mínima**: um usuário que só quer usar `comex-fetcher` como biblioteca não precisa de Typer nem Rich. A `cli.py` garante isso.
- **UX superior no hub**: quando carregado via `quantilica-cli`, o ambiente já tem Typer e Rich disponíveis. O `plugin.py` usa isso sem declarar dependência.
- **Automação vs. interativo**: `cli.py` é adequada para cron jobs e scripts; `plugin.py` serve quem usa o terminal interativamente.

### 1.2 Vocabulário canônico de subcomandos

Para que a CLis sejam previsíveis, todo fetcher usa o **mesmo verbo** para a
mesma intenção. Cada fetcher implementa apenas o subconjunto que faz sentido
para sua fonte, mas nunca inventa um nome alternativo para um verbo já
existente nesta tabela:

| Verbo | Significado | Default |
|---|---|---|
| `sync` | Baixar/atualizar os dados da fonte; idempotente (pula o que já está atualizado) | baixa **tudo**; aceita seleção opcional via argumento posicional ou `--dataset` |
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
- **Pré-visualização é uma flag, não um comando.** Use `--dry-run` no `sync`;
  não crie um comando `info`/`status` separado só para listar o que seria
  baixado. `info` é reservado para metadados de uma entidade.
- **Agrupe quando houver mais de um eixo semântico.** Veja §3.5 — fetchers como
  o `bcb-sgs` separam operações por série (`series sync`, `series metadata`) das
  operações de catálogo (`catalogo sync`, `catalogo metadata-bulk`).

---

## 2. CLI nativa — `cli.py`

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

    # --- subcomando: download ---
    dl = subparsers.add_parser("download", help="Baixar dados.")
    dl.add_argument(
        "-o",
        "--output",
        metavar="DIR",
        default="/data/<fonte>",
        help="Diretório de saída (padrão: /data/<fonte>).",
    )
    dl.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Exibir logs detalhados em vez de barra de progresso.",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = get_parser()
    args = parser.parse_args(argv)

    from quantilica_core.logging import configure_cli_logging
    configure_cli_logging(verbose=args.verbose)

    if args.command == "download":
        _cmd_download(args)


def _cmd_download(args: argparse.Namespace) -> None:
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

def _cmd_download(args):
    if not args.output.parent.exists():
        print(f"Erro: diretório pai não existe: {args.output.parent}", file=sys.stderr)
        sys.exit(1)
```

- Nunca use `raise SystemExit(1)` diretamente em funções de negócio — reserve para o nível de CLI.
- Não suprima exceções silenciosamente. Se não souber o que fazer com uma exceção, deixe propagar.

### 2.6 Silenciar logs INFO quando exibindo progresso

`configure_cli_logging(verbose=False)` define o nível raiz em `INFO`. Isso faz com que mensagens internas do core (como `log_step` em `quantilica_core.http`) apareçam no terminal e corrompam a saída de barras tqdm.

Quando `cli.py` exibe progresso (barra tqdm ou output limpo), adicione após `configure_cli_logging`:

```python
def main(argv: list[str] | None = None) -> None:
    parser = get_parser()
    args = parser.parse_args(argv)
    configure_cli_logging(verbose=args.verbose)
    if not args.verbose:
        # Suprime log_step (INFO) do core e logs de rastreamento do fetcher
        logging.getLogger("quantilica_core").setLevel(logging.WARNING)
        logging.getLogger("<pacote_fetcher>").setLevel(logging.WARNING)
    args.func(args)
```

Onde `<pacote_fetcher>` é o nome do pacote do fetcher (ex: `"comex_fetcher"`, `"pdet_fetcher"`). São necessários dois `setLevel` porque `quantilica_core.*` usa o namespace `"quantilica_core"` e cada fetcher usa o namespace do seu próprio pacote — `get_logger(__name__)` retorna `logging.getLogger(name)` sem prefixo adicional. Evite `logging.getLogger().setLevel(WARNING)` (raiz) pois suprime loggers de terceiros como `httpx`.

---

## 3. Plugin para `quantilica-cli` — `plugin.py`

### 3.1 Por que `plugin.py` existe

O `quantilica-cli` monta uma árvore de comandos a partir de todos os fetchers instalados:

```
quantilica
└── fetch
    ├── bcb-sgs    ← bcb_sgs_fetcher.plugin:app
    ├── comex      ← comex_fetcher.plugin:app
    ├── datasus    ← datasus_fetcher.plugin:app
    ├── inmet      ← inmet_fetcher.plugin:app
    ├── pdet       ← pdet_fetcher.plugin:app
    ├── rtn        ← rtn_fetcher.plugin:app
    ├── sidra      ← sidra_fetcher.plugin:app
    └── td         ← tesouro_direto_fetcher.plugin:app
```

Cada nó da árvore é um `typer.Typer` exportado por `plugin.py` e descoberto via entry point.

O `plugin.py` pode importar funções auxiliares de `cli.py` quando ambos compartilham lógica de negócio que não pertence a um módulo separado (ex: helpers de exportação Excel/SQLite no `rtn-fetcher`). Isso não é acoplamento indevido — `cli.py` funciona como módulo de lógica reutilizável enquanto `plugin.py` cuida da apresentação Rich.

### 3.2 Cabeçalho obrigatório

```python
"""Typer plugin for quantilica-cli integration."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from quantilica_core.cli import get_console, setup_rich_logging

app = typer.Typer(help="<Descrição curta do fetcher.>")
console = get_console()

_DEFAULT_OUTPUT = Path("/data/<fonte>")
```

Regras:

- O docstring do módulo deve ser exatamente `"""Typer plugin for quantilica-cli integration."""`.
- `app` deve ser o nome do objeto `typer.Typer` exportado (é o que o entry point aponta).
- `console = get_console()` deve ser instanciado no topo do módulo — todos os comandos compartilham a mesma instância. `get_console()` retorna um console global compartilhado pelo processo, garantindo intercalamento correto entre logs e barras de progresso.
- `_DEFAULT_OUTPUT` define o caminho padrão de saída do fetcher. Deve ser `/data/<fonte>` para consistência com a convenção de montagem Docker do ecossistema.
- Não importe `typer` ou `rich` no `pyproject.toml` do fetcher — essas dependências são fornecidas pelo host `quantilica-cli`.

### 3.3 `setup_rich_logging` — o ponto central de logging

Cada `plugin.py` deve chamar `setup_rich_logging` de `quantilica_core.cli` como primeira linha de cada comando:

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

`configure_cli_logging(verbose=False)` configura o nível para `INFO` com um handler padrão de stderr. Isso faz com que mensagens internas (como `log_step` em `quantilica_core.http`) apareçam no terminal e **corrompam barras de progresso Rich**, pois escrevem diretamente no stderr sem coordenação com o `Console`.

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

### 3.5 Subcommands aninhados

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
quantilica fetch bcb-sgs series sync 433
quantilica fetch bcb-sgs series metadata 433
quantilica fetch bcb-sgs catalogo sync
quantilica fetch bcb-sgs catalogo metadata-bulk
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

O `<nome-curto>` é o que o usuário digitará: `quantilica fetch <nome-curto>`. Use kebab-case quando necessário (`bcb-sgs`), mas prefira nomes de uma palavra quando possível.

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

#### Dois níveis simultâneos com `Live + Group`

Para fetchers que baixam N arquivos grandes em sequência, exiba uma barra de itens (overall) e uma barra de bytes do arquivo atual ao mesmo tempo usando `Live + Group`:

```python
from rich.console import Group
from rich.live import Live
from quantilica_core.cli import make_batch_progress, make_download_progress
from quantilica_core.http import ProgressCallback
from rich.progress import Progress, TaskID

def _file_callback(
    file_progress: Progress,
    task_id: TaskID,
    description: str,
) -> ProgressCallback:
    """Retorna ProgressCallback que alimenta uma task Rich de bytes."""
    def callback(downloaded: int, total_bytes: int) -> None:
        if downloaded == 0 and total_bytes == 0:   # sinal de retry
            file_progress.reset(task_id)
            file_progress.update(task_id, description=description, visible=True)
            return
        if total_bytes:
            file_progress.update(task_id, total=total_bytes)
        file_progress.update(task_id, completed=downloaded)
    return callback

# No comando:
overall = make_batch_progress(console)
file_prog = make_download_progress(console)
overall_task = overall.add_task("[cyan]Iniciando...[/cyan]", total=total)
file_task = file_prog.add_task("", total=None, visible=False)

ok = 0
with Live(Group(overall, file_prog), console=console, refresh_per_second=10):
    for year in years_list:
        overall.update(overall_task, description=f"[cyan]{year}[/cyan]")
        cb = _file_callback(file_prog, file_task, str(year))
        get_year(data_dir=output, year=year, progress=cb)
        file_prog.update(file_task, visible=False)
        ok += 1
        overall.update(overall_task, advance=1, description=f"[green]{ok}✓[/green]")
```

`make_batch_progress` e `make_download_progress` são fornecidas por `quantilica_core.cli` e já usam o console correto. `ProgressCallback = Callable[[int, int], None]` é definida em `quantilica_core.http`. Veja o `comex-fetcher plugin.py :: sync` como referência.

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
from quantilica_core.http import ProgressCallback  # Callable[[int, int], None]

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
@app.command("data")
def cmd_data(
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Listar sem baixar")
    ] = False,
) -> None:
    """Baixar dados brutos."""
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

Use a função **`expand_years_cli`** importada de `quantilica_core.cli`. Ela faz a expansão utilizando `expand_year_range` internamente e imprime avisos amigáveis no console compartilhado caso encontre algum formato inválido:

```python
from quantilica_core.cli import expand_years_cli

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

Na CLI nativa standalone (que não depende de `rich`), utilize diretamente a função **`expand_year_range`** de `quantilica_core.dates`. Como ela pode lançar `ValueError` para intervalos ou anos inválidos, capture e trate a exceção exibindo uma mensagem no stderr:

```python
from quantilica_core.dates import expand_year_range

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
from quantilica_core.logging import configure_cli_logging
configure_cli_logging(verbose=verbose)

# ✅ Use setup_rich_logging de quantilica_core.cli
from quantilica_core.cli import setup_rich_logging
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
    "httpx>=0.28.1",
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

### `cli.py` (argparse)

- [ ] `argparse.ArgumentParser` com `prog` e `description` definidos.
- [ ] `--version` com `action="version"` lendo de `__version__`.
- [ ] `-o`/`--output` com padrão `/data/<fonte>`.
- [ ] `--verbose` sem atalho `-v`.
- [ ] Subcomandos com `add_subparsers(dest="command", required=True)` **ou** `parser.set_defaults(func=lambda _: parser.print_help())` (§2.1).
- [ ] Função de construção do parser nomeada **`get_parser()`** (não `set_parser`, não `get_args`).
- [ ] `main(argv: list[str] | None = None)` — aceita argv para testabilidade (obrigatório).
- [ ] `main()` chama `configure_cli_logging(verbose=args.verbose)` antes de qualquer I/O.
- [ ] Se exibir progresso: `logging.getLogger("quantilica_core").setLevel(logging.WARNING)` e `logging.getLogger("<pacote_fetcher>").setLevel(logging.WARNING)` quando `not verbose` (§2.6).
- [ ] Erros fatais escrevem em `stderr` e encerram com `sys.exit(1)`.
- [ ] Entry point declarado em `[project.scripts]`.

### `plugin.py` (Typer + Rich)

- [ ] Docstring `"""Typer plugin for quantilica-cli integration."""`.
- [ ] `app = typer.Typer(help="...")` no topo.
- [ ] `console = get_console()` compartilhado por todos os comandos (importado de `quantilica_core.cli`).
- [ ] `_DEFAULT_OUTPUT = Path("/data/<fonte>")`.
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
| `getLogger("quantilica_core"/"<pacote>").setLevel(WARNING)` em cli.py | `inmet-fetcher` | `cli.py :: main` |
| `parser.set_defaults(func=print_help)` sem `required=True` | `bcb-sgs-fetcher` | `cli.py :: get_parser` |
| Table com totais em rodapé | `datasus-fetcher` | `plugin.py :: cmd_list` |
| `console.status` em conexão FTP | `datasus-fetcher` | `plugin.py :: cmd_list` |
| Subcommands aninhados (`series_sub`, `catalogo_sub`) | `bcb-sgs-fetcher` | `plugin.py` |
| Expansão de intervalos de anos `2018:2020` | `comex-fetcher` | `plugin.py :: _expand_years` |
| Panel com metadados de entidade | `sidra-fetcher` | `plugin.py :: cmd_info` |
| `--dry-run` com tabela de pré-visualização | `datasus-fetcher` | `plugin.py :: cmd_sync` |
| Pipeline `sync` → `export`/`convert` | `rtn-fetcher` | `plugin.py :: cmd_pipeline` |
| `_print_info` como helper de tabela reutilizável | `tesouro-direto-fetcher` | `plugin.py :: _print_info` |
| `console.rule` / `console.print(Rule(...))` para seção | `tesouro-direto-fetcher` | `plugin.py :: cmd_pipeline` |
| Importar helpers de `cli.py` no `plugin.py` | `rtn-fetcher` | `plugin.py` (importa de `cli.py`) |

---

## Saiba mais

- [Arquitetura de CLI e Estratégia de Dependências](../concepts/cli.md) — visão arquitetural de alto nível.
- [quantilica-cli](../fundacoes/quantilica-cli.md) — como o hub descobre e monta os plugins.
- [Padrões Práticos — UX de CLI](../concepts/padroes.md#cli-ux) — padrão progresso vs. logs.
- [Padronização de Versão](python.md) — como expor `__version__` em argparse e Typer.
