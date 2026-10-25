---
title: Padrões visuais Rich
description: Paleta, console.status, Progress, Table, Panel, Rule e mensagens de resultado padronizadas para a saída dos fetchers.
---

# Padrões visuais Rich

> Parte da norma [Padronização de CLI para Fetchers](../cli-fetchers.md). Os números de seção (§) são os da norma completa.

## 4.1 Paleta de cores e estilos

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

## 4.2 `console.status` — operação única de rede

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

## 4.3 `Progress` — barras de progresso para operações bulk

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

### Progresso com total conhecido

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

### Progresso indeterminado (total desconhecido inicialmente)

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

### Downloads Paralelos e Progresso Concorrente

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

## 4.4 `Table` — exibição de dados tabulares

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

## 4.5 `Panel` — metadados de uma entidade

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

## 4.6 `Rule` — divisores de seção em pipelines

Use para separar visualmente passos de pipelines longos:

```python
from rich.rule import Rule

console.print(Rule("[bold]Passo 1/4: Árvore de grupos[/bold]"))
# ... execução do passo ...
console.print(Rule("[bold]Passo 2/4: Séries desativadas[/bold]"))
```

Substitui os antigos `typer.echo("=== Passo N/4 ===")`.

`console.rule("[bold]texto[/bold]")` é equivalente a `console.print(Rule("[bold]texto[/bold]"))` e pode ser preferido pela brevidade.

## 4.7 Mensagens de resultado padronizadas

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
