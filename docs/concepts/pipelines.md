# Pipelines de Dados

Construindo fluxos de trabalho de dados confiáveis e automatizados.

## O Que é um Pipeline?

Uma sequência de etapas automatizadas que movem dados da fonte para o destino.

```
Pipeline = Extrair → Validar → Transformar → Carregar → Expor
```

### Exemplo Simples de Pipeline

```python
import polars as pl
from sidra_fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao

# EXTRACT: Construir um Parametro e buscar linhas brutas
param = Parametro(
    agregado="1620",
    territorios={"1": ["all"]},
    variaveis=["116"],
    periodos=[],
    classificacoes={},
    formato=Formato.A,
    decimais={"": Precisao.M},
)

with SidraClient(timeout=60) as client:
    rows = client.get(param.url())  # list[dict]

# VALIDATE: Verificar qualidade
assert len(rows) > 0, "Nenhum dado retornado"
gdp = pl.DataFrame(rows)
assert "V" in gdp.columns, "Coluna de valor ausente"

# TRANSFORM: Processar
gdp = gdp.with_columns([
    pl.col("V").cast(pl.Float64, strict=False).pct_change().alias("growth")
])

# LOAD: Armazenar resultado
gdp.write_parquet("gdp_analysis.parquet")
```

## Tipos de Pipeline

### 1. Pipelines em Batch

Executam em intervalos agendados (diário, semanal, mensal).

**Exemplo**: Busca diária de dados de desemprego

```python
# Agendamento: Todos os dias às 8 AM
# Executar: Buscar dados de CAGED de ontem
# Armazenar: Anexar ao PostgreSQL
# Tempo: 5-10 minutos
```

**Ferramentas**: cron, Airflow, Lambda, Cloud Scheduler

**Vantagens**:

- Simples implementar
- Fácil debugar (schedule previsível)
- Eficiente em custo (executa apenas quando necessário)

**Desvantagens**:

- Dados antigos entre execuções
- Pode ser excessivo para datasets pequenos

### 2. Pipelines de Streaming

Processa dados em tempo real conforme chegam.

**Exemplo**: Monitoramento ao vivo de casos de COVID-19

```python
# Monitor: API DATASUS
# Cada: 1 minuto
# Verificar: Novos casos reportados
# Alerta: Se threshold excedido
```

**Ferramentas**: Kafka, Spark Streaming, Kinesis, Pub/Sub

**Vantagens**:

- Alertas em tempo real possíveis
- Visão atual do mundo

**Desvantagens**:

- Infraestrutura complexa
- Custo operacional maior
- Dados governamentais brasileiros raramente atualizam em tempo real

### 3. Pipelines Híbridos

Batch com componentes em tempo real.

**Exemplo**: Dashboard econômico diário

```mermaid
graph TD
    A["Batch Diário<br/>Buscar IBGE SIDRA, Tesouro, RAIS<br/>Agregar e armazenar"] --> B["Tempo real A cada minuto<br/>Stream dados mais recentes<br/>Atualizar dashboard"]
```

## Padrões de Pipeline

### Padrão 1: Extrair-Carregar-Transformar

```mermaid
graph TD
    A["Dados Brutos<br/>inalterados"] --> B["LOAD"]
    B --> C["PostgreSQL<br/>tabela bruta"]
    C --> D["TRANSFORM<br/>on-demand"]
    D --> E["Views / Agregações"]
    E --> F["EXPOSE"]
    F --> G["Dashboards / Análise"]
```

**Vantagens**: Flexibilidade, preserva dados brutos, fácil reprocessar

**Melhor para**: Datasets grandes, análise evoluindo

### Padrão 2: Extrair-Transformar-Carregar

```mermaid
graph TD
    A["Dados Brutos<br/>API"] --> B["TRANSFORM"]
    B --> C["Dados Limpos<br/>memória"]
    C --> D["LOAD"]
    D --> E["PostgreSQL<br/>tabela processada"]
    E --> F["EXPOSE"]
    F --> G["Dashboards / Análise"]
```

**Vantagens**: Armazenamento otimizado, saída previsível

**Melhor para**: Datasets pequenos, transformações estáveis

### Padrão 3: Data Lake

