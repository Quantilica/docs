# Visão Geral da Arquitetura

Como a Plataforma Brasileira de Dados Públicos é organizada e como as partes se conectam.

## Arquitetura do Sistema

```mermaid
graph TD
    Sources["Fontes de Dados Governamentais<br/>(IBGE, Tesouro, Trabalho, Comércio, Saúde)"]
    
    Sources -->|IBGE SIDRA| SF["sidra-fetcher"]
    Sources -->|IBGE SIDRA| SQL["sidra-sql"]
    Sources -->|Tesouro| TD["tddata"]
    Sources -->|RAIS/CAGED| PD["pdet-data"]
    Sources -->|Siscomex| CX["comexdown"]
    Sources -->|DATASUS| DS["datasus-fetcher"]
    
    SF --> Processing["Processamento & Transformação<br/>(Processamento Vetorial Polars)"]
    SQL --> Processing
    TD --> Processing
    PD --> Processing
    CX --> Processing
    DS --> Processing
    
    Processing --> Storage["Armazenamento Estruturado"]
    
    Storage --> PQ["Arquivos Parquet<br/>(Analítico)"]
    Storage --> PG["PostgreSQL<br/>(Operacional)"]
    
    PQ --> Analytics["Analytics & BI<br/>(Dashboards, ML, Relatórios)"]
    PG --> Analytics
```

## Princípios de Design

### 1. Modularidade

Cada ferramenta é **independente e reutilizável**:

- **sidra-fetcher**: `httpx` + `tenacity` apenas (sem deps de DataFrame; você traz Polars/Pandas)
- **tddata**: Async `httpx` + `tqdm`; opcional `polars` + `altair` via extra `[analysis]`
- **pdet-data**: FTP stdlib + `polars` + `tqdm` (binário `7z` em PATH para extração)
- **comexdown**: biblioteca padrão pura — sem deps de terceiros
- **datasus-fetcher**: cliente FTP stdlib puro
- **inmet-bdmep-data**: `httpx` + `pandas` + `pyarrow` (+ `polars` opcional)

Nenhuma ferramenta depende de outra. Misture e combine baseado em suas necessidades.

### 2. Resiliência

Fontes de dados governamentais são **pouco confiáveis**:

```
Problema: API IBGE faz timeout aleatoriamente
Solução:  Auto-retries com backoff exponencial
          Tratamento de timeout
          Tolerância a falha parcial

Problema: Rate limiting no acesso a API
Solução:  Throttling integrado
          Respeitar respostas HTTP 429
          Pacing de requisição adaptativo

Problema: Respostas malformadas
Solução:  Validação em forma/schema de dados
          Verificação e casting de tipo
          Tratamento de valores faltantes
```

### 3. Performance

Datasets brasileiros são **grandes**:

```
RAIS 2023:        ~60M registros, ~850 MB CSV → ~100 MB Parquet
CAGED mensal:     ~500k-1M registros
Títulos Tesouro:  ~1000 instrumentos × 20+ anos
Siscomex:         ~10M transações/mês

Solução:
  - Armazenamento colunar (Parquet): compressão 80%+
  - Lazy evaluation (Polars): Computar apenas o necessário
  - Streaming: Processar em batches, não tudo-de-uma-vez
  - Agregação: Reduzir no servidor antes de download
```

### 4. Reprodutibilidade

Todas as transformações são **determinísticas e registradas**:

- Mesma entrada → mesma saída (hashing determinístico)
- Passos de pipeline são registrados (rastreamento de linhagem)
- Versões de dados são rastreadas (timestamps, checksums)
- Transformações são idempotentes (seguro re-executar)

### 5. Sem Mágica

**Explícito > Implícito**:

- Você escolhe formato de output (Parquet, CSV, PostgreSQL)
- Você vê quais dados estão sendo buscados e transformados
- Mensagens de erro são acionáveis
- Sem perda silenciosa de dados ou truncamento

## Exemplo de Fluxo de Dados: Pipeline de Análise Econômica

