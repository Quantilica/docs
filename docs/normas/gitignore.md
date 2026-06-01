---
title: Padronização de .gitignore e política de uv.lock
description: Guia normativo para escrever .gitignore nos pacotes Quantilica e decidir quando versionar uv.lock — template canônico para bibliotecas e fetchers.
---

# Padronização de `.gitignore` e política de `uv.lock`

Este documento define o padrão de `.gitignore` adotado pelos pacotes-biblioteca da Quantilica (libs de infraestrutura e fetchers) e a política para o arquivo `uv.lock`.

---

## 1. Princípios

- **Curto e legível.** Listar apenas o que de fato aparece no repo. Templates inflados (estilo `github/gitignore/Python.gitignore` com 160+ linhas) misturam ferramentas que ninguém usa e dificultam revisão.
- **Por seção, com comentário.** Cada bloco de padrões começa com um comentário curto (`# Build / packaging`, `# Caches…`). Comentário explicando *por que* algo está ignorado, nunca *o que*.
- **Overrides específicos no fim.** Entradas exclusivas do repo (`data/`, `*.ini`, `output/`, etc.) vão **abaixo** do bloco template, sob um cabeçalho explícito `# Específico do repo`.
- **Sem patterns redundantes.** Não listar `venv/`, `ENV/`, `env/` se o projeto só usa `.venv/` (convenção `uv`). Não listar `Pipfile.lock` / `poetry.lock` / `pdm.lock` em repos que usam exclusivamente `uv`.

---

## 2. Política de `uv.lock` nos pacotes-biblioteca

`uv.lock` **não é versionado** em pacotes-biblioteca (libs e fetchers). O pacote é distribuído via `pip install git+https://...` ou PyPI; quem instala não usa o lockfile. Contribuidores trabalham no workspace, onde a `.venv` raiz já fornece um ambiente reproduzível. Versionar o lockfile cria ruído de merge sem ganho.

Em todos os casos, **nunca** versionar `.venv/`, `.uv-cache/` ou outros artefatos de runtime.

---

## 3. Template canônico — pacote Python (library / fetcher)

Use este template em pacotes-biblioteca: `quantilica-core`, `quantilica-io`, `quantilica-cli`, `quantilica-cloud`, `quantilica-catalog`, e em todos os fetchers (`sidra-fetcher`, `comex-fetcher`, `datasus-fetcher`, etc.).

```gitignore
# Build / packaging
__pycache__/
*.py[cod]
*.egg-info/
build/
dist/

# Virtual envs e caches do uv
.venv/
.uv-cache/

# Lockfile — libs não versionam uv.lock
uv.lock

# Caches de teste / lint / tipos
.pytest_cache/
.ruff_cache/
.mypy_cache/

# Cobertura
.coverage
.coverage.*
htmlcov/

# Editor / IDE / OS
.vscode/
.idea/
.DS_Store
Thumbs.db
*.swp

# Logs e env locais
*.log
.env
.env.local

# Claude
.claude/
```

---

## 4. Como adaptar entradas específicas do repo

Quando um repo precisar ignorar caminhos próprios (`data/`, `output/`, `*.ini`, etc.), inclua-os **abaixo** do bloco template sob um cabeçalho explícito:

```gitignore
# ...template acima...

# Específico do repo
data/
output/
*.csv
*.xlsx
```

Isto facilita auditoria — quem lê o arquivo sabe imediatamente o que é convenção compartilhada e o que é exceção local.

---

## 5. Aplicando a um repo existente

Para adotar o template em um repo que antes versionava `uv.lock`:

```bash
git rm --cached uv.lock
# atualizar .gitignore conforme o template
git add .gitignore
git commit -m "chore: padronizar .gitignore (template lib); deixar uv.lock untracked"
```

O arquivo `uv.lock` permanece em disco — apenas deixa de ser rastreado pelo git.

---

## 6. `.gitignore` por pacote vs. workspace

Pacotes membros do workspace **não precisam de `.gitignore` próprio** se seu diretório está coberto pelo `.gitignore` da raiz do workspace. A ausência de `.gitignore` em um subdiretório é uma decisão intencional, não uma omissão.

O `.gitignore` raiz do workspace já lista os padrões do template canônico (`__pycache__/`, `.venv/`, `.ruff_cache/`, etc.) e aplica a todos os subdiretórios via herança normal do git.

### Quando criar `.gitignore` próprio no pacote

Crie `.gitignore` no diretório do pacote apenas em um destes casos:

1. **O pacote tem entradas específicas** não cobertas pelo `.gitignore` raiz (ex: `data/`, `output/`, `*.sqlite`). Nesse caso, o `.gitignore` local contém **apenas** o bloco `# Específico do repo` — não replica o template inteiro.

2. **O pacote é (ou será) desenvolvido fora do workspace** como repo standalone. Nesse caso, inclui o template completo.

### Exemplo: `.gitignore` com apenas entradas locais

```gitignore
# Específico do repo
data/
output/
*.sqlite
```

O template base não é replicado — o workspace root já o cobre.