```mermaid
graph TD
    A["Múltiplas Fontes<br/>APIs, bancos de dados"] --> B["INGEST"]
    B --> C["Raw Layer<br/>Arquivos Parquet em S3"]
    C --> D["TRANSFORM"]
    D --> E["Camadas Bronze/Silver/Gold"]
    E --> F["EXPOSE"]
    F --> G["Dashboards, ML, Analytics"]
```

**Vantagens**: Escalável, flexível, trilha de auditoria

**Melhor para**: Enterprise, múltiplas fontes de dados, grande escala

## Construindo um Pipeline de Produção

### Etapa 1: Definir Requisitos

```
Fonte de dados: Tabela SIDRA 1620 IBGE, variável 116
Frequência de atualização: Semanal (IBGE publica sextas)
Lag de atualização: 60 dias (liberado sextas)
Volume: 1000-2000 linhas por fetch
Histórico: Manter 20+ anos
Qualidade: Validar schema, verificar NULLs, monitorar outliers
Output: Tabela PostgreSQL + arquivo Parquet
SLA: Dados Disponíveis dentro de 2 horas da publicação
```

### Etapa 2: Error Handling

```python
import logging
import httpx
import polars as pl
from sidra_fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao

logger = logging.getLogger(__name__)

param = Parametro(
    agregado="1620",
    territorios={"1": ["all"]},
    variaveis=["116"],
    periodos=[],
    classificacoes={},
    formato=Formato.A,
    decimais={"": Precisao.M},
)

try:
    with SidraClient(timeout=60) as client:
        rows = client.get(param.url())

    if not rows:
        raise ValueError("Resultado vazio do IBGE")

    pl.DataFrame(rows).write_parquet("gdp.parquet")
    logger.info(f"Busca bem-sucedida de {len(rows)} linhas")

except httpx.TimeoutException:
    logger.error("IBGE API timeout - tentará novamente amanhã")

except httpx.HTTPStatusError as e:
    logger.error(f"Erro HTTP {e.response.status_code}: {e}")

except Exception as e:
    logger.exception(f"Erro inesperado: {e}")
    raise
```

### Etapa 3: Monitoramento

```python
import polars as pl
from datetime import datetime, timedelta

def check_pipeline_health():
    """Verificar se pipeline está saudável"""
    
    # Check 1: Recência
    df = pl.read_parquet("gdp.parquet")
    last_date = df["date"].max()
    age = datetime.now() - last_date
    
    if age > timedelta(days=75):  # Espera atualização dentro de 75 dias
        alert(f"Dados com {age.days} dias de idade")
    
    # Check 2: Completude
    expected_quarters = 96  # 24 anos
    actual_quarters = len(df)
    
    if actual_quarters < expected_quarters * 0.95:
        alert(f"Faltam dados: {expected_quarters - actual_quarters} linhas")
    
    # Check 3: Qualidade
    missing_values = df["value"].is_null().sum()
    
    if missing_values > 0:
        alert(f"{missing_values} valores faltantes")
    
    # Check 4: Anomalias
    recent_mean = df.tail(8)["value"].mean()  # Últimos 2 anos
    all_time_mean = df["value"].mean()
    
    change = abs(recent_mean - all_time_mean) / all_time_mean
    if change > 0.50:
        alert(f"Valor mudou {change*100:.1f}%")

if __name__ == "__main__":
    check_pipeline_health()
```

### Etapa 4: Agendamento

**Opção 1: cron** (simples, uma máquina)

```bash
# Executar toda sexta às 9 AM
0 9 * * 5 /usr/bin/python3 /home/user/fetch_gdp.py

# Output de log
0 9 * * 5 /usr/bin/python3 /home/user/fetch_gdp.py >> /var/log/gdp_fetch.log 2>&1
```

**Opção 2: Apache Airflow** (complexo, distribuído)

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def fetch_gdp():
    import polars as pl
    from sidra_fetcher import SidraClient
    from sidra_fetcher.sidra import Parametro, Formato, Precisao

    param = Parametro(
        agregado="1620",
        territorios={"1": ["all"]},
        variaveis=["116"],
        periodos=[],
        classificacoes={},
        formato=Formato.A,
        decimais={"": Precisao.M},
    )
    with SidraClient(timeout=60) as client:
        rows = client.get(param.url())
    pl.DataFrame(rows).write_parquet("gdp.parquet")

