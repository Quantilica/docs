# Padrão de Documentação — Quantilica

Este documento define o padrão de README adotado por todos os repositórios da organização. Novos pacotes e contribuições devem seguir este guia.

---

## Regras Gerais

- **Idioma:** Todo o texto em prosa (descrições, títulos de seção, comentários) é escrito em **português**. Exemplos de código, flags de CLI, identificadores e nomes de funções permanecem em inglês.
- **Emoji:** Nenhum emoji decorativo em cabeçalhos ou prosa. Usar somente onde necessário para clareza técnica (ex: tabelas comparativas).
- **Instalação:** Pacotes publicados no PyPI (`quantilica-core`, `sidra-fetcher`, `sidra-sql`, `datasus-fetcher`, `bcb-sgs-fetcher`, `bcb-sgs-sql`) usam `pip install <pacote>` / `uv add <pacote>`; os demais são instalados via `git+https://`.

---

## Badges

Linha de badges imediatamente após o título `# `, seguindo o padrão `flat-square`:

```markdown
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square) ![Python](https://img.shields.io/badge/python-3.12+-blue.svg?style=flat-square)
```

- A versão Python deve corresponder ao `requires-python` do `pyproject.toml`.
- Licença `MIT` para todos os pacotes.
- Badge de CI apenas em pacotes com workflow de testes ativo.
- **Pacotes publicados no PyPI** adicionam um badge de versão do PyPI:
  `![PyPI](https://img.shields.io/pypi/v/<pacote>.svg?style=flat-square)`.

---

## Template para Pacotes de Dados (fetchers)

```markdown
# <nome-do-pacote>: <descrição curta>

![License: MIT](...) ![Python](...)

<2-3 frases: o que faz, qual fonte, para quem>

---

## Instalação

## Uso Rápido

## CLI           ← apenas se o pacote instala um comando

## API Python    ← apenas se expõe uma API programática

## Datasets / Fontes de Dados   ← se aplicável

## Desenvolvimento

## Changelog       ← link para o CHANGELOG.md do repo

## Licença
```

---

## Template para Pacotes de Infraestrutura

```markdown
# <nome-do-pacote>: <descrição curta>

![License: MIT](...) ![Python](...)

<2-3 frases>

---

## Instalação

## Uso Rápido

## Módulos

## Princípios de Design

## Desenvolvimento

## Changelog       ← link para o CHANGELOG.md do repo

## Licença
```

---

## Seções Obrigatórias

### `## Instalação`

Para pacotes **publicados no PyPI** (`quantilica-core`, `sidra-fetcher`, `sidra-sql`, `datasus-fetcher`, `bcb-sgs-fetcher`, `bcb-sgs-sql`):

```markdown
## Instalação

\`\`\`bash
pip install <pacote>
\`\`\`

Com [uv](https://github.com/astral-sh/uv):

\`\`\`bash
uv add <pacote>
\`\`\`
```

Para pacotes **ainda não publicados** (instalados via `git+https`):

```markdown
## Instalação

\`\`\`bash
pip install git+https://github.com/Quantilica/<pacote>.git
\`\`\`

Com [uv](https://github.com/astral-sh/uv):

\`\`\`bash
uv add "git+https://github.com/Quantilica/<pacote>.git"
\`\`\`
```

Para extras opcionais: `pip install "<pacote>[extra]"` (PyPI) ou `pip install "<pacote>[extra] @ git+https://github.com/Quantilica/<pacote>.git"` (git).

### `## Desenvolvimento`

```markdown
## Desenvolvimento

\`\`\`bash
git clone https://github.com/Quantilica/<pacote>.git
cd <pacote>
uv sync --dev
uv run pytest
\`\`\`
```

### `## Changelog`

Todo pacote mantém um `CHANGELOG.md` (formato Keep a Changelog — ver [Padronização de CHANGELOG.md](changelog.md)); o README apenas aponta para ele:

```markdown
## Changelog

Veja [CHANGELOG.md](CHANGELOG.md).
```

### `## Licença`

```markdown
## Licença

MIT — veja [LICENSE](LICENSE).
```

---

## Pacotes em Conformidade

| Pacote | Tipo | Idioma | Badges |
|---|---|---|---|
| `bcb-sgs-fetcher` | Data Package | PT | ✓ |
| `bcb-sgs-sql` | Motor ETL | PT | ✓ |
| `comex-fetcher` | Data Package | PT | ✓ |
| `datasus-fetcher` | Data Package | PT | ✓ |
| `inmet-fetcher` | Data Package | PT | ✓ |
| `pdet-fetcher` | Data Package | PT | ✓ |
| `quantilica-catalog` | Infraestrutura | PT | ✓ |
| `quantilica-cli` | CLI | PT | ✓ |
| `quantilica-core` | Infraestrutura | PT | ✓ |
| `quantilica-analytics` | Infraestrutura | PT | ✓ |
| `rtn-fetcher` | Data Package | PT | ✓ |
| `sidra-fetcher` | Client Library | PT | ✓ |
| `sidra-pipelines` | Catálogo ETL | PT | ✓ |
| `sidra-sql` | Motor ETL | PT | ✓ |
| `tesouro-direto-fetcher` | Data Package | PT | ✓ |

---

*Atualizado em: 2 de junho de 2026*
