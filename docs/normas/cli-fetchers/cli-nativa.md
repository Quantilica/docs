---
title: CLI nativa — cli.py
description: "Norma da CLI nativa (argparse) dos fetchers customizados: esqueleto, opções, subcomandos, registro no pyproject e erros."
---

# CLI nativa — cli.py

> Parte da norma [Padronização de CLI para Fetchers](../cli-fetchers.md). Os números de seção (§) são os da norma completa.

> **Escopo restrito (ADR `2026-10-08`):** `argparse` completo aplica-se apenas a
> fetchers com **comandos customizados fora do `FetcherApp`** — hoje, somente o
> `sidra-fetcher`. Todo fetcher novo baseado no `FetcherApp` **não** escreve a
> CLI nesta seção: usa o wrapper fino ([§1.3](../cli-fetchers.md)).

## 2.1 Esqueleto obrigatório

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

## 2.2 Opções padronizadas

Todas as CLIs nativas devem implementar as seguintes opções de forma consistente:

| Opção | Forma curta | Padrão | Tipo | Descrição |
|---|---|---|---|---|
| `--output` | `-o` | `/data/<fonte>` | `Path` | Diretório de saída |
| `--verbose` | (nenhuma) | `False` | `bool` | Logs detalhados |
| `--version` | (nenhuma) | — | ação | Exibe versão e encerra |

!!! warning "Sem `-v` como atalho de `--verbose`"
    Nunca use `-v` como atalho de `--verbose`. Wrappers e orquestradores (Makefile, scripts shell, quantilica-cli) podem reservar `-v` para outros fins. Um único `--verbose` sem ambiguidade é o padrão do ecossistema.

## 2.3 Subcomandos recomendados

Os subcomandos seguem o **vocabulário canônico** definido em [§1.2](../cli-fetchers.md). A `cli.py`
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

## 2.4 Registro no `pyproject.toml`

```toml
[project.scripts]
<pacote>-fetcher = "<modulo>.cli:main"
```

Exemplo real (comex-fetcher):

```toml
[project.scripts]
comex-fetcher = "comex_fetcher.cli:main"
```

## 2.5 Tratamento de erros

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

## 2.6 Silenciar logs INFO quando exibindo progresso

> **Só se aplica a fetcher customizado** (hoje, apenas `sidra-fetcher`, ADR `2026-10-08`) — wrappers finos não exibem progresso próprio nem tocam em loggers ([§1.3](../cli-fetchers.md)).

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