```python
# 1. EXTRACT: cada ferramenta usa seu próprio padrão de acesso
import polars as pl
from sidra_fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao

# SIDRA: construir um Parametro e requisitar a URL
gdp_param = Parametro(
    agregado="1620",
    territorios={"1": ["all"]},
    variaveis=["116"],
    periodos=[],
    classificacoes={},
    formato=Formato.A,
    decimais={"": Precisao.M},
)
with SidraClient(timeout=60) as client:
    gdp = pl.DataFrame(client.get(gdp_param.url()))

# Tesouro Direto: converter CSVs brutos para Parquet
from tddata.converter import convert_to_parquet
convert_to_parquet(src_dir="raw/tesouro", dest_dir="data/tesouro", dataset_type="precos")
bonds = pl.read_parquet("data/tesouro/precos.parquet")

# 2. TRANSFORM: Polars
combined = gdp.join(bonds, on="date", how="inner")
combined = combined.with_columns([
    pl.col("V").cast(pl.Float64, strict=False).pct_change().alias("gdp_growth"),
    pl.col("yield").pct_change().alias("yield_change"),
])

# 3. LOAD
combined.write_parquet("gdp_bonds_analysis.parquet")
combined.write_database(
    "gdp_bonds",
    connection="postgresql://user:pass@host/db",
    if_table_exists="replace",
)

# 4. ANALYZE
data = pl.read_parquet("gdp_bonds_analysis.parquet")
print(data.select(pl.corr("gdp_growth", "yield_change")))
```

## Responsabilidades das Ferramentas

### Ferramentas de Extração (sidra-fetcher, tddata, pdet-data, comexdown, datasus-fetcher)

**Responsabilidade**: Obter dados de APIs governamentais com confiabilidade

**Faça**:

- Lidar com características das APIs (paginação, rate limits, retries)
- Normalizar formatos de data
- Validar schema
- Exportar em formatos padrão (Parquet, DataFrame)

**Não faça**:

- Transformar dados (isso é responsabilidade do usuário)
- Fazer suposições analíticas
- Esconder falhas silenciosamente

### Storage (Parquet / PostgreSQL)

**Responsabilidade**: Armazenamento eficiente e confiável

**Parquet** (recomendado para análise):

- Formato colunares (consultas analíticas rápidas)
- Altamente comprimido (80%+ economia de espaço)
- Schema preservado
- Sem necessidade de infraestrutura de banco de dados

**PostgreSQL** (recomendado para operações):

- Transações ACID (consistência)
- Acesso em tempo real
- Backups e replicação
- Concorrência multi-usuário

### Processing (Polars, Pandas)

**Responsabilidade**: Transformação de dados rápida e flexível

Use Polars para:

- Arquivos grandes (Parquet, CSV)
- Transformações complexas
- Avaliação lazy (otimização)

Use Pandas para:

- Integração com bibliotecas estatísticas
- Funções customizadas complexas
- Datasets menores

## Padrões de Implementação

### 1. Local Development

```mermaid
graph TD
    A["Seu computador"] --> B["Extrair"]
    B --> C["Transformar"]
    C --> D["Arquivos Parquet"]
    D --> E["Jupyter notebook<br/>Script Python"]
```

**Melhor para**: Análise exploratória, prototipagem

### 2. Daily Batch Pipeline

```mermaid
graph TD
    A["Tarefa agendada<br/>(cron / orquestrador)"] --> B["Extrair dados recentes"]
    B --> C["Validar"]
    C --> D["Transformar"]
    D --> E["Adicionar ao armazenamento"]
    E --> F["PostgreSQL<br/>(para aplicações)"]
    E --> G["Parquet<br/>(para análise)"]
```

**Melhor para**: Dados operacionais, dashboards de relatórios

### 3. Real-Time Streaming

```mermaid
graph TD
    A["API Governamental"] --> B["Monitorar novos dados"]
    B --> C["Validar"]
    C --> D["Transformar"]
    D --> E["Transmitir para banco de dados"]
    E --> F["Dashboard em tempo real<br/>alertas"]
```

**Melhor para**: Vigilância (epidemiologia, monitoramento comercial)

### 4. Integração Multi-Fonte

```mermaid
graph TD
    A["Múltiplas APIs<br/>(IBGE, Tesouro, Trabalho, Comércio, Saúde)"] --> B["Extrair em paralelo"]
    B --> C["Unir por chaves comuns"]
    C --> D["Conjunto de dados unificado"]
    D --> E["Data warehouse<br/>(PostgreSQL / Data lake)"]
    E --> F["Analytics, modelos ML, relatórios"]
```

**Melhor para**: Análise macroeconômica, modelagem econométrica

## Características de Performance

### Tempo de Extração

| Ferramenta | Tempo Típico | Volume de Dados |
|------|--------------|-------------|
| sidra-fetcher (série única) | 5-10s | 100-1000 linhas |
| sidra-fetcher (todos os dados) | 30-60s | 10k-100k linhas |
| tddata (todos os títulos) | 5-10s | 1000 títulos |
| pdet-data (ano RAIS) | 30-60s | 60M registros |
| pdet-data (agregado) | 5-10s | 10k-100k linhas |
| comexdown (anual) | 10-20s | 1M-10M transações |
| datasus-fetcher (doença) | 5-15s | 100k-1M registros |

