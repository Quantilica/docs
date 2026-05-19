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
| Colorido / progresso | Não | Sim |

O `quantilica-cli` descobre plugins dinamicamente via entry points — nunca declara fetchers como dependências diretas. Isso mantém o hub leve e desacoplado.

### 1.1 Por que dois níveis?

- **Instalação mínima**: um usuário que só quer usar `comex-fetcher` como biblioteca não precisa de Typer nem Rich. A `cli.py` garante isso.
- **UX superior no hub**: quando carregado via `quantilica-cli`, o ambiente já tem Typer e Rich disponíveis. O `plugin.py` usa isso sem declarar dependência.
- **Automação vs. interativo**: `cli.py` é adequada para cron jobs e scripts; `plugin.py` serve quem usa o terminal interativamente.

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

Não há uma lista fechada de subcomandos, pois cada fetcher tem semântica própria. Entretanto, alguns padrões são recorrentes:

| Subcomando | Quando usar |
|---|---|
| `download` / `fetch` | Baixar o conjunto principal de dados |
| `list` | Listar o que está disponível (datasets, anos, etc.) |
| `convert` | Converter de formato bruto para Parquet/JSON |
| `info` | Exibir metadados sem baixar |
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
    └── tesouro-direto ← tesouro_direto_fetcher.plugin:app
