---
title: Quickstart — Dados públicos brasileiros em 5 minutos
description: Instale uma ferramenta Quantilica, baixe um dataset real e analise. Três caminhos prontos para IBGE, Tesouro e Saúde.
---

# Comece em 5 minutos

Três caminhos prontos para baixar e analisar um dataset público real, do zero. Escolha o domínio mais próximo do seu trabalho — todos seguem o mesmo padrão.

## Pré-requisitos

- **Python 3.12+**
- **[uv](https://github.com/astral-sh/uv)** para gerenciar ambientes (recomendado).

```bash
# Cria um projeto novo
uv init quantilica-demo && cd quantilica-demo
```

Se preferir `pip` puro, substitua `uv add` por `pip install` nos comandos abaixo.

---

=== "IBGE — IPCA"

    Baixa os metadados completos do IPCA-15 (agregado 1705) e mostra a estrutura: períodos disponíveis, localidades cobertas, variáveis.

    ```bash
    uv add "sidra-fetcher @ git+https://github.com/Quantilica/sidra-fetcher.git"
    ```

    ```python
    from sidra_fetcher.fetcher import SidraClient

    with SidraClient() as client:
        agregado = client.get_agregado(1705)  # IPCA-15

        print(f"Agregado: {agregado.nome}")
        print(f"Periodicidade: {agregado.periodicidade.frequencia}")
        print(f"Períodos disponíveis: {len(agregado.periodos)}")
        print(f"Localidades cobertas: {len(agregado.localidades)}")

        ultimos = agregado.periodos[-5:]
        for p in ultimos:
            print(f"  {p.id}  ({p.data_inicio} → {p.data_fim})")
    ```

    Saída esperada: nome do agregado, frequência mensal, ~84 períodos, dezenas de localidades, e os últimos 5 períodos com data de início e fim já parseados.

    **Próximos passos:**

    - [Construa uma URL `/values` SIDRA com `Parametro`](ibge/sidra-fetcher.md)
    - [Carregue tudo em PostgreSQL com `sidra-sql`](ibge/sidra-sql.md)
    - [Use um pipeline pronto do catálogo](ibge/sidra-pipelines.md)

=== "Tesouro — Yield Curve"

    Baixa o histórico completo de taxas e preços do Tesouro Direto via API CKAN, lê com Polars e plota a yield curve por tipo de título.

    ```bash
    uv add "tesouro-direto-fetcher[analysis] @ git+https://github.com/Quantilica/tesouro-direto-fetcher.git"
    ```

    ```python
    import asyncio
    from pathlib import Path
    from tesouro_direto_fetcher import downloader, reader, plot

    dest = Path("./dados")

    asyncio.run(
        downloader.download(
            dest_dir=dest,
            dataset_id="taxas-dos-titulos-ofertados-pelo-tesouro-direto",
        )
    )

    csv = next(dest.glob("taxas-*.csv"))
    df = reader.read_prices(csv)

    chart = plot.plot_prices(df, bond_type="Tesouro Selic")
    chart.save("selic.html")
    ```

    Saída esperada: CSV baixado em `./dados/`, DataFrame com colunas tipadas, e um arquivo `selic.html` com a curva pronta para abrir no navegador.

    **Próximos passos:**

    - [Calcule retornos GIPS-compliant](tesouro/calculo-retornos.md)
    - [Combine com o RTN para a foto fiscal mensal](tesouro/rtn-fetcher.md)

=== "Saúde — DATASUS"

    Baixa os microdados do SIH-RD (Internações Hospitalares) para São Paulo nos últimos 3 anos. Sem dependências externas — `datasus-fetcher` roda em Python puro e está no PyPI.

    ```bash
    uv add datasus-fetcher
    ```

    ```bash
    datasus-fetcher data \
        --data-dir ./dados \
        sih-rd \
        --start 2022-01 \
        --end 2024-12 \
        --regions sp \
        --threads 4
    ```

    Saída esperada: dezenas de arquivos `.dbc` em `./dados/sih-rd/`, com retry automático, verificação de integridade e versionamento por data.

    Para abrir os `.dbc`, use o leitor `pyreaddbc` ou a conversão via [`quantilica-io`](fundacoes/quantilica-io.md).

    **Próximos passos:**

    - [Liste todos os 113 datasets disponíveis](saude/datasus-fetcher.md)
    - [Cruze óbitos do SIM com população do SIDRA](cookbook/index.md)

=== "Clima — INMET"

    Baixa um intervalo de anos do BDMEP em paralelo, com encoding e cabeçalhos já tratados, e exporta direto em Parquet.

    ```bash
    uv add "inmet-fetcher @ git+https://github.com/Quantilica/inmet-fetcher.git"
    ```

    ```bash
    inmet-fetcher fetch 2020:2024 --data-dir ./dados --workers 4
    inmet-fetcher read --data-dir ./dados --uf SP,RJ --output sudeste.parquet
    ```

    Saída esperada: ZIPs anuais baixados, dados unificados em `sudeste.parquet` com colunas em `snake_case`, `datetime` nativo e valores nulos limpos.

    **Próximos passos:**

    - [Filtrar por estação e período](clima/inmet-fetcher.md)
    - [Series climáticas históricas + IPCA agrícola](cookbook/index.md)

---

## O que vem junto, de graça

Toda ferramenta Quantilica entrega o mesmo conjunto de garantias — você não precisa pedir:

- **Retry automático** com backoff exponencial em qualquer erro de rede.
- **Proveniência SHA-256** em manifestos `.manifest.json` ao lado de cada arquivo baixado.
- **Saída tipada** em Parquet (via [`quantilica-io`](fundacoes/quantilica-io.md)) ou dataclasses Python.
- **Logging estruturado** consistente em toda a stack.
- **Idempotência** — rodar duas vezes não baixa duas vezes.

Esses comportamentos vêm do pacote de fundação [`quantilica-core`](fundacoes/quantilica-core.md). Você nunca precisa configurar isso à mão.

---

## Próximos passos

1. **[Princípios de Design](concepts/principios.md)** — entenda por que o sistema tem essa forma.
2. **[Cookbook](cookbook/index.md)** — receitas que combinam múltiplos domínios.
3. **[Arquitetura](concepts/arquitetura.md)** — como `-fetcher`, `-sql` e `-pipelines` se conectam.
