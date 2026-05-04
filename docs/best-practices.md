# Melhores Práticas

Este guia cobre padrões práticos usados em todas as ferramentas da Plataforma Brasileira de Dados Públicos. Seguindo esses padrões seu pipelines de dados ficarão mais rápidos, mais confiáveis e mais fáceis de manter.

## 1. Sempre Use Processamento Idempotent

**Definição**: Operações idempotentes produzem o mesmo resultado se executadas uma ou múltiplas vezes. Elas verificam antes de baixar/processar, pulam trabalho inalterado e resumem tarefas interrompidas.

### Por Que Importa

- **Economiza bandwidth**: Não re-baixe datasets inalterados
- **Economiza tempo**: Speedup 57x em execuções em cache (comexdown)
- **Tolerância a falhas**: Resume meio de transferência em vez de começar novamente
- **Seguro para retry**: Executar duas vezes produz mesmo resultado que uma

### Padrão: Verificar Antes de Baixar

```python
# ✅ Idempotente: comexdown HEAD-verifica Last-Modified antes de cada GET
from pathlib import Path
import comexdown

comexdown.get_year(Path("./DATA"), year=2023)
# Primeira execução: faz stream do CSV em chunks de 8 KiB
# Re-execuções: HEAD mostra Last-Modified == mtime local, GET é pulado
```

Não há flag `force_refresh` — para re-buscar, delete o arquivo local primeiro.

### Padrão: Retomada Inteligente

```sh
# ✅ datasus-fetcher sempre compara tamanho remoto vs local e pula correspondências
# Primeira tentativa: interrompida no meio
datasus-fetcher data --data-dir ./data sim-do-cid10 \
    --start 2023 --end 2023 --threads 5

# Segunda tentativa: re-execute o mesmo comando
# Arquivos já completos são pulados, apenas faltantes/incompatíveis são re-baixados
datasus-fetcher data --data-dir ./data sim-do-cid10 \
    --start 2023 --end 2023 --threads 5
```

### Padrão: Pular Archives Já Baixados

```python
# ✅ Fetchers pdet-data verificam se dest_filepath já existe e pulam.
# Re-executar `pdet-data fetch ./raw` apenas baixa novos archives RAIS / CAGED.
from pathlib import Path
from pdet_data import connect, fetch_rais

ftp = connect()
try:
    fetch_rais(ftp=ftp, dest_dir=Path("./raw"))  # idempotent
finally:
    ftp.close()
```

### Padrão: Dry-Run Antes de Bulk Downloads

```sh
# ✅ Visualizar o que `datasus-fetcher` faria download antes de confirmar
datasus-fetcher data --data-dir ./data sim-do-cid10 \
    --start 2018 --end 2023 --regions sp \
    --dry-run
# Prints filenames + sizes + grand total, no bytes transferred
```

## 2. Use Concorrência para Operações I/O-Bound

**Definição**: Concorrência significa fazer múltiplas operações de I/O (requisições de rede, downloads de arquivo) simultaneamente em vez de sequencialmente.

### Por Que Importa

- **Network I/O é lenta**: Uma única requisição pode levar 1 segundo. Enquanto aguarda uma resposta, você pode iniciar 5 outras.
- **Speedup massivo**: 4-10x mais rápido que abordagens sequenciais
- **Speedup livre**: Não requer hardware mais rápido; apenas melhor utilização de recursos

### Padrão: Async/Await para APIs REST

```python
import asyncio
from sidra_fetcher import AsyncSidraClient

async def fetch_multiple_metadata():
    async with AsyncSidraClient(timeout=60) as client:
        # ✅ Concorrente: busca metadados de 3 agregados simultaneamente
        return await asyncio.gather(
            client.get_agregado(1620),  # GDP
            client.get_agregado(1419),  # IPCA inflation
            client.get_agregado(6381),  # Unemployment (PNADC)
        )

# Sequential: ~6 seconds
# Concurrent: ~2 seconds (3x faster)
agregados = asyncio.run(fetch_multiple_metadata())
```

### Padrão: Crawling FTP Multithreaded

```sh
# ✅ Multithreaded: 5 concurrent FTP fetchers
datasus-fetcher data --data-dir ./data sim-do-cid10 \
    --start 2018 --end 2023 \
    --threads 5

# Sequential (--threads 1): 300 minutes
# Concurrent (--threads 5):   50 minutes (~6x faster)
```

Entrypoint Python equivalente:

```python
from pathlib import Path
from datasus_fetcher import fetcher
from datasus_fetcher.slicer import Slicer

fetcher.download_data(
    datasets=["sim-do-cid10"],
    destdir=Path("./data"),
    threads=5,
    slicer=Slicer(start_time="2018", end_time="2023", regions=None),
)
```

### Padrão: Batches Multi-Ano com Re-runs Idempotentes

