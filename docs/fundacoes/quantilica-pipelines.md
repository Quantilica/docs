---
title: quantilica-pipelines — Catálogo unificado de pipelines ETL declarativos
description: Catálogo declarativo unificado de pipelines ETL e modelos analíticos SQL para o motor quantilica-sql, organizado em macro, setorial, IBGE e cross-domain.
---

# quantilica-pipelines

**Catálogo unificado de pipelines ETL e transformações analíticas em SQL para o motor [`quantilica-sql`](quantilica-sql.md).**

## Resumo

O `quantilica-pipelines` é um repositório Git de definições declarativas: cada pipeline é um diretório com um `fetch.toml` (o que buscar), um `transform.toml` (quais tabelas e views analíticas criar) e um ou mais arquivos `.sql` com a transformação em si. Não há código Python — o catálogo não é um pacote instalável, e sim um *plugin* que o motor clona via Git e executa.

O catálogo consolida em uma única árvore os pipelines que antes eram distribuídos em dois catálogos separados — o [sidra-pipelines](../fontes/ibge/sidra-pipelines.md), de pesquisas agregadas do IBGE, e o [bcb-sgs-pipelines](../fontes/bcb/bcb-sgs-pipelines.md), de séries temporais do BCB SGS — e acrescenta o domínio `cross/`, com modelos que cruzam indicadores de múltiplos domínios e schemas.

```text
quantilica-pipelines/
├── macro/       # indicadores macroeconômicos do BCB SGS (juros, câmbio, atividade...)
├── setorial/    # dados setoriais do BCB SGS (energia, petróleo, BNDES, álcool)
├── ibge/        # pesquisas estruturais e agregadas do IBGE (SIDRA)
└── cross/       # modelos cruzando múltiplos domínios e schemas
```