with DAG(
    "gdp_pipeline",
    schedule_interval="0 9 * * 5",  # Toda sexta 9 AM
    start_date=datetime(2024, 1, 1),
    default_args={"retries": 3}
) as dag:
    
    extract = PythonOperator(
        task_id="fetch_gdp",
        python_callable=fetch_gdp
    )
    
    validate = PythonOperator(
        task_id="validate_data",
        python_callable=validate_gdp
    )
    
    load = PythonOperator(
        task_id="load_to_db",
        python_callable=load_to_postgres
    )
    
    extract >> validate >> load
```

## Pipeline Multi-Fonte

Combinando dados de múltiplas fontes brasileiras. Cada ferramenta tem seu próprio padrão de acesso — use-as como blocos de construção:

```python
import polars as pl
import sqlalchemy as sa
from sidra_fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao

# 1. SIDRA (IBGE): construir Parametro → client.get(url) → list[dict]
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

# 2. Tesouro Direto (tddata): converter + analytics em CSVs brutos
from tddata.converter import convert_to_parquet
convert_to_parquet(
    src_dir="raw/tesouro",
    dest_dir="data/tesouro",
    dataset_type="precos",
)
bonds = pl.read_parquet("data/tesouro/precos.parquet")

# 3. RAIS (pdet-data): FTP fetch + conversão Polars
from pdet_data.fetch import connect, fetch_rais
from pdet_data.reader import convert_columns_dtypes
ftp = connect()
fetch_rais(ftp, dest_dir="raw/rais")  # baixa CSVs comprimidos

# Persistir cada fonte
gdp.write_parquet("data/gdp.parquet")
bonds.write_parquet("data/bonds.parquet")

# Carregar em PostgreSQL para joins cross-source
engine = sa.create_engine("postgresql://user:pass@localhost/analytics")
gdp.write_database("gdp", engine, if_table_exists="replace")
bonds.write_database("bonds", engine, if_table_exists="replace")
```

## Testando Pipelines

### Testes Unitários

```python
import pytest
import polars as pl

def test_fetch_gdp():
    """Testar extração de dados"""
    from sidra_fetcher import SidraClient
    from sidra_fetcher.sidra import Parametro, Formato, Precisao

    param = Parametro(
        agregado="1620",
        territorios={"1": ["all"]},
        variaveis=["116"],
        periodos=[],
        classificacoes={},
        formato=Formato.A,
        decimais={"": Precisao.M},
    )
    with SidraClient(timeout=60) as client:
        rows = client.get(param.url())

    assert len(rows) > 0, "Resultado vazio"
    assert "V" in rows[0], "Campo V (valor) ausente"
    assert "D3C" in rows[0] or "D2C" in rows[0], "Campo dimensão ausente"

def test_validate_gdp(gdp_data):
    """Testar lógica de validação"""
    assert (gdp_data["value"] > 0).all(), "Valores negativos"
    assert gdp_data["value"].is_null().sum() == 0, "Valores nulos"

def test_transform_gdp(gdp_data):
    """Testar transformação"""
    gdp_with_growth = gdp_data.with_columns([
        pl.col("value").pct_change().alias("growth")
    ])
    
    assert "growth" in gdp_with_growth.columns
    assert gdp_with_growth["growth"].dtype == pl.Float64
```

### Testes de Integração

```python
def test_end_to_end_pipeline(tmp_path):
    """Testar pipeline completo"""
    from pathlib import Path
    import polars as pl
    
    # Extrair
    gdp = fetch_gdp()
    
    # Validar
    assert len(gdp) > 100
    
    # Transformar
    gdp = gdp.with_columns([
        pl.col("value").pct_change().alias("growth")
    ])
    
    # Carregar
    output = tmp_path / "gdp.parquet"
    gdp.write_parquet(output)
    
    # Verificar
    loaded = pl.read_parquet(output)
    assert len(loaded) == len(gdp)
    assert "growth" in loaded.columns
```

## Armadilhas Comuns

### Armadilha 1: Falhas Silenciosas

```python
# Ruim: Falha silenciosamente
try:
    gdp = fetch_data()
except:
    gdp = pd.DataFrame()  # Resultado vazio
    
# Bom: Log e alerta
try:
    gdp = fetch_data()
except Exception as e:
    logger.error(f"Falha ao buscar: {e}")
    alert_team()
    raise
```

### Armadilha 2: Sem Error Handling

```python
# Ruim: Uma falha quebra tudo
gdp = fetch_gdp()  # Pode falhar
bonds = fetch_bonds()  # Não roda se gdp falha
employment = fetch_employment()  # Não roda

