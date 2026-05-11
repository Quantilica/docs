# Quantilica — Documentação

Portal público da Quantilica (`docs.quantilica.io`), construído com [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

## Desenvolvimento local

```bash
uv sync
uv run mkdocs serve
```

Site disponível em `http://127.0.0.1:8000`.

## Estrutura

```
docs/
├── docs/                  # conteúdo (Markdown)
│   ├── index.md           # hero e narrativa de abertura
│   ├── quickstart.md      # 5 minutos para o primeiro dado
│   ├── concepts/          # arquitetura, princípios, padrões
│   ├── fundacoes/         # quantilica-core, quantilica-io
│   ├── ibge/ tesouro/ ... # domínios e ferramentas
│   └── cookbook/          # receitas multi-fonte
├── overrides/             # extensões do tema Material
│   └── partials/
│       └── extrahead.html # meta tags Open Graph / Twitter
└── mkdocs.yml
```

## Open Graph e cards sociais

A configuração padrão emite tags `og:*` e `twitter:*` básicas via `overrides/partials/extrahead.html`, usando a `description` do front-matter de cada página e a imagem em `docs/assets/og-image.png`.

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
- Veja [`.github/DOCUMENTATION.md`](https://github.com/Quantilica/.github/blob/main/DOCUMENTATION.md) para o padrão de READMEs dos repositórios.
