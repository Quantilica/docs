---
title: rtn-fetcher — Resultado do Tesouro Nacional (RTN)
description: Baixa, lê e normaliza a gigantesca planilha Excel do RTN em tabelas de formato longo com hierarquia de contas pronta para engenharia de dados.
---

# Resultado do Tesouro Nacional (RTN)

**rtn-fetcher** domina a extração dos relatórios fiscais do Governo Federal Brasileiro.

O Tesouro Nacional publica os resultados primários (receitas e despesas) em uma pasta de trabalho Excel incrivelmente complexa. Este agente automatiza o `fetch-and-normalize`: baixa a planilha da URL oficial e a lê em tabelas tipadas em formato longo, preservando a hierarquia contábil; a gravação em CSV ou Parquet fica com a API Python.

!!! warning "Pegadinhas da fonte oficial"

    - **Tabela Viva.** Os headers não estão em uma linha fixa. Cada uma das 24 abas tem cabeçalhos em linhas diferentes e células mescladas caóticas. O `rtn-fetcher` varre a planilha descobrindo o escopo dos dados dinamicamente; não tente carregar isso via `pd.read_excel(header=3)`.
    - **Hierarquia Implícita.** Um código contábil `1.2.3` na planilha não explica quem são seus pais. O fetcher reconstrói a árvore inteira gerando duas tabelas separadas: Tabela de Fatos e Tabela de Dimensão (Hierarquia de Contas).
    - **Mistura de Unidades Lógicas.** Abas `1.x` estão em milhões de Reais correntes; `2.x-A` são frações do PIB percentual; `1.2-B` deflacionadas pelo IPCA. O Data Contract tipa o período e as colunas; a conversão de valores em milhões de reais é aplicada na leitura (`convert_value`).
    - **Períodos Misturados.** Meses, trimestres e anos coabitam a mesma aba. O motor divide inteligentemente os esquemas para `year/month` ou `year/quarter`.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install rtn

# Ou como biblioteca no seu projeto
uv add rtn-fetcher --index https://index.quantilica.com/simple/
```

**Requisitos:** Python 3.12+

## CLI Oficial (Ambiente Unificado)

A forma idomática de varrer os dados fiscais é utilizando o binário host `quantilica`. Ele cuidará de acessar a API APEX do Tesouro, encontrar a URL mais recente (cujo ID muda mensalmente) e baixar a planilha. A leitura e a conversão para CSV ou Parquet ficam com a API Python (veja abaixo):

```bash
# Baixar a série do RTN (relatório mais recente publicado)
quantilica rtn sync -o ./data
```

---

## Estrutura de Extração (Abas e Dimensões)

O pacote domina as 24 abas mais cruciais de contas públicas do Excel do Tesouro Nacional:

| Aba | Descrição | Granularidade | Unidade |
|--------|-------------|--------|------|
| **1.1 a 1.6** | Séries correntes (Receitas, Despesas, Previdência) | Mensal | Milhões de R$ |
| **1.1-A a 1.5-A** | Séries a valores constantes (Deflacionadas) | Mensal | Milhões de R$ |
| **1.2-B** | Acumulado de 12-meses pelo IPCA | Mensal | Milhões de R$ |
| **2.1 a 2.5** | Resultados agregados correntes | Anual | Milhões de R$ |
| **2.1-A a 2.5-A** | Resultados versus o tamanho do país | Anual | % Fração do PIB |
| **4.1 a 4.2** | Orçamento Trimestral do Governo Central | Trimestral | Milhões de R$ |

---

## Uso via Python Puro (Engine Tbl Interna)

Para cenários sem a CLI, o fetcher tem uma classe própria e leve, a `Tbl`, para leitura em memória:

```python
from pathlib import Path
from rtn_fetcher import read_sheet, write_table_to_csv

filepath = Path("data/rtn@20241230T120000.xlsx")

# Extrai os Fatos e as Dimensões Contábeis de uma vez
fato, contas = read_sheet(filepath, "1.2")

print(f"Fatos: {fato.nrows} linhas x {fato.ncols} colunas")
print(f"Dimensão Contábil: {contas.nrows} linhas x {contas.ncols} colunas")

write_table_to_csv(fato, Path("output/rtn_1_2_data.csv"))
```

## Saiba Mais

- **[Visão Geral do Tesouro](index.md)** — Todas as ferramentas do Tesouro (Finanças)
- **[tesouro-direto-fetcher](tesouro-direto-fetcher.md)** — Microdados do Tesouro Direto e análise de portfólio
