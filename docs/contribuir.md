---
title: Contribuir com a Quantilica
description: Como reportar bugs, sugerir novas fontes, enviar PRs, ou propor receitas para o Cookbook. Padrões técnicos e editoriais do ecossistema.
---

# Contribuir

Quantilica é um ecossistema aberto. Bugs em fetcher, novas fontes de dados, receitas do Cookbook, correções de doc — tudo é bem-vindo.

## Os três caminhos mais comuns

### 1. Bug em um fetcher (governo mudou o endpoint)

Sites governamentais mudam com frequência. Se um fetcher parou de funcionar:

1. **Abra issue no repositório específico**, não no repositório de docs.
2. Use o template **Bug Report**.
3. Inclua: a URL/comando que falhou, mensagem de erro completa, e — se possível — o log do `quantilica-core`.
4. Confirme antes que a fonte oficial não esteja fora do ar (`gov.br` cai com regularidade).

### 2. Sugerir uma nova fonte de dados

Quer ver `pnad-covid-fetcher` ou `siscomex-servicos-fetcher`?

1. Abra issue em [github.com/Quantilica/.github/issues](https://github.com/Quantilica/.github/issues).
2. Use o template **Feature Request / Nova Fonte**.
3. Descreva: URL oficial, formato dos dados (CSV, API, FTP, Excel), periodicidade de atualização, e por que vale o esforço.

### 3. Receita nova para o Cookbook

Receitas do Cookbook são o melhor jeito de contribuir sem mexer em código de coletor.

1. Fork do repositório de docs.
2. Crie um arquivo em `docs/cookbook/<slug>.md` seguindo a estrutura das receitas existentes (front-matter, "O que você vai produzir", "Setup", "A receita", "Pegadinhas", "Variações").
3. Inclua código que **roda** — não pseudocódigo.
4. Adicione a receita ao índice em `docs/cookbook/index.md`.
5. Abra PR.

## Padrões técnicos (para PRs em código)

Todos os repositórios da Quantilica seguem o mesmo padrão. Consulte o [`ARCHITECTURE.md`](https://github.com/Quantilica/.github/blob/main/ARCHITECTURE.md) para o racional completo.

| Item | Regra |
|---|---|
| Linguagem | Python 3.12+ |
| Ambiente | `uv` para deps e venv |
| Build | `hatchling` |
| Lint/format | `ruff` |
| Testes | `pytest`, cobertura mínima 80% em código novo |
| Fundação | Coletores devem usar [`quantilica-core`](fundacoes/quantilica-core.md) |
| Nomenclatura | Novos coletores seguem `<fonte>-fetcher` |
| Proveniência | Todo artefato baixado gera um `.manifest.json` |
| Documentação | READMEs seguem o template em [`DOCUMENTATION.md`](https://github.com/Quantilica/.github/blob/main/DOCUMENTATION.md) |

## Workflow de PR

```bash
git clone https://github.com/Quantilica/<repo>.git
cd <repo>
uv sync --dev
git checkout -b feat/descricao-curta

# implemente

uv run ruff check .
uv run ruff format .
uv run pytest

git push -u origin feat/descricao-curta
```

- Abra o PR como **Draft** enquanto trabalha.
- Marque como **Ready for Review** com descrição clara do *quê* mudou e *por quê*.
- PRs são mergeados via **squash merge** para manter histórico linear.

## Padrões editoriais (para PRs em docs)

- **Idioma:** prosa em português brasileiro. Identificadores, flags de CLI, nomes de função permanecem em inglês.
- **Sem emoji decorativo** em títulos ou prosa. Tabelas comparativas podem usar onde necessário para clareza.
- **Front-matter obrigatório** em toda página nova (`title` + `description` — alimentam SEO e Open Graph).
- **Estilo:** técnico, concreto, direto. Sem hype, sem "revolucionário". Conte o que dói e mostre como a ferramenta resolve.

## Versionamento

Todos os pacotes seguem **SemVer**:

- **PATCH** — fix de bug, atualização de URL governamental.
- **MINOR** — feature compatível.
- **MAJOR** — quebra de API.

Releases saem sem cadência fixa — quando funcionalidade está pronta e testada. O único pacote no PyPI é `datasus-fetcher`; os demais são instalados via `git+https`.

## Governança

A Quantilica opera sob modelo BDFL — veja [`GOVERNANCE.md`](https://github.com/Quantilica/.github/blob/main/GOVERNANCE.md) para o detalhe. Conforme o projeto crescer em contribuidores, a intenção é migrar para governança comunitária com comitê técnico.

## Licenças

- Todos os pacotes: **MIT**.

Ao contribuir, você concorda em licenciar seu código sob a licença do pacote em questão.

---

Dúvidas? Abra issue em [github.com/Quantilica/.github](https://github.com/Quantilica/.github/issues).