# Bom: Tratar cada um independentemente
sources = {
    "gdp": fetch_gdp,
    "bonds": fetch_bonds,
    "employment": fetch_employment
}

results = {}
for name, fetch_fn in sources.items():
    try:
        results[name] = fetch_fn()
    except Exception as e:
        logger.error(f"Falha ao buscar {name}: {e}")
        # Continuar com outras fontes
```

### Armadilha 3: Sem Validação de Dados

```python
# Ruim: Confiar na API
gdp = fetch_data()
gdp.write_parquet("gdp.parquet")  # E se API retornar lixo?

# Bom: Validar antes de armazenar
gdp = fetch_data()

if len(gdp) == 0:
    raise ValueError("Resultado vazio")
if gdp["value"].is_null().sum() > 0.5 * len(gdp):
    raise ValueError("Muitos nulos")

gdp.write_parquet("gdp.parquet")
```

## Armazenamento & Formatos

Depois de extrair e transformar dados, escolher o formato de armazenamento certo é crítico. Aqui como decidir:

### Parquet (Recomendado para Análise)

**O quê**: Formato de armazenamento colunares, comprimido

**Vantagens**:

- ✅ Altamente comprimido (80%+ economia vs CSV)
- ✅ Leitura rápida (colunares: ler apenas colunas necessárias)
- ✅ Sem banco de dados (apenas arquivos)
- ✅ Agnóstico de linguagem (Python, R, Rust, etc.)
- ✅ Schema preservado
- ✅ Cloud-native (funciona com S3, GCS, Azure)

**Melhor para**: Dados históricos (arquivo), consultas analíticas (dashboards, relatórios), datasets grandes

### PostgreSQL (Recomendado para Operações)

**O quê**: Banco de dados relacional, interface SQL

**Vantagens**:

- ✅ Transações ACID (consistência)
- ✅ Acesso concorrente (múltiplos usuários)
- ✅ Atualizações em tempo real
- ✅ Interface SQL (consultas poderosas)
- ✅ Backups & replicação embutidos

**Melhor para**: Dados ao vivo (constantemente atualizados), aplicações (precisam consistência), ambientes multi-usuário

### CSV (Simples, Legível por Humanos)

**Vantagens**:

- ✅ Legível por humanos
- ✅ Funciona em qualquer lugar
- ✅ Sem ferramentas especiais

**Desvantagens**:

- ❌ Lento para ler arquivos grandes
- ❌ Tamanho grande de arquivo (sem compressão)
- ❌ Sem informação de tipo

**Melhor para**: Datasets pequenos (<100 MB), troca de dados com usuários não-técnicos

### Comparação de Formatos

| Formato | Tamanho | Velocidade | Schema | Type Safety | Concorrente |
|--------|------|-------|--------|-------------|------------|
| CSV | ⭐⭐⭐ (grande) | ⭐ (lento) | ❌ | ❌ | ✅ (leitura) |
| Parquet | ⭐ (minúsculo) | ⭐⭐⭐ (rápido) | ✅ | ✅ | ❌ (leitura) |
| PostgreSQL | ⭐⭐ (médio) | ⭐⭐ (rápido) | ✅ | ✅ | ✅ |

### Estratégia: Arquivo Parquet + PostgreSQL Live

```
Parquet (armazenamento longo prazo)
    ↓ [arquivo anual]
    gdp_2015.parquet
    gdp_2024.parquet

PostgreSQL (dados ao vivo)
    ↓ [apenas últimos meses]
    Últimos 12 meses de dados
    Atualizado diariamente
    
Benefícios:
  - Arquivo eficiente (armazenamento barato)
  - Consultas ao vivo rápidas (dados atuais em BD)
  - Recuperação de arquivos se necessário
```

### Melhores Práticas

1. **Usar formatos apropriados**: CSV para desenvolvimento, Parquet para armazenamento, PostgreSQL para operações
2. **Versione seus dados**: `gdp_2024_01_10.parquet`, `gdp_2024_01_15.parquet` (correções), etc.
3. **Arquive dados antigos**: Manter últimos 2 anos em PostgreSQL, arquivar dados mais antigos em Parquet
4. **Indexar colunas críticas**: Acelerar consultas comuns em PostgreSQL

## Saiba Mais

- [Data Engineering](data-engineering.md)
- [Architecture Overview](../architecture/overview.md)
