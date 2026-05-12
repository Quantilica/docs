# Padrão de Documentação — Quantilica

Este documento define o padrão de README adotado por todos os repositórios da organização. Novos pacotes e contribuições devem seguir este guia.

---

## Regras Gerais

- **Idioma:** Todo o texto em prosa (descrições, títulos de seção, comentários) é escrito em **português**. Exemplos de código, flags de CLI, identificadores e nomes de funções permanecem em inglês.
- **Emoji:** Nenhum emoji decorativo em cabeçalhos ou prosa. Usar somente onde necessário para clareza técnica (ex: tabelas comparativas).
- **Instalação:** Todos os pacotes são instalados via `git+https://`, exceto `datasus-fetcher` (publicado no PyPI).

---

## Badges

Linha de badges imediatamente após o título `# `, seguindo o padrão `flat-square`:

```markdown
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square) ![Python](https://img.shields.io/badge/python-3.12+-blue.svg?style=flat-square)
```

- A versão Python deve corresponder ao `requires-python` do `pyproject.toml`.
- Licença `MIT` para todos os pacotes.
- Badge de CI apenas em pacotes com workflow de testes ativo.

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

## Licença
```

---

## Template para Aplicações Web (apps `-db`)

```markdown
# <package-name>: <descrição curta>

![License: MIT](...) ![Python](...)

<2-3 frases: o que é, qual fonte de dados, quem usa>

---

## Instalação

## Configuração

## Pipeline de Dados   ← apenas se o pacote inclui CLI de ingestão de dados

## Desenvolvimento

## Licença
```

A seção `## Configuração` deve conter uma tabela com todas as variáveis de ambiente (obrigatórias e opcionais):

```markdown
## Configuração

| Variável | Obrigatório | Descrição |
|---|---|---|
| `MYAPP_DATABASE_URI` | Sim | DSN PostgreSQL |
| `MYAPP_SECRET_KEY` | Sim | Chave de sessão Flask (mín. 32 caracteres) |
| `MYAPP_DATABASE_SCHEMA` | Não | Schema PostgreSQL (padrão: `myapp`) |
| `MYAPP_REDIS_URL` | Não | URL Redis para cache |
```

---

## Seções Obrigatórias

### `## Instalação`

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

Para extras opcionais:

```bash
pip install "<pacote>[extra] @ git+https://github.com/Quantilica/<pacote>.git"
```

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

### `## Licença`

```markdown
## Licença

MIT — veja [LICENSE](LICENSE).
```

---

## Pacotes em Conformidade

| Pacote | Tipo | Idioma | Badges |
|---|---|---|---|
| `comex-fetcher` | Data Package | PT | ✓ |
| `datasus-fetcher` | Data Package | PT | ✓ |
| `inmet-fetcher` | Data Package | PT | ✓ |
| `pdet-fetcher` | Data Package | PT | ✓ |
| `quantilica-cli` | CLI | PT | ✓ |
| `quantilica-core` | Infraestrutura | PT | ✓ |
| `quantilica-io` | Infraestrutura | PT | ✓ |
| `rtn-fetcher` | Data Package | PT | ✓ |
| `sidra-fetcher` | Client Library | PT | ✓ |
| `sidra-pipelines` | Catálogo ETL | PT | ✓ |
| `sidra-sql` | Motor ETL | PT | ✓ |
| `tesouro-direto-fetcher` | Data Package | PT | ✓ |

---

*Atualizado em: 12 de maio de 2026*
