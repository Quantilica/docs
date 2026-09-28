# Quantilica — Documentação

Portal público da Quantilica (`docs.quantilica.com`), construído com [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

## Desenvolvimento local

```bash
uv sync
uv run mkdocs serve
```

Site disponível em `https://docs.quantilica.com/`.

## Estrutura

```
docs/
├── docs/                  # conteúdo (Markdown)
│   ├── index.md           # hero e narrativa de abertura
│   ├── quickstart.md      # 5 minutos para o primeiro dado
│   ├── concepts/          # arquitetura, princípios, padrões
│   ├── fundacoes/         # núcleo, camada analítica, CLI, catálogo
│   ├── ibge/ tesouro/ ... # domínios e ferramentas
│   └── cookbook/          # receitas multi-fonte
├── overrides/             # extensões do tema Material
│   ├── main.html          # meta tags Open Graph / Twitter
│   └── partials/integrations/analytics/custom.html # analytics (consent-aware)
└── mkdocs.yml
```

## O que nunca entra neste site (privacidade)

Este repositório é público. Documenta apenas contratos públicos: instalação,
CLI, schemas, pipelines declarativos e conceitos. Nunca publique aqui
planejamento interno, conhecimento operacional interno, autenticação ou
documentos internos de aplicações, infraestrutura e rotinas de produção,
credenciais, tokens ou URLs internas. Em exemplos de configuração, use sempre
placeholders (`<senha>`) em vez de valores reais.

## Open Graph e cards sociais

A configuração padrão emite tags `og:*` e `twitter:*` básicas via `overrides/main.html`, usando a `description` do front-matter de cada página e a imagem em `docs/assets/og-image.png`.

Para gerar **cards Open Graph automáticos por página** (com título, descrição e logo), ative o plugin `social` do Material:

```bash
uv add "mkdocs-material[imaging]"
```

Depois descomente o bloco `- social:` em `mkdocs.yml`. Esse plugin requer Cairo e Pango no sistema (no Windows, geralmente via MSYS2 ou WSL).

### `og-image.png`

Coloque em `docs/assets/og-image.png` uma imagem 1200×630 com o logo e a tagline da Quantilica. Esse é o fallback usado quando o plugin `social` não está ativo.

## Padrões editoriais

- Idioma: português brasileiro. Identificadores, flags de CLI e nomes de função permanecem em inglês.
- Sem emoji decorativo em títulos e prosa.
- Toda página nova deve ter front-matter com `title` e `description` para SEO e Open Graph.
- Veja [Padrões de Escrita](docs/normas/escrita.md) para o padrão de READMEs dos repositórios.
