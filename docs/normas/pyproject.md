---
title: Padronização de pyproject.toml
description: Convenções canônicas para pyproject.toml nos pacotes Quantilica — dependency-groups, configuração do ruff e regras de precedência.
---

# Padronização de `pyproject.toml`

Este documento define as convenções adotadas nos campos do `pyproject.toml` que não são cobertos por outras normas — especificamente a declaração de dependências de desenvolvimento e a configuração do linter/formatter.

---

## 1. Dependências de desenvolvimento — `[dependency-groups]`

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
```

Exemplo: `quantilica-core` expõe `quantilica-core[cli]` para habilitar helpers de Rich/Typer nos hosts que precisam deles. Esse é o uso correto.

---

## 2. Configuração do ruff — localização e precedência

### Regra de precedência

O arquivo **`ruff.toml` na raiz do workspace é canônico**. Ele define as regras base para todos os pacotes.

Por pacote, o `[tool.ruff]` no `pyproject.toml` deve existir **somente para overrides locais** — quando um módulo específico precisa suprimir uma regra que não faz sentido no seu contexto.

```
Quantilica/
├── ruff.toml          ← canônico (target-version, select, line-length)
└── meu-fetcher/
    └── pyproject.toml ← [tool.ruff] só se houver override local
```

### O que vai no `ruff.toml` raiz

```toml
# ruff.toml (raiz do workspace)
target-version = "py312"
exclude = [".venv", ".uv-cache"]

[lint]
select = ["E", "F", "I", "UP", "B"]
```

Esse arquivo não declara `line-length` — ele herda o padrão do ruff (88), que é o valor adotado pelo ecossistema.

### O que pode ir no `[tool.ruff]` por pacote

Apenas overrides que **não fazem sentido subir** para o nível workspace:

```toml
# pyproject.toml do pacote (apenas overrides)
[tool.ruff.lint.per-file-ignores]
"src/meu_pacote/cli.py" = ["B008"]   # default mutável em argparse é intencional
"tests/test_algo.py" = ["E402"]      # imports fora do topo por necessidade de mock
```

### O que nunca repetir por pacote

Não repita no `pyproject.toml` do pacote o que já está no `ruff.toml` raiz:

```toml
# NÃO faça isso — duplicação sem ganho
[tool.ruff]
line-length = 88          # já é o default
target-version = "py312"  # já está no ruff.toml raiz

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]  # já está no ruff.toml raiz
```

### Quando rodar ruff fora do workspace

Se alguém rodar `ruff check` de dentro do diretório do pacote, sem o `ruff.toml` da raiz visível, as regras base não serão aplicadas. Isso é aceitável: o cenário normal de desenvolvimento é a partir da raiz do workspace. Repos que precisam funcionar completamente standalone (ex: após extração do workspace) devem replicar a configuração no próprio `pyproject.toml`.
