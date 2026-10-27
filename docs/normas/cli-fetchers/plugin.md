---
title: Plugin para o quantilica-cli — plugin.py
description: "Norma do plugin.py dos fetchers: cabeçalho, setup_rich_logging, estrutura de comandos, dependências opcionais e entry points."
---

# Plugin para o quantilica-cli — plugin.py

> Parte da norma [Padronização de CLI para Fetchers](../cli-fetchers.md). Os números de seção (§) são os da norma completa.

## 3.1 Por que `plugin.py` existe

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

## 3.2 Cabeçalho obrigatório

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

## 3.3 `setup_rich_logging` — o ponto central de logging

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

### Por que não `configure_cli_logging`?

`configure_cli_logging(verbose=False)` configura o nível para `INFO` com um handler padrão de stderr. Isso faz com que mensagens internas (como `log_step` em `quantilica.core.http`) apareçam no terminal e **corrompam barras de progresso Rich**, pois escrevem diretamente no stderr sem coordenação com o `Console`.

`setup_rich_logging` resolve em duas frentes:

1. **Nível padrão = `WARNING`** — sem ruído de INFO no terminal.
2. **`RichHandler(console=console)`** — quando `--verbose`, logs passam pelo mesmo objeto `Console` que as barras de progresso.

## 3.4 Estrutura de um comando completo

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

## 3.5 Comandos Analíticos e Dependências Opcionais

Fetchers são, por definição, ferramentas de extração leve. Subcomandos que exigem processamento de dados denso (como `convert` ou `pipeline`, que utilizam bibliotecas como `polars`, `duckdb` ou `quantilica-analytics`) **não devem** impor essas dependências aos usuários que apenas desejam fazer o download (`sync`).

### A fronteira autorizada do Lake Hive: `lake.py`

A conversão para o formato analítico Parquet particionado em Hive segue a especificação canônica definida em [Padronização de Lake Hive (Parquet)](../lake.md). Para assegurar a pureza arquitetural do coletor:

- O módulo **`lake.py`** (ou subpacote `lake/`) é a **fronteira exclusiva e autorizada** para escrita no lake Hive.
- Todos os imports de motores pesados (`duckdb`, `polars`, `quantilica.analytics.lake`) residem dentro de `lake.py`.
- O pacote base do fetcher nunca declara essas bibliotecas em `[project.dependencies]`: elas pertencem estritamente ao extra opcional `[project.optional-dependencies]` sob a chave `analysis`.

### Registro padrão com `FetcherApp.command_convert` e `FetcherApp.command_pipeline`

Em vez de registrar comandos analíticos manualmente com decorators Typer genéricos, coletores baseados em `FetcherApp` devem utilizar os métodos do SDK `fetcher.command_convert()` e `fetcher.command_pipeline()`:

```python
# plugin.py
from pathlib import Path
from typing import Any
from quantilica.cli.sdk import FetcherApp

fetcher = FetcherApp(name="pdet-fetcher", help="Microdados do PDET.")
app = fetcher.app

def convert(
    input_dir: Path,
    lake_dir: Path,
    dataset: list[str] | None = None,
    force: bool = False,
) -> Any:
    """Converter dados brutos sob input_dir para o lake em lake_dir."""
    from pdet_fetcher import lake
    return lake.converter.convert(input_dir, lake_dir, datasets=dataset, force=force)

# Registra o comando canônico `convert` (-i, --lake, --dataset, --force, --verbose):
fetcher.command_convert(convert)

# Registra o comando encadeado `pipeline` (sync -> convert):
fetcher.command_pipeline(convert)
```

Benefícios do padrão:

1. **Paridade de flags**: expõe automaticamente as opções canônicas `-i/--input`, `--lake` (aliases `-o`/`--output`, resolvendo para `lake_root()`), `--dataset` (repetível), `--force` e `--verbose`.
2. **Tratamento gracioso de dependências**: caso o usuário execute `convert` ou `pipeline` sem o extra instalado, o `FetcherApp` captura o `ImportError` e imprime automaticamente a instrução de instalação adequada (`quantilica install <fonte> --extra analysis`), encerrando com código 1 sem despejar tracebacks no terminal.
3. **Resumo padronizado**: formata o relatório de conversão com itens convertidos, pulados (*skipped*) e eventuais falhas.

### Padrão para fetchers customizados com comandos manuais

Fetchers customizados que não utilizam `FetcherApp` para `convert` devem adotar o mesmo isolamento:

