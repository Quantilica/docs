---
title: sidra-fetcher — Cliente Python para a API SIDRA do IBGE
description: SDK Python para extrair dados e metadados da API IBGE/SIDRA. Cliente sync e async, parsing de períodos, construtor de URL tipado, retry resiliente.
---

# Instituto Brasileiro de Geografia e Estatística (SIDRA)

Cliente Python para a API SIDRA do IBGE — com suporte para requisições assíncronas (alta performance), construtores declarativos de URLs e sistema anti-falha de conexão.

!!! warning "Pegadinhas da fonte oficial"

    - **URLs indecifráveis.** O SIDRA usa pares de identificador/valor (`/t/1620/n1/all/v/116/p/all/d/m`). Isso é confuso e quebra scripts com facilidade. Use nossa abstração `Parametro` ao invés de concatenar *strings* manualmente.
    - **O produto cartesiano fatal.** Uma tabela com 3 classificações cruzadas vira milhares de linhas. Se você não especificar o filtro na URL, a API retornará cruzamentos absurdos e estourará a RAM.
    - **Limitação invisível por volume.** O IBGE trunca silenciosamente respostas de tabelas muito grandes (como o PIB Municipal ou o Censo) resultando em um erro genérico `503`. O fetcher possui iteração segura fragmentando chamadas mês a mês se necessário.
    - **Rate Limit Oculto.** Evite horários comerciais. Em scripts massivos, utilize o cliente `AsyncSidraClient` travado com um `asyncio.Semaphore` para não ser banido temporariamente pelo governo.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install sidra

# Ou como biblioteca no seu projeto
uv add sidra-fetcher --index https://index.quantilica.com/simple/
```

## CLI Oficial (Ambiente Unificado)

A forma recomendada de exploração via terminal é através da CLI central, que permite varrer o vasto catálogo do IBGE para descobrir o que você precisa:

```bash
# Listar todas as pesquisas (Censo, IPCA, PNAD)
quantilica sidra list

# Descobrir metadados detalhados de uma tabela específica (ex: IPCA 1620)
quantilica sidra info 1620

# Verificar todos os períodos suportados
quantilica sidra periods 1620

# Verificar o que mudou sem baixar (plano de freshness por nível)
quantilica sidra check 1620 -o ./data

# Fazer o dump completo respeitando limites da API
quantilica sidra sync 1620 -o ./data
```

---

## Cookbook Analítico: IBGE com Polars

O gargalo de uso do SIDRA é criar a sintaxe da URL sem cometer erros. Através da biblioteca Python, nós abstraímos isso com a classe `Parametro`.

```python
import polars as pl
from sidra_fetcher.fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao

# 1. Constrói declarativamente a requisição sem sujar as mãos com strings
param = Parametro(
    agregado="1620",              # Tabela do PIB
    territorios={"1": ["all"]},   # Nível Nacional (1)
    variaveis=["116"],            # Variável PIB
    periodos=[],                  # Todos os trimestres
    classificacoes={},            # Sem quebras adicionais
    formato=Formato.A,
    decimais={"": Precisao.M},
)

# 2. Executa a requisição com proteção de Timeout (60s)
with SidraClient(timeout=60) as client:
    dados_json = client.get(param.url())

# 3. Transforma o dicionário bruto em um LazyFrame analítico
df_pib = (
    pl.DataFrame(dados_json[1:]) # A linha 0 sempre é metadados no SIDRA
    .select(
        pl.col("D3C").alias("Trimestre"),
        pl.col("V").cast(pl.Float64, strict=False).alias("PIB_Trilhoes")
    )
    .drop_nulls()
)

print(df_pib.tail())
```

---

## Extração Assíncrona (Alta Performance)

Para coleta de metadados em larga escala ou extração de décadas de Censo Municipal, o cliente `async` da Quantilica pulveriza o gargalo de I/O de rede fazendo downloads dezenas de vezes mais rápidos:

```python
import asyncio
from sidra_fetcher.fetcher import AsyncSidraClient

async def coleta_macro():
    """Busca o IPCA e o PIB concorrentemente."""
    async with AsyncSidraClient(timeout=60) as client:
        # Dispara todas as requisições simultaneamente
        ipca, pib = await asyncio.gather(
            client.get_agregado(7060),
            client.get_agregado(1620)
        )
    return ipca, pib

ipca_meta, pib_meta = asyncio.run(coleta_macro())
print(f"PIB suporta {len(pib_meta.periodos)} períodos históricos.")
```

## Engenharia Reversa Automática (Cheat Code)

Achou um gráfico legal no site do SIDRA e quer automatizar a extração no Python, mas não quer escrever o `Parametro` na mão?

Basta copiar a URL do portal web do governo e jogar no decodificador:

```python
from sidra_fetcher.sidra import parameter_from_url

url = "https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2265/p/all/d/m"
param = parameter_from_url(url)

print(param.agregado)   # "1737"
print(param.variaveis)  # ["2265"]
```

## Saiba Mais

- **[sidra-sql](sidra-sql.md)** — Motor de data warehousing e ETL que consome o `sidra-fetcher`.
- **[Arquitetura do Ecossistema](../concepts/arquitetura.md)** — Como as bibliotecas se conectam.
