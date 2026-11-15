---
title: Publicação e Release
description: Processo de release dos pacotes: Fluxo A (PyPI/OIDC) para os pacotes âncora e Fluxo B (GitHub Releases + índice) para os fetchers.
---

# Publicação e Release

Os pacotes públicos do ecossistema Quantilica seguem **dois fluxos de release distintos**, dependendo do canal de distribuição:

| Fluxo | Canal | Pacotes | Workflow |
|---|---|---|---|
| **A — PyPI (OIDC)** | PyPI oficial | `quantilica-core`, `quantilica-cli` | `publish.yml` com Trusted Publishing |
| **B — GitHub Releases** | Índice estático próprio | `quantilica-analytics`, `quantilica-catalog`, todos os `*-fetcher` e `*-sql` (inclui `ibge-sidra-fetcher`, `sidra-sql`, `bcb-sgs-sql`) | `publish.yml` com GitHub Release + dispatch |

> Pacotes distribuídos via índice próprio não passam pelo PyPI. Instalam-se via `quantilica install <fonte>`, que consulta o índice hospedado em `quantilica-index` no GitHub Pages. Aqui, `<fonte>` é a chave do `SOURCES_REGISTRY` local (`quantilica-cli/src/quantilica/cli/sources.py`) mesclada com o `sources.json` remoto do índice; chaves remotas atuais: `anac`, `anp`, `bcb-sgs`, `bcb-sgs-sql`, `comex`, `cvm`, `datasus`, `inep`, `inmet`, `pdet`, `rfb-cnpj`, `rtn`, `sidra`, `sidra-sql`, `tesouro-direto`, `tse`, `quantilica-analytics`, `quantilica-catalog` (o registro local tem também `td`) — não necessariamente o nome do pacote (ex.: `td` → `tesouro-direto-fetcher`).
>
> `sidra-fetcher 0.10.5` (hoje `ibge-sidra-fetcher`), `sidra-sql 2.0.1` e `bcb-sgs-sql 0.2.2` (2026-10-08) foram os primeiros releases no Fluxo B; versões anteriores permanecem congeladas no PyPI.

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

> **Deriva cross-repo:** workflows por pacote não enxergam a quebra de um vizinho (ex.: função removida de `ibge-sidra-fetcher` quebrando `sidra-sql` em silêncio por ~1 mês). Para isso existe `integration.yml` em `quantilica-core` (cron diário): monta o uv workspace com todos os members, roda o suite conjunto e veta o vazamento de `workspace = true`.

### `public-hygiene.yml` — termos internos (todos os repositórios públicos)