1. Registre as dependências pesadas em `[project.optional-dependencies]` sob o grupo `analysis` no `pyproject.toml` do fetcher.
2. Atrase as importações do módulo de conversão (`from .lake import convert`) para o momento da execução do comando, isolando em um bloco `try...except ImportError`.
3. Avise graciosamente o usuário caso o módulo não esteja disponível com a mensagem `quantilica install <chave> --extra analysis`, saindo com código 1.

```python
@app.command("convert")
def cmd_convert(
    input: Annotated[Path, typer.Option("-i", "--input")] = Path("/data/fonte"),
) -> None:
    """Converter dados brutos para Parquet (requer extra 'analysis')."""
    try:
        from .lake import converte_dados
    except ImportError:
        console.print(
            "[red]Erro:[/red] convert requer extras de análise: "
            "quantilica install <chave> --extra analysis"
        )
        raise typer.Exit(1) from None

    converte_dados(input)
```

4. Módulos analíticos (`lake`, `reader`, `contracts` ou equivalentes) que importam `polars`, `duckdb` ou `quantilica-analytics` diretamente **devem** converter a ausência do extra num `ImportError` com instrução acionável:

```python
try:
    import duckdb
    from quantilica.analytics.lake import LakeWriter
except ImportError as exc:
    raise ImportError(
        "requer o extra 'analysis': uv add '<pacote-fetcher>[analysis]' --index https://index.quantilica.com/simple/"
    ) from exc
```

Teste canônico no ambiente **sem** o extra `analysis` instalado:

- `python -c "import <pacote>"` funciona normalmente;
- `python -c "from <pacote>.lake import <simbolo>"` falha com o `ImportError` acionável acima — nunca `ModuleNotFoundError` cru.

## 3.6 Subcommands aninhados

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

## 3.7 Registro no `pyproject.toml`

Os coletores registram dois grupos de entry points: um para a montagem de comandos na CLI e outro para os conversores do Lake Hive.

### 3.7.1 Entry point da CLI: `quantilica.fetchers`

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

# pdet-fetcher/pyproject.toml
[project.entry-points."quantilica.fetchers"]
pdet = "pdet_fetcher.plugin:app"
```

O `<nome-curto>` é o subcomando na raiz da CLI: `quantilica <nome-curto>`. Use kebab-case quando necessário (`bcb-sgs`), mas prefira nomes de uma palavra quando possível.

### 3.7.2 Entry point de conversão para Lake: `quantilica.lake`

Fetchers que disponibilizam conversão de seus microdados para o formato Parquet Hive registram adicionalmente o conversor no grupo `quantilica.lake`:

```toml
[project.entry-points."quantilica.lake"]
<nome-curto> = "<modulo>.lake:converter"
```

Exemplos reais:

```toml
# pdet-fetcher/pyproject.toml
[project.entry-points."quantilica.lake"]
pdet = "pdet_fetcher.lake:converter"

# anac-fetcher/pyproject.toml
[project.entry-points."quantilica.lake"]
anac = "anac_fetcher.lake:converter"

# datasus-fetcher/pyproject.toml
[project.entry-points."quantilica.lake"]
datasus = "datasus_fetcher.lake:converter"
```

O `quantilica-cli` e o `quantilica-analytics` descobrem os conversores dinamicamente via `quantilica.core.lake.load_lake_converter("<nome-curto>")`, permitindo que pipelines e automações executem conversões padronizadas em qualquer fonte sem acoplamento direto de código.

> **Nota sobre instalação sob demanda:** O `quantilica-cli` descobre os entry points registrados em `quantilica.fetchers` e `quantilica.lake` automaticamente assim que o pacote é instalado via `quantilica install <fonte>`. Aqui, `<fonte>` é a chave do `SOURCES_REGISTRY` local (`quantilica-cli/src/quantilica/cli/sources.py`) mesclada com o `sources.json` remoto do índice (o local tem precedência), que mapeia chave → distribuição — não necessariamente o nome do pacote (ex.: `td` → `tesouro-direto-fetcher`). Chaves remotas atuais: `anac`, `anp`, `bcb-sgs`, `bcb-sgs-sql`, `comex`, `cvm`, `datasus`, `inep`, `inmet`, `pdet`, `rfb-cnpj`, `rtn`, `sidra`, `sidra-sql`, `tesouro-direto`, `tse`, `quantilica-analytics`, `quantilica-catalog`; o registro local tem também `td`. O comando resolve via `registry.get(source, source)` — chave desconhecida é passada adiante como nome de distribuição.