!!! warning "Pegadinhas do catálogo e das fontes"

    - **`run` não busca dados.** `quantilica sql run` apenas materializa a camada analítica a partir do que já está no PostgreSQL. A carga bruta é um passo anterior, com `quantilica sql load` (veja [Executando](#executando)).
    - **Não é um pacote Python.** O repositório não tem `pyproject.toml` — não existe `quantilica install pipelines` nem `uv add quantilica-pipelines`. O catálogo é instalado como plugin do motor (abaixo).
    - **Identificadores legados não resolvem mais.** O `manifest.toml` unificado registra ids com prefixo de domínio (`macro_juros`, `ibge_precos`); `snipc` ou `precos` puros não são ids válidos. Use a forma por caminho: `quantilica sql run ibge/precos/snipc`.
    - **Modelos `cross/` leem a camada `analytics`.** O `cross/macro_trabalho` seleciona de `analytics.precos`, `analytics.juros` e `analytics.pnadcm_ocupada` — rode os pipelines de origem antes do modelo cruzado.
    - **Seleção por `themes` depende de metadados.** Um `[[series]]` com `themes` (ex.: `macro/juros`) filtra a tabela `series_metadata` no SQL. Rode antes um pipeline por `ids` (ex.: `macro/bcb_precos`) para popular o catálogo de metadados.

## Instalação

### 1. Instalar o motor `quantilica-sql`

```bash
# Via CLI unificada (recomendado)
quantilica install sql

# Ou como biblioteca no seu projeto
uv add quantilica-sql --index https://index.quantilica.com/simple/
```

**Requisitos:** Python 3.12+ e um PostgreSQL acessível.

### 2. Configurar a conexão PostgreSQL

O motor lê a string de conexão da variável de ambiente `DATABASE_URL`:

```bash
export DATABASE_URL=postgresql://postgres:<senha>@localhost:5432/dados
```

Sem a variável, o default é `postgresql://postgres@localhost:5432/dados`. O schema analítico de destino padrão é `analytics` (mude com `QUANTILICA_ANALYTICS_SCHEMA` ou com a flag `--target-schema` do `run`).

### 3. Instalar o catálogo como plugin

```bash
quantilica sql plugin install <url-do-repositorio> --alias std
```

Substitua `<url-do-repositorio>` pelo endereço Git do catálogo de pipelines. A flag `--alias` é opcional: sem ela, o nome do catálogo deriva da própria URL. Reexecutar o mesmo comando atualiza o catálogo (o repositório é clonado novamente sob o mesmo alias).

Gerencie os catálogos instalados com:

```bash
quantilica sql plugin list     # lista os catálogos instalados
quantilica sql plugin remove std  # remove o catálogo instalado sob o alias
```

!!! note "O alias não participa do identificador"
    O `--alias std` é apenas o nome local do catálogo, usado por `plugin list` e `plugin remove`. Os pipelines são endereçados pelo caminho dentro do catálogo — `quantilica sql run macro/juros` funciona com qualquer alias.

## Anatomia de um pipeline

Cada pipeline é um diretório com três peças. Na execução, o motor valida os TOMLs, infere o schema de origem a partir do `fetch.toml`, coloca-o no `search_path` e materializa cada entrada `[[table]]` numa transação própria.

```text
macro/juros/
├── fetch.toml      # o que buscar (séries SGS 432, 11, 12, 226)
├── transform.toml  # materializar analytics.juros
└── juros.sql       # o SELECT da transformação
```

### fetch.toml — o que buscar

Há três formas, uma por tipo de fonte.

**Séries BCB SGS** — blocos `[[series]]`, selecionadas por `ids` (sempre válido) ou por `themes`/`frequency` (dependem do catálogo de metadados carregado):

```toml
# macro/bcb_precos/fetch.toml
[[series]]
ids = [433, 13522, 188, 189, 7478]

[[series]]
themes = ["Preços"]
frequency = "M"
```

**Tabelas SIDRA** — blocos `[[tabelas]]`, com o id da tabela, variáveis, níveis territoriais e classificações:

```toml
# ibge/precos/snipc/fetch.toml (trecho)
# Tabela 1419 - IPCA - Variação e peso mensal (de janeiro/2012 até dezembro/2019)
[[tabelas]]
tabela_sidra    = "1419"
variables       = ["63", "66"]
territories     = {1 = [], 6 = [], 7 = []}
classifications = {315 = []}
```

**Modelos cross-domain** — bloco `[pipeline]`, que apenas declara os domínios de origem (os dados já devem existir na camada analítica):

```toml
# cross/macro_trabalho/fetch.toml
[pipeline]
name = "macro_trabalho"
domains = ["bcb_sgs", "ibge_sidra"]
description = "Modelo cruzado entre política monetária (SELIC), inflação (IPCA) e mercado de trabalho (PNAD Contínua)"
```

### transform.toml — o que materializar

Cada entrada `[[table]]` declara uma tabela ou view de saída. Um pipeline pode declarar várias — o `snipc` materializa sete:

```toml
# macro/juros/transform.toml
[[table]]
name        = "juros"
schema      = "analytics"
strategy    = "replace"
sql         = "juros.sql"
description = "Séries de taxas de juros do mercado financeiro filtradas por tema"
primary_key = ["date", "date_end", "taxa"]
```

| Chave | Obrigatória | Papel |
|---|---|---|
| `name` | sim | Nome da tabela/view de saída |
| `schema` | sim | Schema de destino (`--target-schema` sobrescreve) |
| `strategy` | sim | `replace` ou `view` |
| `sql` | sim | Arquivo com o SELECT (relativo ao diretório do pipeline) |
| `primary_key` | não | Colunas da PK criada na tabela (ignorada em views) |
| `indexes` | não | Índices adicionais (`name`, `columns`, `unique`) |
| `description` | não | Documentação da tabela |

- **`replace`** executa `DROP TABLE IF EXISTS` + `CREATE TABLE ... AS SELECT` e depois cria a PK e os índices declarados.
- **`view`** executa `DROP VIEW IF EXISTS ... CASCADE` + `CREATE VIEW ... AS SELECT`.

### Arquivos .sql — a transformação

No lado BCB, a saída costuma ser longa — uma linha por série e data:

```sql
-- macro/juros/juros.sql (trecho)
SELECT
    sd.date,
    COALESCE(sd.date_end, sd.date) AS date_end,
    CASE sd.series_id
        WHEN 432 THEN 'SELIC-META'
        WHEN 11 THEN 'SELIC-OVER'
        WHEN 12 THEN 'CDI'
        WHEN 226 THEN 'TR'
        ELSE sm.name
    END AS taxa,
    sm.name AS nome_serie,
    sm.unit AS unidade,
    sm.frequency AS frequencia,
    sd.value::double precision AS valor
FROM series_data sd
    INNER JOIN series_metadata sm ON sd.series_id = sm.series_id
WHERE sm.theme_hierarchy @> ARRAY['Mercados financeiros e de capitais', 'Indicadores do mercado financeiro', 'Taxas de juros']
    AND sd.ativo = TRUE
```

No lado IBGE, os pipelines de inflação pivotam as variáveis em colunas (formato *wide*): no `snipc`, "Variação mensal" e "Peso mensal" viram as colunas `variacao` e `peso`:

```sql
-- ibge/precos/snipc/ipca.sql (trecho)
SUM(CASE WHEN VARIAVEL = 'IPCA - Peso mensal' THEN VALOR END)      AS PESO,
SUM(CASE WHEN VARIAVEL = 'IPCA - Variação mensal' THEN VALOR END)  AS VARIACAO
```

Entre os pipelines BCB, `credito` e `monetario` são as exceções ao formato longo: pivotam uma coluna por série (`credito_saldo_mi`, `m1_mi`, ...).

!!! note "Criando pipelines novos"
    O motor gera o esqueleto de um pipeline ou de um catálogo completo (com `manifest.toml` e `README.md`) para você preencher:

    ```bash
    quantilica sql scaffold meu_pipeline --type ibge
    quantilica sql scaffold meu_catalogo --catalog --description "Meu catálogo"
    ```

    Publique o catálogo em um repositório Git e instale-o com `quantilica sql plugin install <url-do-repositorio>`.

## Catálogo

Contagem por domínio realizada em 25 de outubro de 2026: **34 pipelines**.

### macro/ — 9 pipelines (BCB SGS)

| Pipeline | Conteúdo | Saída |
|---|---|---|
| `macro/atividade` | IBC-Br nacional e regional | `analytics.atividade` |
| `macro/bcb_precos` | Índices de preços BCB (IPCA, IPCA-12M, INPC, IGP-M, IPCA-15) | `analytics.precos` |
| `macro/cambio` | Taxas de câmbio diárias (USD, EUR, etc.) | `analytics.cambio` |
| `macro/commodities` | IC-Br (agropecuária, energia, metal e total) | `analytics.commodities` |
| `macro/credito` | Operações de crédito (saldo, inadimplência, spread) | `analytics.credito` |
| `macro/juros` | Taxas de juros (SELIC meta/over, CDI, TR) | `analytics.juros` |
| `macro/monetario` | Meios de pagamento M1, M2, M3, M4 | `analytics.monetario` |
| `macro/movimento_cambio_contratado` | Fluxo cambial contratado | `analytics.movimento_cambio_contratado` |
| `macro/pib_mensal` | PIB mensal acumulado em 12 meses (R$ milhões e US$ milhões) | `analytics.pib_mensal` |

### setorial/ — 4 pipelines (BCB SGS)

| Pipeline | Conteúdo | Saída |
|---|---|---|
| `setorial/alcool_carburante` | Consumo de álcool hidratado, anidro e total | `analytics.alcool_carburante` |
| `setorial/derivados_petroleo` | Produção e consumo de derivados de petróleo | `analytics.derivados_petroleo` |
| `setorial/desembolsos_bndes` | Desembolsos do BNDES por setor | `analytics.desembolsos_bndes` |
| `setorial/energia_eletrica` | Consumo e geração de energia elétrica | `analytics.energia_eletrica` |

### ibge/ — 20 pipelines em 8 temas (SIDRA)

| Tema | Pipelines |
|---|---|
| `ibge/agropecuaria` (9) | `abate`, `couro`, `estoques`, `leite`, `lspa`, `pam`, `pevs`, `pog`, `ppm` |
| `ibge/contas_nacionais` (3) | `anual`, `pib_municipal`, `trimestral` |
| `ibge/industria` (1) | `pim-pf` |
| `ibge/pmc` (1) | Pesquisa Mensal do Comércio |
| `ibge/pms` (1) | Pesquisa Mensal de Serviços |
| `ibge/populacao` (1) | Censo, contagem e estimativas de população |
| `ibge/precos` (3) | `ipp`, `sinapi`, `snipc` |
| `ibge/trabalho` (1) | `pnadcm` (PNAD Contínua mensal) |

Pipelines com múltiplas saídas: `snipc` materializa sete tabelas (`inpc`, `ipca`, `ipca15`, `inflacao`, `inflacao_numero_indice`, `inflacao_difusao`, `inflacao_hierarquia_subitem`) e `pnadcm` cinco (`pnadcm_populacao`, `pnadcm_pia`, `pnadcm_ocupada`, `pnadcm_rendimento`, `pnadcm_massa_rendimento`).

### cross/ — 1 modelo cross-domain

| Modelo | Lê de | Saída |
|---|---|---|
| `cross/macro_trabalho` | `analytics.precos`, `analytics.juros`, `analytics.pnadcm_ocupada` | view `analytics.macro_trabalho_indicadores` |

### manifest.toml — o registro do catálogo

A raiz do repositório traz um `manifest.toml` com os metadados do catálogo (`[catalog]`) e o registro de pipelines (`[pipelines.<id>]`), cada um com `theme`, `path` e `description`. O motor aceita tanto o caminho (`quantilica sql run macro/juros`) quanto o id registrado (`quantilica sql run macro_juros`) — mas nem todo pipeline do catálogo está registrado no manifesto, então a forma por caminho é a mais confiável.

## Executando

`quantilica sql run` materializa a camada analítica; a carga bruta é um passo anterior, feita com `quantilica sql load` apontando para os dados coletados. Um fluxo completo:

```bash
# 1. Carregar os dados brutos no PostgreSQL (domínios sidra e bcb-sgs)
quantilica sql load sidra --source-path <diretorio-de-dados> --all
quantilica sql load bcb-sgs --source-path <diretorio-de-dados> --all

# 2. Materializar um pipeline
quantilica sql run ibge/precos/snipc
# Pipeline 'ibge/precos/snipc' executado com sucesso!
# Materializados: analytics.inpc, analytics.ipca, analytics.ipca15, ...

# 3. Consultar como qualquer tabela SQL
SELECT * FROM analytics.ipca WHERE periodo >= '2024-01-01' ORDER BY periodo DESC;
```

O schema de origem é inferido do `fetch.toml` (`[[tabelas]]` → `ibge_sidra`; `[[series]]` → `bcb_sgs`) e colocado no `search_path`; os modelos cross-domain qualificam os schemas explicitamente no SQL.

O identificador aceita id, nome ou caminho:

```bash
quantilica sql run macro/juros        # caminho dentro do catálogo
quantilica sql run macro_juros       # id registrado no manifest.toml
quantilica sql run ./meu_pipeline    # diretório local com transform.toml
```

Subdiretórios inteiros também podem ser executados — os pipelines filhos rodam primeiro:

```bash
quantilica sql run ibge/precos        # roda ipp, sinapi e snipc
quantilica sql run macro              # roda os 9 pipelines de macro
```

Flags do `run`:

```bash
--raw-schema <schema>     # sobrescreve o schema de origem (default: inferido do fetch.toml)
--target-schema <schema>  # sobrescreve o schema de destino (default: analytics)
```

Se o identificador não for encontrado, o comando termina com erro e código 1: `Pipeline '<nome>' não encontrado. Verifique o nome ou instale o plugin correspondente.`

!!! note "Primeiras execuções e modelos cross"

    - Pipelines do IBGE podem ter milhões de linhas na primeira execução (Censo, PAM municipal, PPM rebanhos). Rode um pipeline por vez e confira o resultado antes de seguir.
    - Rode as origens antes do modelo cruzado: `cross/macro_trabalho` depende de `macro/bcb_precos`, `macro/juros` e `ibge/trabalho/pnadcm` já materializados.

## Migrando dos catálogos legados

Os pipelines dos dois catálogos anteriores foram preservados, reorganizados sob o domínio. A sintaxe muda de `<motor-legado> run std <id>` para `quantilica sql run <dominio>/<caminho>`:

```bash
# Antes (catálogos legados)          # Agora (catálogo unificado)
sidra-sql run std snipc              quantilica sql run ibge/precos/snipc
bcb-sgs-sql run std juros            quantilica sql run macro/juros
```

### De `bcb-sgs-pipelines` (13 pipelines)

Os 13 pipelines mantêm os nomes: 9 foram para `macro/` e 4 para `setorial/`. A única renomeação de caminho é `precos` → `macro/bcb_precos` (para não colidir com `ibge/precos`):

| Id legado | Novo identificador |
|---|---|
| `precos` | `macro/bcb_precos` |
| `juros` | `macro/juros` |
| `cambio` | `macro/cambio` |
| `atividade` | `macro/atividade` |
| `credito` | `macro/credito` |
| `monetario` | `macro/monetario` |
| `commodities` | `macro/commodities` |
| `movimento_cambio_contratado` | `macro/movimento_cambio_contratado` |
| `pib_mensal` | `macro/pib_mensal` |
| `alcool_carburante` | `setorial/alcool_carburante` |
| `derivados_petroleo` | `setorial/derivados_petroleo` |
| `desembolsos_bndes` | `setorial/desembolsos_bndes` |
| `energia_eletrica` | `setorial/energia_eletrica` |

### De `sidra-pipelines` (20 pipelines)

O caminho relativo do catálogo legado é preservado sob `ibge/` — basta prefixar: `sidra-sql run std <id>` vira `quantilica sql run ibge/<caminho>`:

| Id legado | Novo identificador |
|---|---|
| `pib_municipal` | `ibge/contas_nacionais/pib_municipal` |
| `contas_nacionais_anual` | `ibge/contas_nacionais/anual` |
| `contas_nacionais_trimestral` | `ibge/contas_nacionais/trimestral` |
| `snipc` | `ibge/precos/snipc` |
| `ipp` | `ibge/precos/ipp` |
| `sinapi` | `ibge/precos/sinapi` |
| `pim_pf` | `ibge/industria/pim-pf` |
| `pmc` | `ibge/pmc` |
| `pms` | `ibge/pms` |
| `populacao` | `ibge/populacao` |
| `pnadcm` | `ibge/trabalho/pnadcm` |
| `pam` | `ibge/agropecuaria/pam` |
| `ppm` | `ibge/agropecuaria/ppm` |
| `pevs` | `ibge/agropecuaria/pevs` |
| `lspa` | `ibge/agropecuaria/lspa` |
| `abate` | `ibge/agropecuaria/abate` |
| `leite` | `ibge/agropecuaria/leite` |
| `couro` | `ibge/agropecuaria/couro` |
| `pog` | `ibge/agropecuaria/pog` |
| `estoques` | `ibge/agropecuaria/estoques` |

### O que mais muda

- **Um único motor.** `sidra-sql` e `bcb-sgs-sql` dão lugar ao `quantilica sql` — um motor unificado de ingestão e pipelines analíticos no PostgreSQL.
- **Configuração de banco.** Os motores legados liam `config.ini`; o `quantilica-sql` lê `DATABASE_URL` (variável de ambiente).
- **Atualização do catálogo.** No lugar de `plugin update`, reexecute `quantilica sql plugin install <url-do-repositorio> --alias std` — o comando instala ou atualiza.

## Saiba mais

- **[quantilica-sql](quantilica-sql.md)** — o motor que carrega os dados brutos e executa este catálogo
- **[quantilica-cli](quantilica-cli.md)** — a CLI unificada que hospeda o comando `quantilica sql`
- **[sidra-pipelines](../fontes/ibge/sidra-pipelines.md)** — catálogo legado do IBGE, consolidado neste catálogo
- **[bcb-sgs-pipelines](../fontes/bcb/bcb-sgs-pipelines.md)** — catálogo legado do BCB SGS, consolidado neste catálogo
- **[SIDRA](https://sidra.ibge.gov.br/)** — banco de dados agregados do IBGE
- **[BCB SGS](https://www3.bcb.gov.br/sgspub/)** — Sistema Gerenciador de Séries Temporais do Banco Central