```

Cada nó da árvore é um `typer.Typer` exportado por `plugin.py` e descoberto via entry point.

### 3.2 Cabeçalho obrigatório

```python
"""Typer plugin for quantilica-cli integration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler

app = typer.Typer(help="<Descrição curta do fetcher.>")
console = Console()

_DEFAULT_OUTPUT = Path("/data/<fonte>")
```

Regras:

- O docstring do módulo deve ser exatamente `"""Typer plugin for quantilica-cli integration."""`.
- `app` deve ser o nome do objeto `typer.Typer` exportado (é o que o entry point aponta).
- `console = Console()` deve ser instanciado no topo do módulo — todos os comandos compartilham a mesma instância.
- `_DEFAULT_OUTPUT` define o caminho padrão de saída do fetcher. Deve ser `/data/<fonte>` para consistência com a convenção de montagem Docker do ecossistema.
- Não importe `typer` ou `rich` no `pyproject.toml` do fetcher — essas dependências são fornecidas pelo host `quantilica-cli`.

### 3.3 `_setup_logging` — o ponto central de logging

Cada `plugin.py` deve definir a seguinte função e chamá-la no início de cada comando:

```python
def _setup_logging(verbose: bool) -> None:
    """Configura logging via RichHandler para não quebrar barras de progresso.

    verbose=False → WARNING apenas (sem poluição de INFO no terminal).
    verbose=True  → DEBUG via Rich console (intercalado corretamente).
    """
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, show_path=False)],
        force=True,
    )
```

E em cada comando:

```python
@app.command("download")
def cmd_download(
    verbose: Annotated[bool, typer.Option("--verbose", help="Logs detalhados")] = False,
) -> None:
    """..."""
    _setup_logging(verbose)
    ...
```

#### Por que `_setup_logging` e não `configure_cli_logging`?

`quantilica_core.configure_cli_logging(verbose=False)` configura o nível para `INFO`. Isso faz com que todos os `logger.info()` internos do fetcher — incluindo logs de cada requisição HTTP — apareçam no terminal e **quebrem a renderização das barras de progresso Rich**, pois são escritos diretamente no stderr sem coordenação com o Rich.

`_setup_logging` resolve isso em duas frentes:

1. **Nível padrão = `WARNING`**: por padrão, somente avisos e erros são exibidos. O terminal fica limpo para o Rich renderizar.
2. **`RichHandler` com `console=console`**: quando `--verbose` é ativado, os logs passam pelo mesmo objeto `Console` que as barras de progresso. O Rich gerencia o intercalamento e nenhum log quebra o layout.

| Situação | Comportamento esperado |
|---|---|
| Sem `--verbose` (padrão) | Apenas `WARNING` e `ERROR`; barras de progresso limpas |
| Com `--verbose` | `DEBUG` completo, formatado via `RichHandler`, intercalado com progress |

### 3.4 Estrutura de um comando completo

```python
@app.command("download")
def cmd_download(
    output: Annotated[
        Path,
        typer.Option("-o", "--output", help="Diretório de saída"),
    ] = _DEFAULT_OUTPUT,
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Logs detalhados")
    ] = False,
) -> None:
    """Baixar dados do <fonte>."""
    _setup_logging(verbose)
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

Para fetchers com muitos comandos agrupados por função, use `typer.Typer` aninhado:

```python
app = typer.Typer(help="Resultado do Tesouro Nacional (RTN).")
fetch_sub = typer.Typer(help="Buscar metadados e baixar arquivos RTN.")
export_sub = typer.Typer(help="Exportar dados RTN para diferentes formatos.")
app.add_typer(fetch_sub, name="fetch")
app.add_typer(export_sub, name="export")

@fetch_sub.command("metadata")
def cmd_metadata(...) -> None:
    """Buscar metadados HTML e gerar metadata.json."""
    ...

@export_sub.command("excel")
def cmd_export_excel(...) -> None:
    """Exportar dados RTN para Excel."""
    ...
```

Isso produz:

```
quantilica fetch rtn fetch metadata
quantilica fetch rtn fetch download
quantilica fetch rtn export excel
quantilica fetch rtn export sqlite
```

Use subcommands aninhados quando há mais de dois grupos semânticos distintos. Para fetchers simples (3-6 comandos), um único nível é suficiente.

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

```python
from collections.abc import Callable

# Progresso por item (N itens com total conhecido)
on_progress: Callable[[int, int, int, int, int], None] | None = None
# args: (processed, total, ok, failed, skipped)

# Progresso por grupo (com total descoberto ao vivo)
on_grupo: Callable[[str, int, int], None] | None = None
# args: (nome_grupo, done, total)

# Progresso por página
on_page: Callable[[int, int], None] | None = None
# args: (page, n_pages)
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
    _setup_logging(verbose)
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

Fetchers que aceitam anos como argumento devem suportar o formato de intervalo `INICIO:FIM`:

```python
def _expand_years(years: list[str]) -> list[int]:
    result = []
    for arg in years:
        if ":" in arg:
            try:
                start, end = map(int, arg.split(":"))
                step = 1 if start <= end else -1
                result.extend(range(start, end + step, step))
            except ValueError:
                console.print(f"[yellow]Aviso:[/yellow] intervalo inválido '{arg}'")
        else:
            try:
                result.append(int(arg))
            except ValueError:
                console.print(f"[yellow]Aviso:[/yellow] ano inválido '{arg}'")
    return result
```

Uso no Typer:

```python
@app.command("trade")
def trade(
    years: Annotated[
        list[str],
        typer.Argument(help="Anos (ex: 2020), intervalos (2018:2020) ou 'complete'"),
    ],
) -> None:
    """Baixar dados de transações comerciais."""
    if years == ["complete"]:
        get_complete(...)
        return
    for year in _expand_years(years):
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

### 11.5 `configure_cli_logging` no `plugin.py`

```python
# ❌ Nível INFO por padrão quebra barras de progresso Rich
from quantilica_core.logging import configure_cli_logging
configure_cli_logging(verbose=verbose)

# ✅ Use _setup_logging definido localmente
_setup_logging(verbose)
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
- [ ] Subcomandos com `add_subparsers(dest="command", required=True)`.
- [ ] `main()` chama `configure_cli_logging(verbose=args.verbose)` antes de qualquer I/O.
- [ ] Erros fatais escrevem em `stderr` e encerram com `sys.exit(1)`.
- [ ] Entry point declarado em `[project.scripts]`.

### `plugin.py` (Typer + Rich)

- [ ] Docstring `"""Typer plugin for quantilica-cli integration."""`.
- [ ] `app = typer.Typer(help="...")` no topo.
- [ ] `console = Console()` compartilhado por todos os comandos.
- [ ] `_DEFAULT_OUTPUT = Path("/data/<fonte>")`.
- [ ] Função `_setup_logging(verbose)` com `RichHandler(console=console)`.
- [ ] Cada comando chama `_setup_logging(verbose)` como primeira linha.
- [ ] Nenhum `typer.echo()` — apenas `console.print()`.
- [ ] Nenhum `print()` direto.
- [ ] `-o`/`--output` presente em todo comando que salva arquivos.
- [ ] `--verbose` presente em todo comando que faz I/O de rede.
- [ ] Operações únicas de rede usam `console.status(...)`.
- [ ] Operações bulk usam `Progress` com `console=console`.
- [ ] Callbacks (`on_progress`, `on_grupo`, `on_page`) separam display de lógica.
- [ ] Mensagens de sucesso usam `[green]✓[/green]`.
- [ ] Erros usam `[red]Erro:[/red]` + `raise typer.Exit(code=1)`.
- [ ] Avisos usam `[yellow]Aviso:[/yellow]`.
- [ ] Entry point declarado em `[project.entry-points."quantilica.fetchers"]`.
- [ ] `typer` e `rich` **não** estão em `[project.dependencies]`.

---

## 13. Exemplos de referência no ecossistema

| Padrão | Fetcher de referência | Arquivo |
|---|---|---|
| Pipeline completo com Rule + Progress + resumo | `bcb-sgs-fetcher` | `plugin.py :: pipeline_cmd` |
| Callbacks `on_progress` / `on_grupo` / `on_page` | `bcb-sgs-fetcher` | `bulk.py` |
| `_setup_logging` com `RichHandler` | `bcb-sgs-fetcher` | `plugin.py :: _setup_logging` |
| Table com totais em rodapé | `datasus-fetcher` | `plugin.py :: cmd_list_datasets` |
| `console.status` em conexão FTP | `pdet-fetcher` | `plugin.py :: cmd_fetch` |
| Subcommands aninhados (`fetch_sub`, `export_sub`) | `rtn-fetcher` | `plugin.py` |
| Expansão de intervalos de anos `2018:2020` | `comex-fetcher` | `plugin.py :: _expand_years` |
| Panel com metadados de entidade | `sidra-fetcher` | `plugin.py :: info` |
| `--dry-run` com tabela de pré-visualização | `datasus-fetcher` | `plugin.py :: cmd_data` |
| `console.status` com `--force` | `rtn-fetcher` | `plugin.py :: cmd_metadata` |
| `_print_info` como helper de tabela reutilizável | `tesouro-direto-fetcher` | `plugin.py :: _print_info` |
| `console.rule` para divisores de seção | `tesouro-direto-fetcher` | `plugin.py :: cmd_info` |

---

## Saiba mais

- [Arquitetura de CLI e Estratégia de Dependências](../concepts/cli.md) — visão arquitetural de alto nível.
- [quantilica-cli](../fundacoes/quantilica-cli.md) — como o hub descobre e monta os plugins.
- [Padrões Práticos — UX de CLI](../concepts/padroes.md#cli-ux) — padrão progresso vs. logs.
- [Padronização de Versão](python.md) — como expor `__version__` em argparse e Typer.