`comexdown` é sequencial por design — depende de idempotência temporal em vez de paralelismo. Passe um range de ano e deixe a verificação HEAD/`Last-Modified` fazer re-runs baratos:

```bash
# Primeira execução baixa tudo; execuções posteriores apenas buscam o que mudou.
comexdown trade 2014:2023 -o ./DATA
```

```python
from pathlib import Path
import comexdown

for year in range(2014, 2024):
    comexdown.get_year(Path("./DATA"), year=year)  # HEAD-cached
```

Se genuinamente quer sobrepor trabalho não relacionado (ex. download SECEX junto com fetch SIDRA), faça na camada de orquestração com `asyncio` ou `concurrent.futures` — mas mantenha concorrência em um único nível para evitar explosão de threads.

## 3. Armazene Resultados em Parquet, Não CSV

**Definição**: Parquet é um formato de armazenamento colunares otimizado para análise. CSV é um formato de texto baseado em linhas dos anos 70.

### Por Que Importa

- **95%+ menor**: 8 GB CSV → 0.4 GB Parquet
- **100x mais rápido para ler**: Formato colunares deixa você pular dados irrelevantes
- **Tipado**: Sem adivinhar se uma coluna é string ou número
- **Comprimido**: Compressão embutida; sem arquivos gzip separados

### Padrão: Converter CSV para Parquet

```python
import polars as pl

# ❌ Lento e grande
df = pl.read_csv("large_file.csv")  # 8 GB, 30 segundos para ler
df.write_csv("output.csv")          # 4 GB, 60 segundos para escrever

# ✅ Rápido e pequeno
df = pl.read_csv("large_file.csv")
df.write_parquet("output.parquet")  # 0.4 GB, 2 segundos para escrever
df = pl.read_parquet("output.parquet")  # 0.5 segundos para ler
```

### Padrão: Parquet com Seleção de Colunas

```python
import polars as pl

# Ler apenas colunas que precisa (100x mais rápido que CSV)
df = pl.read_parquet(
    "large_file.parquet",
    columns=["year", "state", "salary", "employee_id"]
)

# CSV força você a ler arquivo inteiro, mesmo se precisa de 2 colunas
df = pl.read_csv("large_file.csv")  # Deve ler todas as 50 colunas
```

### Padrão: Bulk Convert para Parquet

```bash
# pdet-data fornece convert_rais / convert_caged por trás de um subcomando CLI.
# Descompacta cada .7z, faz parse com o schema por-ano, e escreve Parquet.
pdet-data convert ./raw ./parquet
```

```python
import polars as pl

# Ler uma vez, depois manter tudo em Parquet para análise
df = pl.read_parquet("parquet/rais-vinculos/2023.parquet")
# CSV é apenas para compartilhar com stakeholders não-técnicos
```

## 4. Use Lazy Evaluation para Análise Multi-Ano

**Definição**: Lazy evaluation adia computação até ser explicitamente requisitado. Deixa o otimizador de query simplificar suas operações antes de executá-las.

### Por Que Importa

- **Otimização**: Query optimizer combina múltiplas operações em pass único
- **Eficiência de memória**: Processe 100M linhas sem carregar tudo em RAM
- **Execução mais rápida**: Trabalho desnecessário é eliminado automaticamente

### Padrão: Lazy Group-By Aggregation

```python
import polars as pl

# ❌ Eager: Carrega todos os dados em memória, depois agrega
df = pl.read_parquet("rais_2023.parquet")
result = df.group_by("state").agg(pl.col("salary").mean())
# Uso alto de memória; múltiplas passagens sobre dados

# ✅ Lazy: Adia execução; optimizer combina operações
df = pl.read_parquet("rais_2023.parquet")
result = (
    df
    .lazy()  # Defer execution
    .filter(pl.col("salary") > 0)  # Optional: filter first
    .group_by("state")
    .agg(pl.col("salary").mean())
    .collect()  # Execute now
)
# Low memory usage; single optimized pass
```

### Padrão: Concatenação Multi-Ano

```python
import polars as pl

# ❌ Ineficiente: Agregar por ano, depois combinar
years_data = []
for year in range(2010, 2024):
    df = pl.read_parquet(f"rais_{year}.parquet")
    agg = df.group_by("sector").agg(pl.col("salary").mean())  # 14 agregações
    years_data.append(agg)

combined = pl.concat(years_data)

# ✅ Eficiente: Concatenar primeiro, agregar uma vez
years_data = []
for year in range(2010, 2024):
    df = pl.read_parquet(f"rais_{year}.parquet").with_columns(
        pl.lit(year).alias("year")
    )
    years_data.append(df)

combined = pl.concat(years_data, how="vertical")  # Concatenação única
by_sector = (
    combined
    .lazy()
    .group_by(["year", "sector"])
    .agg(pl.col("salary").mean())
    .collect()
)
```

