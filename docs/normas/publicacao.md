---
title: Publicação e Release
description: Processo canônico de release dos pacotes Quantilica — Fluxo A (PyPI/OIDC) para pacotes âncora e Fluxo B (GitHub Releases + índice estático) para fetchers. Inclui workflows de CI, CHANGELOG e versionamento por tags.
---

# Publicação e Release

Os pacotes públicos do ecossistema Quantilica seguem **dois fluxos de release distintos**, dependendo do canal de distribuição:

| Fluxo | Canal | Pacotes | Workflow |
|---|---|---|---|
| **A — PyPI (OIDC)** | PyPI oficial | `quantilica-core`, `quantilica-cli` + **exceção legada transitória**: `sidra-fetcher`, `sidra-sql`, `bcb-sgs-sql`¹ | `publish.yml` com Trusted Publishing |
| **B — GitHub Releases** | Índice estático próprio | `quantilica-analytics`, `quantilica-catalog`, todos os `*-fetcher` (exceto `sidra-fetcher`, no Fluxo A como legado)² | `publish.yml` com GitHub Release + dispatch |

> Fetchers distribuídos via índice próprio não passam pelo PyPI. Instalam-se via `quantilica install <fonte>`, que consulta o índice hospedado em `quantilica-index` no GitHub Pages. Aqui, `<fonte>` é a chave do `SOURCES_REGISTRY` (`quantilica-cli/src/quantilica/cli/sources.py`: `anac`, `anp`, `bcb-sgs`, `comex`, `cvm`, `datasus`, `inmet`, `pdet`, `rtn`, `sidra`, `td`, `tse`) — não necessariamente o nome do pacote (ex.: `td` → `tesouro-direto-fetcher`).
>
> ¹ Legado transitório declarado (ADRs `2026-07-30-distribuicao-fetchers-github-releases` e `2026-10-08-fetcher-cli-wrapper-e-canal-de-distribuicao`): permanecem no PyPI por back-compat até migração para o Fluxo B (item do plano; confirmar `publish.yml` dos dois `*-sql` antes de migrar).
>
> ² `datasus-fetcher` e `bcb-sgs-fetcher` já publicam por Fluxo B (`Release to GitHub & Notify Index`).

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

Dispara em push/PR para `main` (+ `workflow_dispatch`); roda `ruff check`, `ruff format --check` e `pytest` numa matriz 3.12/3.13 via `uv`. **Três regras obrigatórias**, cada uma nascida de falha real de CI:

1. **Um único `uv sync` com retry** — o `--index` do índice próprio é sempre passado (pacotes âncora residem no PyPI, mas `quantilica-analytics`/`quantilica-catalog` só existem no índice), e o índice (GitHub Pages) já deu flake de DNS no runner (2026-08-23): sem retry, um push bom fica vermelho até o próximo push.
2. **Todos os passos pós-sync usam `uv run --no-sync`** — cada `uv run` *sem* essa flag re-resolve o ambiente e **remove os extras** instalados no sync (caso `anp`: `ModuleNotFoundError: polars`, 2026-08-29).
3. **O pyproject do repo não contém `[tool.uv.sources] { workspace = true }`** — é uma configuração do clone de desenvolvimento; num repo standalone o CI não resolve workspace (caso `anac`, 2026-08-29).

```yaml
name: Test

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

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
        run: |
          for i in 1 2 3; do
            if uv sync --group dev --python ${{ matrix.python-version }} \
                --index https://index.quantilica.com/simple/ \
                --index-strategy unsafe-best-match; then
              exit 0
            fi
            echo "::warning::uv sync falhou (tentativa $i/3); nova tentativa em 10s"
            sleep 10
          done
          exit 1

      - name: Lint with ruff
        run: |
          uv run --no-sync ruff check src/ tests/
          uv run --no-sync ruff format --check src/ tests/

      - name: Run tests
        run: uv run --no-sync pytest
```

Se o repo tem testes que exigem um extra opcional do próprio pacote, use a variante com `--extra <nome>` no `uv sync`. **Quando usar:** sempre que a suíte importar módulos do extra (ex.: `reader`/`contracts`/`wrangling` que importam `polars` via o extra `analysis`) — sem o extra, esses testes quebram com `ModuleNotFoundError` no CI mesmo passando no workspace. Já adotada em `anac`, `anp`, `cvm`, `inmet`, `rtn`, `pdet` e `datasus` (todos com `--extra analysis`):

```yaml
      - name: Install dependencies
        run: |
          for i in 1 2 3; do
            if uv sync --group dev --extra analysis --python ${{ matrix.python-version }} \
                --index https://index.quantilica.com/simple/ \
                --index-strategy unsafe-best-match; then
              exit 0
            fi
            echo "::warning::uv sync falhou (tentativa $i/3); nova tentativa em 10s"
            sleep 10
          done
          exit 1
```

(todo o resto do `test.yml` permanece igual, sempre com `uv run --no-sync` — regra 2 acima).

> **Deriva cross-repo:** workflows por pacote não enxergam a quebra de um vizinho (ex.: função removida de `sidra-fetcher` quebrando `sidra-sql` em silêncio por ~1 mês). Para isso existe `integration.yml` em `quantilica-core` (cron diário): monta o uv workspace com todos os members, roda o suite conjunto e veta o vazamento de `workspace = true`.

### `publish.yml` — Fluxo A: build → TestPyPI → PyPI (OIDC)

