# Quantilica — Documentação

Portal público da Quantilica (`docs.quantilica.com`), construído com [ProperDocs](https://properdocs.org/) (continuação do MkDocs 1.x) e o tema [Material](https://squidfunk.github.io/mkdocs-material/). O `mkdocs` 1.6.1 segue instalado só como dependência do tema e dos plugins; o build usa `properdocs`.

## Desenvolvimento local

```bash
uv sync
uv run properdocs serve
```

As URLs antigas (`concepts/`, `cookbook/`, `personas/` e as pastas de domínio na raiz) continuam funcionando por redirecionamento (`mkdocs-redirects`). Depois de mover uma página, adicione-a em `redirect_maps` (em `properdocs.yml`) e confira com:

```bash
uv run properdocs build -d site && uv run --with pyyaml python tools/check_redirects.py site
```

O site local sobe em `http://127.0.0.1:8000/`; a versão publicada fica em `https://docs.quantilica.com/`.

## Estrutura

```
docs/
├── docs/                  # conteúdo (Markdown)
│   ├── index.md           # hero e narrativa de abertura
│   ├── quickstart.md      # 5 minutos para o primeiro dado
│   ├── fontes/            # uma pasta por domínio (ibge, tesouro, saude, ...) e uma página por coletor
│   ├── fundacoes/         # núcleo, camada analítica, CLI, catálogo
│   ├── guias/             # perfis/ (por onde começar) e receitas/ (cruzamentos passo a passo)
│   ├── conceitos/         # arquitetura, princípios, preservação histórica, proveniência e armazenamento
│   ├── normas/            # normas de contribuição (referência)
│   └── status.md roadmap.md changelog.md
├── overrides/             # extensões do tema Material
│   ├── main.html          # meta tags Open Graph / Twitter
│   └── partials/integrations/analytics/custom.html # analytics (consent-aware)
├── tools/check_redirects.py  # confere o mapa de redirects contra o site construído
└── properdocs.yml
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

Depois descomente o bloco `- social:` em `properdocs.yml`. Esse plugin requer Cairo e Pango no sistema (no Windows, geralmente via MSYS2 ou WSL).

### `og-image.png`

Coloque em `docs/assets/og-image.png` uma imagem 1200×630 com o logo e a tagline da Quantilica. Esse é o fallback usado quando o plugin `social` não está ativo.

## Padrões editoriais

- Idioma: português brasileiro. Identificadores, flags de CLI e nomes de função permanecem em inglês.
- Sem emoji decorativo em títulos e prosa.
- Toda página nova deve ter front-matter com `title` e `description` para SEO e Open Graph.
- Veja [Padrões de Escrita](docs/normas/escrita.md) para o padrão de READMEs dos repositórios.
