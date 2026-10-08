---
title: Padronização de pyproject.toml
description: Convenções canônicas para pyproject.toml nos pacotes Quantilica — licença, tipagem, build backend, dependency-groups, ruff e pytest.
---

# Padronização de `pyproject.toml`

Este documento define as convenções adotadas no `pyproject.toml` dos pacotes Quantilica. Cada pacote é um **repositório git independente**, publicado standalone no PyPI (ver [Publicação e Release](publicacao.md)) — portanto o `pyproject.toml` de cada um é **auto-contido**.

---

## 1. Metadados de distribuição (pacotes publicáveis)

Todo pacote publicável declara:

```toml
[project]
name = "meu-pacote"
version = "0.1.0"                  # SemVer canônico (MAJOR.MINOR.PATCH)
license = "MIT"                    # PEP 639 (expressão SPDX)
license-files = ["LICENSE"]
classifiers = [
    # ... sem "License :: OSI Approved :: ..." (redundante sob PEP 639)
    "Typing :: Typed",             # se o pacote envia py.typed (PEP 561)
]

[build-system]
requires = ["hatchling>=1.27"]     # >=1.27 para suporte a PEP 639
build-backend = "hatchling.build"
```

- **Versão (`version`):** adere estritamente a [SemVer 2.0.0](https://semver.org/lang/pt-BR/). O bump de versão segue a [Política Canônica de Versionamento](publicacao.md#4-versionamento-semver-e-política-de-bump).
- **Licença — PEP 639:** use a expressão SPDX (`license = "MIT"`) + `license-files`, **não** a forma antiga `license = { file = "LICENSE" }` nem o classifier `License :: OSI Approved :: MIT License`. Requer `hatchling>=1.27`.
- **Exceção — backend `maturin` (extensão nativa):** fetchers com extensão nativa compilada usam `maturin` como backend em vez de `hatchling`, mantendo os demais campos PEP 639 iguais (`license = "MIT"` + `license-files`, classifier `Typing :: Typed` quando aplicável). Hoje, o único caso é o `datasus-fetcher` (módulo Rust `_datasus_dbc`): `requires = ["maturin>=1.5,<2.0"]`, `build-backend = "maturin"`, com `[tool.maturin] python-source = "src"` e `module-name` apontando para o módulo nativo (ver `datasus-fetcher/pyproject.toml`).
- **Tipagem — PEP 561:** um pacote tipado envia um arquivo marcador `py.typed` (vazio) em `src/<pacote>/py.typed` e declara o classifier `Typing :: Typed`. Sem o marcador, consumidores com mypy/pyright não enxergam os tipos. Os dois andam juntos: ou tem ambos, ou nenhum.
- **`uv.lock` em bibliotecas:** bibliotecas e fetchers **nunca versionam `uv.lock`** no repositório. O lockfile é restrito a aplicações web privadas (como `quantilica-portal`).

---

## 2. Dependências de desenvolvimento — `[dependency-groups]`

Use **sempre** `[dependency-groups]` (PEP 735) para declarar dependências de desenvolvimento. Não use `[project.optional-dependencies]` para esse fim.

```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "ruff>=0.9.0",
]
```

### Por que não `[project.optional-dependencies]`?

`[project.optional-dependencies]` é projetado para **extras de runtime** instaláveis pelo usuário final (ex: `pip install pacote[postgres]`). Usar esse mecanismo para dependências de desenvolvimento é um abuso semântico — esses extras aparecem nos metadados publicados do pacote e não fazem sentido fora do contexto de desenvolvimento.

`[dependency-groups]` foi introduzido exatamente para separar esse caso: dependências que só existem durante o desenvolvimento e não integram os metadados de distribuição.

### Instalando o grupo de desenvolvimento

```bash
# workspace (padrão — instala tudo incluindo dev)
uv sync --all-packages

# pacote isolado
uv sync --dev
```

### Quando `[project.optional-dependencies]` é correto

Use `[project.optional-dependencies]` somente para extras que o **usuário** pode instalar opcionalmente em produção:

```toml
[project.optional-dependencies]
cli = ["typer>=0.12", "rich>=13"]
analysis = ["quantilica-analytics>=0.2.0"]
```

Exemplos corretos:
- **Fetchers** usam a tag `analysis` para dependências analíticas pesadas (como `quantilica-analytics`, `polars` ou `pandas`), já que fetchers são focados primariamente em extração leve. Subcomandos analíticos (como `convert` ou `pipeline`) devem tratar a ausência dessas dependências graciosamente.
- **Declare `polars` explicitamente no extra `analysis`** sempre que um módulo do pacote importar `polars` diretamente (`import polars` / `from polars import ...` em `reader`, `contracts`, `wrangling` ou equivalentes). Não dependa da transitividade via `quantilica-analytics`: o pin transitivo pode mudar e o pacote quebra fora do workspace. Referência conforme: `cvm-fetcher` declara `"polars>=1.0.0"` ao lado de `"quantilica-analytics>=0.3.0"` no extra `analysis`.

O teste canônico da importabilidade sem o extra e a mensagem de erro exigida para módulos analíticos estão em [Padronização de CLI](cli-fetchers.md#35-comandos-analíticos-e-dependências-opcionais).

---

## 3. Configuração do ruff

Como cada pacote é um **repositório independente publicado standalone**, a configuração do ruff vive no próprio `pyproject.toml` — para que `ruff check`/`ruff format --check` (rodados pelo CI `test.yml` dentro do repo) apliquem as regras sem depender de um arquivo externo do workspace.

```toml
[tool.ruff]
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

# Overrides locais, quando necessário:
[tool.ruff.lint.per-file-ignores]
"src/meu_pacote/cli.py" = ["B008"]   # typer.Option/Argument como default é idiomático
"tests/test_algo.py" = ["E402"]      # imports fora do topo por necessidade de mock
```

- `line-length = 88`, `select = ["E", "F", "I", "UP", "B"]` — valores canônicos do ecossistema.
- O `ruff.toml` na raiz do workspace serve à conveniência de rodar o linter a partir da raiz durante o desenvolvimento; ele **não** substitui o `[tool.ruff]` de cada pacote, que é o que acompanha o pacote publicado.

## 4. Configuração do pytest

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["-p", "no:cacheprovider"]
```