### Tamanho de Armazenamento (Parquet Comprimido)

| Data | Raw Size | Parquet | Compression |
|------|----------|---------|-------------|
| RAIS 2023 | ~850 MB | ~100 MB | 88% |
| Treasury (20 years) | ~5 MB | ~1 MB | 80% |
| CAGED (monthly) | ~50 MB | ~6 MB | 88% |
| Siscomex (annual) | ~500 MB | ~50 MB | 90% |

## Escalabilidade

**Para a maioria dos casos de uso** (até bilhões de linhas):

- **Arquivos Parquet** em disco: Escalam para TBs facilmente
- **Polars**: Processa arquivos maiores que RAM usando streaming
- **PostgreSQL**: Lida com 100M+ linhas com indexação adequada

**Para escala extrema** (petabytes):

- Considere data lake (S3/armazenamento de objetos em nuvem)
- Processamento distribuído (Spark, Dask, DuckDB)
- Data warehouses em nuvem (BigQuery, Redshift, Snowflake)

## Padrões de Arquitetura Comuns

### Pesquisa Acadêmica

```mermaid
graph TD
    A["Extrair"] --> B["Limpar & agregar"]
    B --> C["Análise estatística"]
    C --> D["Publicação"]
```

### Inteligência de Negócios

```mermaid
graph TD
    A["Extração diária"] --> B["PostgreSQL"]
    B --> C["Ferramenta BI<br/>(Tableau, Power BI, Metabase)"]
    C --> D["Dashboard"]
```

### Previsão Econométrica

```mermaid
graph TD
    A["Extrair múltiplas fontes"] --> B["Unir & agregar"]
    B --> C["Modelagem de séries temporais"]
    C --> D["Previsão"]
    D --> E["API em tempo real"]
```

### Gestão de Riscos

```mermaid
graph TD
    A["Extrair dados diários"] --> B["Calcular métricas de risco"]
    B --> C["PostgreSQL<br/>(tempo real)"]
    C --> D["Sistema de alerta<br/>(se limites excedidos)"]
```

## Integração com Ferramentas Externas

### Integração de Dados

- **API Gateway**: Servir dados processados via REST API
- **Data Lake**: Arquivos Parquet em S3/Azure/GCS
- **Data Warehouse**: Carregar em Snowflake, BigQuery, Redshift
- **Reverse ETL**: Exportar insights de volta para sistemas operacionais

### Analytics & BI

- **Tableau / Power BI**: Conectar ao PostgreSQL
- **Jupyter**: Carregar arquivos Parquet para análise ad-hoc
- **R / Python**: Fluxos de trabalho padrão em ciência de dados
- **Spark**: Processamento distribuído para datasets muito grandes

### ML & Forecasting

- **Scikit-learn**: Classificação, regressão
- **Prophet**: Previsão de séries temporais
- **XGBoost**: Gradient boosting
- **TensorFlow**: Deep learning em séries temporais

## Melhores Práticas

### 1. Versioná Seus Dados

```
data/
├── gdp_2024_01_15.parquet
├── gdp_2024_01_20.parquet  # Re-buscado (dados corrigidos)
└── gdp_latest.parquet      # Symlink para o mais recente
```

### 2. Documente Seu Pipeline

```python
# Extrair: tabela PIB IBGE SIDRA 1620, variável 116
# Frequência: Trimestral
# Atraso de atualização: ~60 dias
# Última atualização: 2024-01-20
```

### 3. Validar em Cada Etapa

```python
# Após extrair
assert len(df) > 0, "Nenhum dado retornado"
assert "value" in df.columns, "Coluna de valor ausente"

# Após transformar
assert df["date"].is_unique(), "Datas duplicadas"
assert df["value"].is_null().sum() < 0.1 * len(df), ">10% faltando"
```

### 4. Monitorar Qualidade de Dados

```python
# Verificar mudanças inusitadas
new_value = df.tail(1)["value"][0]
old_value = df.tail(2)["value"][0]
change = (new_value - old_value) / old_value

if abs(change) > 0.50:
    alert(f"Mudança inusitada detectada: {change*100:.1f}%")
```

## Saiba Mais

- [Design Principles](design-principles.md)
- [Concepts - Data Engineering](../concepts/data-engineering.md)
- [Concepts - Pipelines](../concepts/pipelines.md)