Workflow idêntico em todos os repositórios públicos, independente do fluxo de
publicação. Veta termos internos (planos, decisões, repositórios privados,
infraestrutura) em `CHANGELOG.md`, `README*` e nas mensagens de commit dos PRs. A
regra e as categorias estão em [Padronização de CHANGELOG.md](changelog.md#51-o-que-um-changelog-nunca-cita);
deve estar verde no `main` antes de criar a tag, como o `test.yml`.

### `publish.yml` — Fluxo A: build → TestPyPI → PyPI (OIDC)

Para `quantilica-core` e `quantilica-cli`. Dispara em push de tag `v*`. Um job de `build` isolado, depois dois jobs de publish em cadeia (TestPyPI → PyPI), cada um num Environment com `id-token: write`.

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

Para todos os `*-fetcher`, `*-sql`, `quantilica-analytics` e `quantilica-catalog`. Dispara em push de tag `v*`. Cria um GitHub Release com os artefatos e dispara o rebuild do índice estático.

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
          files: |
            dist/*.whl
            dist/*.tar.gz
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
| **Versionamento do `uv.lock`** | **PROIBIDO**. Bibliotecas não versionam `uv.lock` para permitir resolução dinâmica por consumidores. | **OBRIGATÓRIO**. `uv.lock` é commitado (`uv lock && uv lock --check`) para garantir deploys 100% determinísticos no servidor. |
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
Quando uma funcionalidade afetar múltiplos pacotes interdependentes (ex: uma alteração em `quantilica-core` que é consumida por `quantilica-analytics` e depois por `ibge-sidra-fetcher`):
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

---

## 7. Renomear um fetcher

Renomear é uma operação com contrato: o resultado é o mesmo em qualquer fetcher e quase tudo é derivado do registro público. A meta é tocar à mão **no máximo quatro repositórios** (o fetcher, a raiz do workspace, `quantilica-index` e, quando houver import, `quantilica-workers`); portal, dashboard, `quantilica-cli`, site e skills não recebem commit. O docs recebe um commit, mas **gerado pelo script**: ele move a página e regera os blocos, sem edição à mão. Por isso o script lista o docs entre os repositórios tocados. O nome novo segue a [convenção de nomes](cli-fetchers.md#nomes-de-fetchers).

### Contrato

1. **O id antigo vira apelido.** O `FetcherInfo` do fetcher passa a declarar o id novo e traz o antigo em `aliases`. A distribuição e o repositório antigos entram no `historico` da seção do fetcher em `quantilica-index/registro.toml`, com `distribution`, `repo`, `id` e `data`.
2. **O que já está persistido continua válido sem migração manual.**
    - URLs públicas: o apelido de fonte redireciona (301) para o id canônico.
    - `catalog.dataset.fetcher_id` e `core.fetcher_run` no portal: o `registry sync` canoniza o id que virou apelido (`fetcher_id` é a identidade do fetcher).
    - Fichas do catálogo (`catalog.source`, `catalog.dataset` e filhos): o comando `catalog-canonizar` do portal (o `deploy.sh` o roda depois do `registry sync`) aplica a regra do `aliases.py`. Fetcher **fora** do `hub_catalog.json` tem as fichas renomeadas para o id novo, com fusão se a ficha nova já existir; fetcher **do** hub (`rtn`, `anp`, `bcb-sgs`...) mantém a fonte do hub, e o apelido não a renomeia. O `registry sync` do workers não toca nas chaves do catálogo, porque só o portal conhece o hub.
    - Lake, `source_id`, `raw_subdir` e os nomes de cron **não mudam**. O script fixa o `source_id` antigo no `FetcherApp` (ele derivava do `name`), e `infra/fetchers.toml` mantém `cron_names` e `raw_subdir`. O registro guarda o mapa.
3. **O inevitável é feito por script**: `infra/rename_fetcher.py`.
4. **Sem módulo de compatibilidade.** O módulo e a distribuição antigos deixam de existir; o índice mantém as wheels antigas congeladas em `/simple/<id-antigo>-fetcher/` e o `historico` alimenta os redirects do docs, o `quantilica install` do apelido e as sondas do cli. A quebra entra no `CHANGELOG.md` do fetcher, em versão MINOR (pré-1.0) ou MAJOR.

### O script

```bash
# ensaio (padrão): imprime o plano e não escreve nada
python3 infra/rename_fetcher.py --de transparencia-sp --para ensaio-sp
# aplica
python3 infra/rename_fetcher.py --de transparencia-sp --para ensaio-sp --aplicar
```

| Opção | Efeito |
|---|---|
| `--aplicar` | escreve; sem ela é ensaio |
| `--forcar` | trabalha mesmo com repositório git que tem arquivo rastreado alterado (o padrão é recusar) |
| `--raiz DIR` | raiz do workspace (padrão: a do script) |
| `--registro URL\|ARQUIVO` | registro público de origem (padrão: o do índice) |
| `--data AAAA-MM-DD` | data do `historico` (padrão: hoje) |

O script recusa um id novo fora da convenção, um id que já existe (id ou apelido) e uma árvore suja. É determinístico: a mesma árvore e a mesma `--data` produzem o mesmo resultado.

**O que ele reescreve:**

- no pacote do fetcher: `pyproject.toml` (nome, script, entry point `quantilica.fetchers`, URLs, `packages`), o diretório do módulo (`git mv`), os imports, `FetcherApp(name=)`, `producer=`, README, docs e testes, e acrescenta a entrada de quebra no `CHANGELOG.md`;
- no `FetcherInfo`: o id novo, o antigo em `aliases`, e o `source_id` fixado no valor antigo;
- em `infra/fetchers.toml`: a seção renomeada, com `cron_names` e `raw_subdir` mantidos;
- em `quantilica-index/registro.toml`: a seção renomeada e a entrada no `historico`;
- nos outros repositórios do workspace: imports do módulo antigo em `.py` e a dependência em `pyproject.toml` (só nas listas de dependências e em `[tool.uv.sources]`; comentários e descrições não mudam);
- no docs: `git mv` de `docs/fontes/<pasta>/<distribuição-antiga>.md` para a página nova, a troca da distribuição, do módulo e do comando no texto da página, os links `<distribuição-antiga>.md` do `index.md` da pasta e os blocos gerados (`hooks/registro.py --escrever`, lendo o registro com o id novo; um id citado na `ordem` do `properdocs.yml` segue valendo pelo apelido), de modo que `tools/check_pages.py` passa sem edição à mão. O redirect da página antiga para a nova vem do `historico`, sem edição;
- nas listas geradas (`pyproject.toml`, `bootstrap.sh`, `bootstrap.ps1`, `.gitignore`, tabelas do `README.md` e do `AGENTS.md`, matriz do CI de integração): chama `registry_build.py --listas` com o registro já com o id novo.

**O que ele imprime e não faz:** a lista dos repositórios tocados (a métrica da meta), os *residuais* (menções ao nome antigo que ficam para revisão: muitas são dado persistido, como `SOURCE_ID`, a chave de `quantilica.lake` e `/data/<id>`, que devem ficar) e o checklist abaixo.

### Passos fora do git

Em ordem, depois de revisar o ensaio, aplicar e commitar por repositório:

```text
[ ] testes e lint do fetcher; commit em cada repositório tocado (commits separados da release)
[ ] release MINOR do fetcher (o índice precisa da wheel nova antes do registro)
[ ] workflow_dispatch do quantilica-index: publica o registro com o id novo e /simple/<id-novo>-fetcher/
[ ] registry sync no servidor do portal LOGO DEPOIS da publicação e ANTES de instalar a versão nova nas máquinas que rodam os fetchers:
    canoniza o fetcher_id e faz o portal conhecer o apelido. Se uma máquina rodar o catalog sync com o id
    novo antes disso, nasce uma ficha nova ao lado da antiga e a canonização do catálogo passa a fundir.
[ ] catálogo do portal: o deploy roda o catalog-canonizar; sem deploy, rode
    docker compose run --rm --no-deps -T quantilica-portal python -m quantilica_portal.cli catalog-canonizar --dry-run
    e depois sem --dry-run (fonte do hub não muda; fora do hub vira o id novo)
[ ] gh repo rename <id-novo>-fetcher --repo Quantilica/<id-antigo>-fetcher
    (nunca crie outro repositório com o nome antigo: quebra o redirecionamento do GitHub)
[ ] git remote set-url origin https://github.com/Quantilica/<id-novo>-fetcher.git
    em todas as máquinas que têm o clone
[ ] mv <id-antigo>-fetcher <id-novo>-fetcher na raiz do workspace de cada máquina
[ ] uv sync --all-packages --all-extras  (um `uv sync` puro remove o cli e os fetchers do ambiente)
[ ] registry_build.py --check --listas e fetchers_ops.py check contra o registro publicado
[ ] ambientes do lake que instalam o pacote: trocar a distribuição antiga pela nova
```

### O que não é renome de fetcher

Vocabulário de produto (o nome SIDRA, `/hub/ibge`, rotas, agendas, schemas), `source_id`, diretórios do lake e nomes de cron persistidos ficam como estão: nada se renomeia em disco nem em banco.

