---
title: Publicação e Release
description: Processo canônico de release dos pacotes Quantilica — Fluxo A (PyPI/OIDC) para pacotes âncora e Fluxo B (GitHub Releases + índice estático) para fetchers. Inclui workflows de CI, CHANGELOG e versionamento por tags.
---

# Publicação e Release

Os pacotes públicos do ecossistema Quantilica seguem **dois fluxos de release distintos**, dependendo do canal de distribuição:

| Fluxo | Canal | Pacotes | Workflow |
|---|---|---|---|
| **A — PyPI (OIDC)** | PyPI oficial | `quantilica-core`, `quantilica-cli`, `sidra-fetcher` | `publish.yml` com Trusted Publishing |
| **B — GitHub Releases** | Índice estático próprio | `quantilica-analytics`, `quantilica-catalog`, todos os `*-fetcher` (exceto `sidra-fetcher`) | `publish.yml` com GitHub Release + dispatch |

> Fetchers distribuídos via índice próprio não passam pelo PyPI. Instalam-se via `quantilica install <fonte>`, que consulta o índice hospedado em `quantilica-index` no GitHub Pages.

---

## 1. Pré-requisitos (uma vez por pacote)

### Fluxo A — PyPI (OIDC)

Feito manualmente no site do PyPI/TestPyPI e no GitHub — **não** versionado no repo:

