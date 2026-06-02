# Padronização de Versão em Pacotes Python

Para garantir consistência entre os projetos da Quantilica e evitar a duplicação manual da versão (no `pyproject.toml` e no código), adotamos o seguinte padrão.

## 1. Definição no `__init__.py`

A versão deve ser recuperada dinamicamente dos metadados do pacote instalado usando a biblioteca padrão `importlib.metadata`. Isso garante que a versão exibida seja sempre a mesma definida no `pyproject.toml`.

No arquivo `src/pacote/__init__.py`:

```python
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nome-do-pacote")
except PackageNotFoundError:
    # Pacote não instalado (ex: rodando direto do código fonte)
    __version__ = "0.0.0"

__all__ = ["__version__"]
```

> **Nota:** Substitua `"nome-do-pacote"` pelo nome exato definido na chave `name` do `pyproject.toml`.

## 2. Exposição via CLI

### Usando `argparse`

O `argparse` possui uma ação nativa para lidar com flags de versão.

```python
import argparse
from . import __version__

def get_args():
    parser = argparse.ArgumentParser(prog="meu-cli")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser.parse_args()
```

### Usando `Typer`

No `Typer`, a versão pode ser exposta via callback ou no construtor do `Typer`.

```python
import typer
from . import __version__

app = typer.Typer(help="<Descrição curta do fetcher.>")


def version_callback(value: bool):
    if value:
        print(f"meu-cli {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", callback=version_callback, is_eager=True
    ),
):
    pass
```

## 3. Por que este método?

1.  **Single Source of Truth:** A versão é definida apenas no `pyproject.toml`.
2.  **Standard Library:** `importlib.metadata` faz parte da biblioteca padrão desde o Python 3.8.
3.  **Robustez:** Funciona corretamente mesmo se o pacote for instalado via `pip install -e .` (modo editável) ou se o ambiente não estiver totalmente configurado (fallback para `0.0.0`).
