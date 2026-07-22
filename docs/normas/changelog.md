---
title: Padronização de CHANGELOG.md
description: Norma canônica do CHANGELOG.md dos pacotes de dados Quantilica — formato Keep a Changelog + SemVer, cabeçalho padrão, categorias permitidas e fluxo de release.
---

# Padronização de CHANGELOG.md

Todo **pacote de dados publicável** do ecossistema mantém um `CHANGELOG.md` na raiz
do seu repositório. É a fonte de verdade _por pacote_ sobre o que mudou em cada
versão — o [changelog do site](../changelog.md) é apenas o resumo cross-pacote dos
marcos maiores, não substitui os arquivos por repo.

Esta norma define o formato único adotado por todos eles. Complementa a norma de
[Publicação e Release](publicacao.md) (que trata do fluxo de tag → PyPI) e a de
[Padrões de Escrita](escrita.md) (que trata do README).

---

## 1. Escopo — quem precisa de um `CHANGELOG.md`

**Obrigatório** em todo pacote versionado por [SemVer](https://semver.org/lang/pt-BR/)
e distribuído como biblioteca — os fetchers, os motores SQL (`*-sql`) e as fundações
(`quantilica-core`, `quantilica-analytics`, `quantilica-cli`, `quantilica-catalog`).
Ou seja: se o repositório tem `[project] version` no `pyproject.toml` e é (ou será)
instalável, ele tem um `CHANGELOG.md`.

**Isento:**

- **Catálogos de ETL** (`sidra-pipelines`, `bcb-sgs-pipelines`) — não têm `version`
  nem API; suas mudanças são as dos arquivos `fetch.toml`/`transform.sql`,
  rastreadas pelo git.
- **Repositórios de artefato de dados** (ex.: `datasus-metadata`) — versionam
  dados gerados, não código de API.
- **Aplicações web privadas** (`*-app`, `*-db`, `quantilica-web`, `docs`) — não
  seguem esta norma; se registrarem mudanças, é em `docs-internal/`.

---

## 2. Cabeçalho padrão

Todo `CHANGELOG.md` começa **exatamente** com este cabeçalho (idioma pt-BR, links
para as versões pt-BR das especificações):

```markdown
# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).
```

---

## 3. Entradas de versão

- Uma entrada por versão, com o título `## [x.y.z] - AAAA-MM-DD` (data ISO 8601 da
  publicação da tag).
- **Ordem decrescente**: a versão mais recente no topo, logo abaixo do cabeçalho.
- A versão do título casa com `[project] version` do `pyproject.toml` e com a tag
  `vX.Y.Z` que dispara o release.
- Um parágrafo de contexto **opcional** pode preceder as categorias, quando a
  versão precisa de uma explicação de fundo (ex.: primeiro release no PyPI, quebra
  de compatibilidade). Mantenha-o curto.

Mudanças ainda não lançadas ficam sob `## [Não lançado]` no topo; ao publicar,
renomeie o bloco para `## [x.y.z] - AAAA-MM-DD`.

---

## 4. Categorias permitidas

Apenas as seis categorias do Keep a Changelog, como `### ` dentro de cada versão,
nesta grafia pt-BR e **só as que se aplicam** (não crie seções vazias):

| Seção | Quando usar |
|---|---|
| `### Adicionado` | Novas funcionalidades, comandos, módulos ou APIs. |
| `### Alterado` | Mudanças em comportamento, dependências ou API existente. |
| `### Descontinuado` | Funcionalidade ainda presente, mas marcada para remoção. |
| `### Removido` | Funcionalidade/código removidos nesta versão. |
| `### Corrigido` | Correções de bug (inclui _hardening_ e robustez). |
| `### Segurança` | Correções de vulnerabilidade. |

Não invente categorias (`### Melhorado`, `### Notas`, `### Robustez`, …) — a única
seção adicional permitida é `### Histórico anterior`, no bootstrap de repos com
tags antigas (§7). Uma observação que não é uma mudança catalogável vai como
_blockquote_ ao final da entrada:

```markdown
> **Nota:** a 0.7.2 foi publicada declarando `quantilica-core[cli]` por engano;
> a 0.7.3 corrige para `quantilica-core`.
```

---

## 5. Como escrever cada item

Seguindo a [norma de escrita](escrita.md):

- **Idioma:** prosa em português; identificadores, nomes de função, flags de CLI e
  nomes de pacote em inglês, sempre em `código`.
- **Altitude:** descreva o efeito para quem usa o pacote, não o diff. "Corrige X que
  quebrava com `AttributeError`" é melhor que "muda `row.series_name`".
- **Concisão:** uma linha por mudança sempre que possível; quebre em ~88 colunas
  para casar com o `line-length` do repo.
- Sem emoji decorativo (idem README).

---

## 6. Relação com SemVer, tags e o changelog do site

- A categoria da mudança sugere o _bump_ [SemVer](https://semver.org/lang/pt-BR/):
  `Corrigido` → PATCH; `Adicionado` → MINOR; `Removido`/quebra de API em
  `Alterado` → MAJOR.
- A **tag `vX.Y.Z`** é o release (dispara `publish.yml`); o `CHANGELOG.md` deve
  conter a entrada dessa versão **antes** de criar a tag.
- Marcos maiores (novo pacote, publicação no PyPI, renomeação) também entram, de
  forma resumida e cross-pacote, no [changelog do site](../changelog.md). O detalhe
  fica sempre no `CHANGELOG.md` do repo.

---

## 7. Bootstrap de repositórios com histórico

Ao adotar o changelog num repo que já tem várias tags de release, **não reconstrua**
o histórico linha a linha (risco de inventar mudanças). A primeira entrada documenta
o estado atual do pacote e uma seção `### Histórico anterior` remete às tags:

```markdown
## [3.0.0] - 2026-05-19

Primeira entrada em formato Keep a Changelog; documenta o estado do pacote nesta
versão.

### Adicionado

- ...

### Histórico anterior

Versões até a 3.0.0 antecedem a adoção deste changelog e estão registradas nas tags
do repositório: 2.1.1 (2026-02-09), 2.0.0 (2026-01-31), 1.0.0 (2025-12-31), …
```

A partir daí, cada release ganha sua entrada normalmente.

---

## 8. Exemplo completo

```markdown
# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.3.1] - 2026-07-22

### Corrigido

- `Config.__str__` não expõe mais a senha do banco em texto puro (mascarada como `***`).

### Removido

- Código morto sem chamadores: `build_localidade_lookup`, `Storage.read_data_dir`.

## [1.3.0] - 2026-07-16

### Adicionado

- Primeiro release público no PyPI.
```

---

## 9. Checklist

```text
[ ] CHANGELOG.md na raiz, com o cabeçalho padrão (§2)
[ ] entrada da nova versão no topo: ## [x.y.z] - AAAA-MM-DD (§3)
[ ] só as categorias de §4, sem seções vazias nem inventadas
[ ] versão casa com pyproject.toml e com a tag vX.Y.Z
[ ] README aponta para o CHANGELOG.md (ver norma de escrita)
[ ] entrada escrita antes de criar a tag de release
```
