---
title: Publicação e Release
description: Processo canônico de release dos pacotes Quantilica no PyPI — Trusted Publishing (OIDC), workflows de CI, CHANGELOG e versionamento por tags.
---

# Publicação e Release

Os pacotes públicos do ecossistema são distribuídos no **PyPI** e publicados de forma automatizada via **Trusted Publishing (OIDC)** — sem tokens de API de longa duração. Esta norma descreve o processo padrão, já aplicado a `quantilica-core`, `sidra-fetcher`, `sidra-sql`, `datasus-fetcher`, `bcb-sgs-fetcher` e `bcb-sgs-sql`.

---

## 1. Pré-requisitos (uma vez por pacote)

Feito manualmente no site do PyPI/TestPyPI e no GitHub — **não** versionado no repo:

1. Conta em [pypi.org](https://pypi.org) e em [test.pypi.org](https://test.pypi.org) (independentes).
2. **Trusted Publisher pendente** cadastrado em **ambos** os índices (Publishing → Add a pending publisher), antes mesmo do primeiro upload:
   - Owner: `Quantilica`
   - Repository: nome do repo
   - Workflow filename: `publish.yml`
   - Environment name: `pypi` (e um segundo publisher com `testpypi` para o índice de teste)
3. Dois **GitHub Environments** no repo (Settings → Environments): `pypi` e `testpypi`. Recomendado exigir *required reviewer* no `pypi` — freio manual contra tag acidental.

Não crie API tokens: o Trusted Publishing os dispensa.

---

## 2. Workflows de CI

Todo repo publicável tem dois workflows em `.github/workflows/`.

### `test.yml` — lint + testes

Dispara em push/PR para `main`; roda `ruff check`, `ruff format --check` e `pytest` numa matriz 3.12/3.13 via `uv`.

```yaml
name: Test
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix: { python-version: ["3.12", "3.13"] }
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with: { enable-cache: true }
      - run: uv python install ${{ matrix.python-version }}
      - run: uv sync --group dev
      - run: |
          uv run ruff check src/ tests/
          uv run ruff format --check src/ tests/
      - run: uv run pytest
```

### `publish.yml` — build → TestPyPI → PyPI

Dispara em push de tag `v*`. Um job de `build` isolado, depois dois jobs de publish em cadeia (TestPyPI → PyPI), cada um num Environment com `id-token: write`. O gate do Environment `pypi` (se tiver reviewer) pausa até aprovação manual.

```yaml
name: Publish to PyPI
on:
  push: { tags: ["v*"] }
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv build
      - uses: actions/upload-artifact@v4
        with: { name: dist, path: dist/ }

  publish-testpypi:
    needs: build
    runs-on: ubuntu-latest
    environment: { name: testpypi, url: https://test.pypi.org/p/<pacote> }
    permissions: { id-token: write }
    steps:
      - uses: actions/download-artifact@v4
        with: { name: dist, path: dist/ }
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/
          skip-existing: true

  publish-pypi:
    needs: publish-testpypi
    runs-on: ubuntu-latest
    environment: { name: pypi, url: https://pypi.org/p/<pacote> }
    permissions: { id-token: write }
    steps:
      - uses: actions/download-artifact@v4
        with: { name: dist, path: dist/ }
      - uses: pypa/gh-action-pypi-publish@release/v1
```

- `skip-existing: true` **só** no TestPyPI (permite re-run com a mesma versão); no PyPI real deixe falhar se a versão já existir.
- `uv build` gera sdist + wheel. **Atenção:** o wheel é construído a partir do sdist; valide que o sdist→wheel contém o código (um `[tool.hatch.build]` mal configurado pode gerar wheel vazio — cheque com `unzip -l dist/*.whl`).

---

## 3. `CHANGELOG.md`

Todo pacote publicável mantém um `CHANGELOG.md` no formato [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) + [SemVer](https://semver.org/lang/pt-BR/), com uma entrada por versão (`## [x.y.z] - AAAA-MM-DD`) e as seções `### Adicionado / Alterado / Corrigido / …`. O `CHANGELOG.md` de cada repo é a fonte por-pacote; o [changelog do site](../changelog.md) é o resumo cross-pacote. A entrada da nova versão deve existir **antes** de criar a tag de release.

O formato completo — cabeçalho padrão, categorias permitidas e bootstrap de repos com histórico — está na norma dedicada de [Padronização de CHANGELOG.md](changelog.md).

---

## 4. Versionamento e tags

- **SemVer**: PATCH = fix; MINOR = feature compatível; MAJOR = quebra de API.
- A versão vive em `[project] version` do `pyproject.toml`.
- A **tag `vX.Y.Z`** é o release: criá-la e dar push dispara o `publish.yml`.
- Uma versão publicada é **imutável**. Errou? Publique uma nova; se necessário, faça *yank* da anterior pela interface web (não há API/twine para yank).

---

## 5. Cadeia de dependências

Dependa **por versão de registro** (`pacote>=X.Y`), nunca por `git+https`/`allow-direct-references` (o PyPI rejeita dependências VCS). Publique **de cima para baixo**: o upstream primeiro, depois troque a dependência do downstream de git para registro. Ex.: `quantilica-core` → `sidra-fetcher` (`quantilica-core>=0.3.1`) → `sidra-sql` (`sidra-fetcher>=0.7.2`).

> Fetchers **não** declaram `typer`/`rich` (nem via extra) — esses vêm do host `quantilica-cli`. Ver [Padronização de CLI](cli-fetchers.md).

---

## 6. Checklist de release

```text
[ ] Trusted Publisher + Environments configurados (§1, uma vez)
[ ] CHANGELOG.md com a entrada da nova versão
[ ] version bumpada no pyproject.toml
[ ] deps são de registro (sem git+https / allow-direct-references)
[ ] test.yml verde no main
[ ] git tag vX.Y.Z && git push origin vX.Y.Z
[ ] aprovar o gate do Environment pypi
[ ] verificar: pip install <pacote>==X.Y.Z em venv limpa
```