1. Conta em [pypi.org](https://pypi.org) e em [test.pypi.org](https://test.pypi.org) (independentes).
2. **Trusted Publisher pendente** cadastrado em **ambos** os índices (Publishing → Add a pending publisher), antes mesmo do primeiro upload:
   - Owner: `Quantilica`
   - Repository: nome do repo
   - Workflow filename: `publish.yml`
   - Environment name: `pypi` (e um segundo publisher com `testpypi`)
3. Dois **GitHub Environments** no repo (Settings → Environments): `pypi` e `testpypi`. Recomendado exigir *required reviewer* no `pypi` — freio manual contra tag acidental.

Não crie API tokens: o Trusted Publishing os dispensa.

### Fluxo B — GitHub Releases

1. **Secret `INDEX_DISPATCH_TOKEN`** configurado no repo (Settings → Secrets and variables → Actions): token com permissão `contents: write` no repo `Quantilica/quantilica-index`.
2. Nenhum Environment adicional é necessário — o workflow usa apenas `GITHUB_TOKEN` para criar o Release.

---

## 2. Workflows de CI

Todo repo publicável tem dois workflows em `.github/workflows/`.

### `test.yml` — lint + testes (todos os pacotes)

Dispara em push/PR para `main`; roda `ruff check`, `ruff format --check` e `pytest` numa matriz 3.12/3.13 via `uv`.

```yaml
name: Test

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    name: Test (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}

      - name: Install dependencies
        run: uv sync --group dev

      - name: Lint with ruff
        run: |
          uv run ruff check src/ tests/
          uv run ruff format --check src/ tests/

      - name: Run tests
        run: uv run pytest
```

### `publish.yml` — Fluxo A: build → TestPyPI → PyPI (OIDC)

Para `quantilica-core`, `quantilica-cli` e `sidra-fetcher`. Dispara em push de tag `v*`. Um job de `build` isolado, depois dois jobs de publish em cadeia (TestPyPI → PyPI), cada um num Environment com `id-token: write`.

```yaml
name: Publish to PyPI

on:
  push:
    tags:
      - "v*"

jobs:
  build:
    name: Build distribution
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Build sdist and wheel
        run: uv build

      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish-testpypi:
    name: Publish to TestPyPI
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: testpypi
      url: https://test.pypi.org/p/<pacote>
    permissions:
      id-token: write
    steps:
      - name: Download build artifacts
        uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Publish to TestPyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/
          skip-existing: true

  publish-pypi:
    name: Publish to PyPI
    needs: publish-testpypi
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/<pacote>
    permissions:
      id-token: write
    steps:
      - name: Download build artifacts
        uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

- `skip-existing: true` **só** no TestPyPI (permite re-run com a mesma versão); no PyPI real deixe falhar se a versão já existir.
- `uv build` gera sdist + wheel. **Atenção:** valide que o sdist→wheel contém o código (um `[tool.hatch.build]` mal configurado pode gerar wheel vazio — cheque com `unzip -l dist/*.whl`).

### `publish.yml` — Fluxo B: build → GitHub Release → dispatch (índice estático)

Para todos os `*-fetcher` (exceto `sidra-fetcher`), `quantilica-analytics` e `quantilica-catalog`. Dispara em push de tag `v*`. Cria um GitHub Release com os artefatos e dispara o rebuild do índice estático.

```yaml
name: Release to GitHub & Notify Index

on:
  push:
    tags:
      - "v*"

jobs:
  release:
    name: Create Release & Dispatch
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Build sdist and wheel
        run: uv build

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: dist/*
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Dispatch Event to quantilica-index
        uses: peter-evans/repository-dispatch@v3
        with:
          token: ${{ secrets.INDEX_DISPATCH_TOKEN }}
          repository: Quantilica/quantilica-index
          event-type: fetcher_released
          client-payload: '{"repository": "${{ github.repository }}", "tag": "${{ github.ref_name }}"}'
```

---

## 3. `CHANGELOG.md`

Todo pacote publicável mantém um `CHANGELOG.md` no formato [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) + [SemVer](https://semver.org/lang/pt-BR/), com uma entrada por versão (`## [x.y.z] - AAAA-MM-DD`) e as seções `### Adicionado / Alterado / Corrigido / ...`. O `CHANGELOG.md` de cada repo é a fonte por-pacote; o [changelog do site](../changelog.md) é o resumo cross-pacote. A entrada da nova versão deve existir **antes** de criar a tag de release.

O formato completo — cabeçalho padrão, categorias permitidas e bootstrap de repos com histórico — está na norma dedicada de [Padronização de CHANGELOG.md](changelog.md).

---

## 4. Versionamento e tags

- **SemVer**: PATCH = fix; MINOR = feature compatível; MAJOR = quebra de API.
- A versão vive em `[project] version` do `pyproject.toml`.
- A **tag `vX.Y.Z`** é o release: criá-la e dar push dispara o `publish.yml`.
- Uma versão publicada é **imutável**. Errou? Publique uma nova; se necessário, faça *yank* da anterior pela interface web (não há API/twine para yank — Fluxo A apenas).

---

## 5. Cadeia de dependências

Dependa **por versão de registro** (`pacote>=X.Y`), nunca por `git+https`/`allow-direct-references` (o PyPI rejeita dependências VCS; o índice próprio também recomenda pins de versão). Publique **de cima para baixo**: o upstream primeiro, depois troque a dependência do downstream de git para registro. Ex.: `quantilica-core` → `sidra-fetcher` (`quantilica-core>=0.3.1`) → `sidra-sql` (`sidra-fetcher>=0.7.2`).

> Fetchers **não** declaram `typer`/`rich` (nem via extra) — esses vêm do host `quantilica-cli`. Ver [Padronização de CLI](cli-fetchers.md).

---

## 6. Checklists de release

### Fluxo A — PyPI

```text
[ ] Trusted Publisher + Environments configurados (s1-A, primeira vez)
[ ] CHANGELOG.md com a entrada da nova versão
[ ] version bumpada no pyproject.toml
[ ] deps são de registro (sem git+https / allow-direct-references)
[ ] test.yml verde no main
[ ] git tag vX.Y.Z && git push origin vX.Y.Z
[ ] aprovar o gate do Environment pypi (se houver required reviewer)
[ ] verificar: pip install <pacote>==X.Y.Z em venv limpa
```

### Fluxo B — GitHub Releases

```text
[ ] Secret INDEX_DISPATCH_TOKEN configurado no repo (primeira vez)
[ ] CHANGELOG.md com a entrada da nova versão
[ ] version bumpada no pyproject.toml
[ ] deps são de registro (sem git+https / allow-direct-references)
[ ] test.yml verde no main
[ ] git tag vX.Y.Z && git push origin vX.Y.Z
[ ] verificar: GitHub Release criado com .whl e .tar.gz anexados
[ ] verificar: quantilica-index atualizado (~1 min após o dispatch)
[ ] verificar: quantilica install <fonte> em venv limpa
```
