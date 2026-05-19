---
title: quantilica-cli
description: CLI unificada do Ecossistema Quantilica — descobre e despacha para fetchers instalados via entry points, sem dependência direta.
---

# `quantilica-cli`

CLI unificada que serve como ponto de entrada único para todos os fetchers do Ecossistema Quantilica. Descobre fetchers instalados via entry point `quantilica.fetchers` e os monta como subcomandos sob `quantilica fetch <fonte>`. Não tem dependência direta de nenhum fetcher — você instala apenas os pacotes que vai usar.

A arquitetura híbrida (argparse no fetcher + Typer no plugin) está descrita em detalhes em [Arquitetura de CLI](../concepts/cli.md). Esta página foca em **como usar** o `quantilica-cli` no dia-a-dia.

## Instalação

```bash
uv add "quantilica-cli @ git+https://github.com/Quantilica/quantilica-cli.git"
```

Em seguida, instale os fetchers que quiser usar:

```bash
uv add "comex-fetcher @ git+https://github.com/Quantilica/comex-fetcher.git"
uv add "sidra-fetcher @ git+https://github.com/Quantilica/sidra-fetcher.git"
# ...
```

O `quantilica-cli` detecta automaticamente cada fetcher instalado.

## Uso

### Listar fontes disponíveis

```bash
quantilica list-sources
```

Imprime uma tabela com todos os fetchers descobertos via entry points, no formato `quantilica fetch <nome>`. Se nada estiver instalado, sugere instalar um fetcher.

### Executar um fetcher

```bash
quantilica fetch <fonte> [opções...]
```

Cada `<fonte>` corresponde ao nome do entry point declarado pelo fetcher (ex.: `comex`, `sidra`, `datasus`, `bcb-sgs`, `td`, `rtn`, `pdet`, `inmet`). As opções e subcomandos disponíveis são definidos pelo próprio plugin Typer do fetcher — use `quantilica fetch <fonte> --help` para vê-las.

Exemplos:

```bash
quantilica fetch comex --help
quantilica fetch comex sync 2023
quantilica fetch sidra info 1737
quantilica fetch bcb-sgs series sync 432
```

### Versão

```bash
quantilica --version
quantilica -V
```

## Como um fetcher é descoberto

Cada fetcher do ecossistema registra seu plugin Typer no `pyproject.toml`:

```toml
[project.entry-points."quantilica.fetchers"]
comex = "comex_fetcher.plugin:app"
```

Na inicialização, `quantilica-cli` itera os entry points do grupo `quantilica.fetchers`, importa o `typer.Typer` exportado por cada um e o monta sob `quantilica fetch <nome>`. Falhas de carga são reportadas como aviso (não derrubam a CLI).

Para registrar um novo fetcher como plugin:

1. Crie `src/<nome>_fetcher/plugin.py` com um objeto `app: typer.Typer`.
2. Declare o entry point no `pyproject.toml` do pacote.
3. Reinstale (`uv pip install -e .`) — o plugin aparece automaticamente no próximo `quantilica list-sources`.

A diretriz é que `typer` e `rich` **não** apareçam em `[project].dependencies` do fetcher — são fornecidas pelo host `quantilica-cli`. Veja [Arquitetura de CLI](../concepts/cli.md) para a justificativa.

## Saiba mais

- [Arquitetura de CLI](../concepts/cli.md) — racional da CLI híbrida e estado de padronização de cada fetcher
- [Arquitetura do Ecossistema](../concepts/arquitetura.md) — como `quantilica-cli` se encaixa no quadro geral