Para `quantilica-core`, `quantilica-cli` e — como **exceção legada transitória** (ADRs `2026-07-30` e `2026-10-08`) — `sidra-fetcher`, `sidra-sql` e `bcb-sgs-sql`. Dispara em push de tag `v*`. Um job de `build` isolado, depois dois jobs de publish em cadeia (TestPyPI → PyPI), cada um num Environment com `id-token: write`.

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

Para os demais `*-fetcher`, `quantilica-analytics` e `quantilica-catalog`. Dispara em push de tag `v*`. Cria um GitHub Release com os artefatos e dispara o rebuild do índice estático.

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

## 4. Versionamento, SemVer e Política de Bump

O ecossistema Quantilica adere estritamente ao [Semantic Versioning 2.0.0](https://semver.org/lang/pt-BR/) (`MAJOR.MINOR.PATCH`). A versão canônica vive em `[project] version` do `pyproject.toml`.

### 4.1. Critérios de Incremento (Quando subir cada dígito)

| Tipo de Bump | Formato | Quando Aplicar | Exemplos no Ecossistema |
|---|---|---|---|
| **`PATCH`** | `x.y.Z` $\to$ `x.y.Z+1` | Correções de bugs, tolerância a falhas na extração, melhorias de desempenho internas sem mudança de assinatura, correções de tipagem (`py.typed`), atualizações de segurança em dependências e documentação. | Fix em parser de HTML de tabela IBGE; correção de timeout em endpoint BCB; bump de segurança de `httpx2`. |
| **`MINOR`** | `x.Y.z` $\to$ `x.Y+1.0` | Adição de novos endpoints, novos datasets/tabelas em fetchers, novos comandos de CLI retrocompatíveis, novos parâmetros opcionais com valor padrão preservado, ou introdução de `DeprecationWarning`. | Adição do endpoint de `royalties` no `anp-fetcher`; novo subcomando de exportação no `quantilica-cli`. |
| **`MAJOR`** | `X.y.z` $\to$ `X+1.0.0` | Quebras de compatibilidade com versões anteriores (breaking changes): remoção ou renomeação de funções/classes públicas, alteração estrutural no retorno de dados, remoção de argumentos legados ou quebra de contrato de schemas. | Remoção do comando `quantilica fetch <fonte>` em prol de `quantilica <fonte>`; refatoração de retorno de dataclasses para novo formato inalterável. |

> **Nota sobre imutabilidade:** Uma versão publicada no PyPI ou no índice estático é **estritamente imutável**. Havendo qualquer erro de empacotamento ou código após a publicação, incremente uma nova versão `PATCH`.

### 4.2. Delineamento: Bibliotecas vs. Aplicações Web

| Dimensão | Bibliotecas & Fetchers (Fluxo A / Fluxo B) | Aplicações Web (`quantilica-portal`) |
|---|---|---|
| **Arquivos tocados no bump** | `pyproject.toml` + `CHANGELOG.md` | `pyproject.toml` + `uv.lock` |
| **Versionamento do `uv.lock`** | **PROIBIDO**. Bibliotecas não versionam `uv.lock` para permitir resolução dinâmica por consumidores. | **OBRIGATÓRIO**. `uv.lock` é commitado (`uv lock && uv lock --check`) para garantir deploys 100% determinísticos no VPS. |
| **`CHANGELOG.md`** | **OBRIGATÓRIO** no formato Keep a Changelog. | **ISENTO** (rastreado por releases git e notas internas). |
| **Tipo de Tag Git** | `vX.Y.Z` simples ou anotada. | `git tag -a vX.Y.Z -m "vX.Y.Z"` anotada. |

### 4.3. Regra de Isolamento Absoluto do Commit de Release (Zero-Feature Release)

Nunca misture código de funcionalidades (`feat`, `fix`, `refactor`) no mesmo commit que realiza o bump de versão:

1. **Commit de Funcionalidade:** Adicione e commite todas as implementações (`git add .` e `git commit -m "feat/fix: ..."`). A working tree deve ficar **100% limpa**.
2. **Commit Exclusivo de Release:** Altere apenas os arquivos de metadados (`pyproject.toml` + `CHANGELOG.md` em pacotes; `pyproject.toml` + `uv.lock` em apps) e faça o commit dedicado:
   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "release: vX.Y.Z"
   ```
3. **Criação e Push de Tags:**
   ```bash
   git tag vX.Y.Z
   git push origin main && git push origin vX.Y.Z
   ```

---

## 5. Cadeia de Dependências e Cascata Upstream-Downstream

Dependa **sempre por versão de registro** (`pacote>=X.Y`), nunca por `git+https`/`allow-direct-references`.

### Ordem Obrigatória de Publicação (Upstream $\to$ Downstream)
Quando uma funcionalidade afetar múltiplos pacotes interdependentes (ex: uma alteração em `quantilica-core` que é consumida por `quantilica-analytics` e depois por `sidra-fetcher`):
1. Faça o release e push da tag do pacote upstream (`quantilica-core`).
2. **Aguarde a conclusão do workflow de CI/CD** (PyPI ou GitHub Release + `quantilica-index`) e certifique-se de que a nova versão já está resolúvel no índice.
3. Somente então atualize o pin mínimo no `pyproject.toml` do pacote downstream (ex: `quantilica-core>=0.5.0`), teste localmente e proceda com o release do downstream.

> **Atenção:** Atualizar o pin downstream antes da publicação do upstream fará com que o workflow `test.yml` ou `publish.yml` do downstream falhe no GitHub Actions por pacote não encontrado.

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
[ ] verificar: quantilica install <fonte> em venv limpa (<fonte> = chave do SOURCES_REGISTRY)
```