## 5. Lide com Erros Graciosamente com Auto-Retry

**Definição**: Auto-retry significa retentar automaticamente operações falhadas com backoff exponencial. Não falhe em erros transitórios.

### Por Que Importa

- **Rede é não confiável**: Timeouts, conexões caídas, indisponibilidade temporária são normais
- **Backoff exponencial**: Previne sobrecarregar o servidor com retry storms
- **Transparente**: Você não precisa implementar manualmente lógica de retry

### Padrão: Retries Embutidas

`datasus-fetcher` retenta cada transferência FTP até 3 vezes em erros transitórios antes de desistir daquele arquivo — outras threads continuam. Para fazer um batch long-running sobreviver a falhas intermitentes, apenas re-execute o comando; a verificação de idempotência baseada em tamanho pega de onde parou.

```sh
datasus-fetcher data --data-dir ./data sim-do-cid10 \
    --start 2023 --end 2023 --threads 5
```

### Padrão: Envolver Retries em Seu Código

```python
import time

def with_retry(func, max_retries=3, backoff_factor=2):
    """Tenta novamente uma função com backoff exponencial."""
    last_exception = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = backoff_factor ** attempt
                print(f"Tentativa {attempt + 1} falhou: {e}; tentando novamente em {delay}s")
                time.sleep(delay)
    raise last_exception

# Exemplo: envolver uma chamada SIDRA (datasus-fetcher já retenta internamente)
from sidra_fetcher import SidraClient
client = SidraClient()
result = with_retry(lambda: client.get_agregado(1620), max_retries=5)
```

## 6. Valide Dados na Fonte

**Definição**: Valide dados imediatamente após buscar, antes de transformações caras. Detecte problemas de qualidade de dados cedo.

### Por Que Importa

- **Falhe rápido**: Detecte problemas de dados antes de desperdiçar tempo em análise
- **Melhores mensagens de erro**: Saiba exatamente qual arquivo da fonte está corrompido
- **Previna garbage in, garbage out**: Dados inválidos não contaminam sua análise

### Padrão: Validação Baseada em Tamanho

```python
import os
from pathlib import Path

# ✅ Validar tamanho do arquivo para detectar truncamento
def validate_downloaded_file(expected_size_bytes: int, path: Path) -> None:
    actual = path.stat().st_size
    if actual < expected_size_bytes * 0.95:
        raise ValueError(
            f"Arquivo baixado parece estar truncado:\n"
            f"  Esperado: {expected_size_bytes} bytes\n"
            f"  Real:     {actual} bytes"
        )

# datasus-fetcher já faz isso para você em cada execução — re-execute para recuperar
# um download truncado. Para seus próprios pipelines, aplique o mesmo padrão após fetch.
```

### Padrão: Validação de Schema

```python
import polars as pl

# ✅ Validar schema após ler
def validate_rais_schema(df):
    required_columns = {
        "year": pl.Int32,
        "employee_id": pl.Utf8,
        "salary": pl.Float64,
        "state": pl.Utf8,
    }
    
    for col_name, col_type in required_columns.items():
        if col_name not in df.columns:
            raise ValueError(f"Coluna ausente: {col_name}")
        
        if df.schema[col_name] != col_type:
            raise ValueError(
                f"Tipo incorreto para {col_name}: "
                f"esperado {col_type}, obtido {df.schema[col_name]}"
            )
    
    return True

df = pl.read_parquet("rais_2023.parquet")
validate_rais_schema(df)
```

### Padrão: Row Count Validation

```python
import polars as pl

# ✅ Validar contagem de linhas é razoável
def validate_rais_row_count(df, year):
    expected_min = 50_000_000  # Deveria ter no mínimo 50M registros de emprego
    expected_max = 80_000_000  # Deveria ter menos que 80M
    
    row_count = len(df)
    
    if row_count < expected_min or row_count > expected_max:
        raise ValueError(
            f"Contagem de linhas inusitada para RAIS {year}:\n"
            f"  Esperado: {expected_min:,} - {expected_max:,}\n"
            f"  Real: {row_count:,}\n"
            f"  Por favor, verifique integridade dos dados"
        )
    
    return True

df = pl.read_parquet("rais_2023.parquet")
validate_rais_row_count(df, year=2023)
```

## 7. Gerenciamento de Memória para Arquivos Grandes

**Definição**: Processe arquivos grandes sem carregar tudo em RAM. Use streaming/chunking ou lazy evaluation.

### Por Que Importa

- **RAIS é 50M+ linhas**: Não cabe em Pandas em máquinas típicas
- **Siscomex é gigabytes**: Abordagem ingênua causa crashes OOM
- **Streaming é livre**: Sem penalidade de performance para streaming; frequentemente mais rápido

### Padrão: Streaming Chunks

```python
# ✅ comexdown transmite cada download em chunks de 8 KiB via urllib —
#    memória constante independente do tamanho do arquivo, *.tmp atômico -> renomeia no sucesso.
from pathlib import Path
import comexdown

comexdown.get_year(Path("./DATA"), year=2023)
```

### Padrão: Lazy Polars Processing

```python
import polars as pl

# ❌ Eager: Carrega arquivo inteiro de 8GB em RAM
df = pl.read_parquet("rais_2023.parquet")  # OOM em máquinas com pouca memória
result = df.group_by("state").agg(pl.col("salary").mean())

# ✅ Lazy: Processa em modo streaming
result = (
    pl.read_parquet("rais_2023.parquet")
    .lazy()
    .group_by("state")
    .agg(pl.col("salary").mean())
    .collect()  # Execução por streaming; uso baixo de memória
)
```

### Padrão: Processamento CSV em Chunks

```python
import polars as pl

# ✅ Processar CSV em chunks
chunk_size = 1_000_000  # Processar 1M linhas por vez

all_results = []
for chunk in pl.read_csv_batched("large_file.csv", batch_size=chunk_size):
    # Process chunk
    result = chunk.group_by("state").agg(pl.col("salary").mean())
    all_results.append(result)

combined = pl.concat(all_results)
```

## 8. Documentação & Reprodutibilidade

**Definição**: Documente seus dados: de onde vêm, quando foram buscados, como foram transformados e como reproduzi-los.

### Por Que Importa

- **Trilha de auditoria**: Saiba exatamente quais dados estão em sua análise
- **Reprodutibilidade**: Outros podem verificar seus resultados
- **Debugging**: Quando algo quebra, você sabe o que mudou

### Padrão: Armazenar Metadados com Parquet

```python
import json
import polars as pl
from datetime import datetime
from pathlib import Path

# ✅ Salvar metadados junto aos dados
parquet_path = Path("parquet/rais-vinculos/2023.parquet")
df = pl.read_parquet(parquet_path)

metadata = {
    "source": "RAIS 2023 (vinculos)",
    "download_timestamp": datetime.now().isoformat(),
    "fetch_method": "pdet_data.convert_rais",
    "row_count": df.height,
    "columns": df.columns,
    "transformations": [
        "Descomprimido via 7z",
        "CSV analisado com schema por-ano (pdet_data.reader.read_rais)",
        "Cast INTEGER_COLUMNS / NUMERIC_COLUMNS / BOOLEAN_COLUMNS",
        "Escrito Parquet via polars.DataFrame.write_parquet",
    ],
}

parquet_path.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2))
```

### Padrão: Extração de Documentação

```sh
# ✅ Baixar dados + livros de códigos + tabelas auxiliares juntos
datasus-fetcher data --data-dir ./data sim-do-cid10 --start 2023 --end 2023
datasus-fetcher docs --data-dir ./docs sim
datasus-fetcher aux  --data-dir ./aux  sim
```

`.dbc` nomes de arquivo já codificam `dataset_uf_period_YYYYMMDD`, então múltiplas revisões DATASUS do mesmo período coexistem em disco. Use `datasus-fetcher archive --archive-data-dir ./archive` para rotacionar versões não-latest para fora da árvore ativa sem perdê-las.

### Padrão: Log de Transformação

```python
import logging

# ✅ Registrar toda transformação
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Processing
df = pl.read_parquet("rais_2023.parquet")
initial_count = len(df)

logger.info(f"Loaded RAIS 2023: {initial_count:,} rows")

# Filter
df = df.filter(pl.col("salary") > 0)
logger.info(f"Filtrado para {len(df):,} linhas com salário > 0 "
            f"(removidos {initial_count - len(df):,} registros inválidos)")

# Group
result = df.group_by("state").agg(pl.col("salary").mean())
logger.info(f"Agregado por estado: {len(result)} estados")

# Save
result.write_parquet("output.parquet")
logger.info("Resultados salvos em output.parquet")
```

## Checklist de Resumo

Quando construindo pipelines de dados com a Plataforma Brasileira de Dados Públicos:

- [ ] **Idempotent**: Verifique antes de baixar/processar (force_refresh=False)
- [ ] **Concorrente**: Use operações async/multithreaded para I/O (num_workers, AsyncClient)
- [ ] **Parquet**: Armazene resultados em Parquet, não CSV
- [ ] **Lazy**: Use lazy evaluation para datasets grandes (pl.lazy().collect())
- [ ] **Retry**: Configure auto-retry com backoff exponencial
- [ ] **Validate**: Verifique qualidade de dados imediatamente após buscar
- [ ] **Memory**: Stream ou chunk para arquivos grandes; use lazy evaluation
- [ ] **Document**: Registre transformações; armazene metadados com resultados; extraia docs

Seguindo esses padrões seus pipelines ficam rápidos, confiáveis e manteníveis.
