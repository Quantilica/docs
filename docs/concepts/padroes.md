# Padrões Práticos

Este guia cobre nove padrões usados em todas as ferramentas do ecossistema. Cada padrão materializa um ou mais [Princípios de Design](principios.md) em código real. Seguindo-os, seus pipelines ficam mais rápidos, confiáveis e fáceis de manter.

| Padrão | Princípio principal |
|---|---|
| [Processamento idempotente](#processamento-idempotente) | Resiliência, Reprodutibilidade |
| [Concorrência para I/O](#concorrencia-io) | Performance |
| [Parquet em vez de CSV](#parquet-vs-csv) | Performance, Reprodutibilidade |
| [Lazy evaluation](#lazy-evaluation) | Performance |
| [Auto-retry com backoff](#auto-retry) | Resiliência |
| [Validação na fonte](#validacao-na-fonte) | Resiliência, Sem Mágica |
| [Gestão de memória para arquivos grandes](#memoria-arquivos-grandes) | Performance |
| [Documentação e reprodutibilidade](#documentacao-reprodutibilidade) | Reprodutibilidade, Sem Mágica |
| [UX de CLI: progresso vs. logs](#cli-ux) | Sem Mágica |

---

## Processamento idempotente {#processamento-idempotente}

**Definição:** operações idempotentes produzem o mesmo resultado se executadas uma ou múltiplas vezes. Verificam antes de baixar/processar, pulam trabalho inalterado e resumem tarefas interrompidas.

### Por quê?

- **Economiza banda**: não re-baixe datasets inalterados.
- **Economiza tempo**: speedup 57× em re-runs cacheados (`comex-fetcher`).
- **Tolerância a falhas**: resume do meio em vez de recomeçar.
- **Seguro para retry**: rodar duas vezes produz o mesmo resultado que rodar uma vez.

### Padrão: verificar antes de baixar

```python
from pathlib import Path
import comex_fetcher

# comex-fetcher HEAD-verifica Last-Modified antes de cada GET
comex_fetcher.get_year(Path("./DATA"), year=2023)
# 1ª execução: stream do CSV em chunks de 8 KiB
# Re-execuções: HEAD mostra Last-Modified == mtime local; GET é pulado
```

Não há flag `force_refresh` — para re-buscar, delete o arquivo local primeiro.

### Padrão: retomada inteligente

```sh
# datasus-fetcher compara tamanho remoto vs. local e pula correspondências
datasus-fetcher sync -o ./data sim-do-cid10 \
    --start 2023 --end 2023 --threads 5

# Re-execução após interrupção: arquivos completos são pulados
datasus-fetcher sync -o ./data sim-do-cid10 \
    --start 2023 --end 2023 --threads 5
```

### Padrão: pular archives já baixados

```python
from pathlib import Path
from pdet_fetcher import fetch_rais

fetch_rais(dest_dir=Path("./raw"))  # idempotente: pula .7z já presentes
```

### Padrão: dry-run antes de bulk downloads

```sh
# Visualize o que datasus-fetcher baixaria antes de confirmar
datasus-fetcher sync -o ./data sim-do-cid10 \
    --start 2018 --end 2023 --regions sp \
    --dry-run
# Imprime nomes de arquivo + tamanhos + total — zero bytes transferidos
```

---

## Concorrência para I/O {#concorrencia-io}

**Definição:** múltiplas operações de I/O (rede, disco) simultâneas em vez de sequenciais.

### Por quê?

- **Network I/O é lenta**: uma requisição pode levar 1 s. Enquanto espera resposta, você pode iniciar mais 5.
- **Speedup**: 4-10× mais rápido que sequencial.
- **Speedup gratuito**: não exige hardware mais rápido — só melhor uso dos recursos.

### Padrão: async/await para APIs REST

```python
import asyncio
from sidra_fetcher.fetcher import AsyncSidraClient

async def fetch_multiple_metadata():
    async with AsyncSidraClient(timeout=60) as client:
        return await asyncio.gather(
            client.get_agregado(1620),  # PIB
            client.get_agregado(1419),  # IPCA
            client.get_agregado(6381),  # Desemprego (PNADC)
        )

# Sequencial: ~6 s
# Concorrente: ~2 s (3× mais rápido)
agregados = asyncio.run(fetch_multiple_metadata())
```

### Padrão: crawling FTP multithreaded

```sh
# 5 fetchers FTP concorrentes
datasus-fetcher sync -o ./data sim-do-cid10 \
    --start 2018 --end 2023 \
    --threads 5

# Sequencial (--threads 1): 300 min
# Concorrente (--threads 5):  50 min (~6× mais rápido)
```

Equivalente em Python:

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

### Padrão: batches multi-ano com re-runs idempotentes

`comex-fetcher` é sequencial por design — depende de idempotência temporal em vez de paralelismo. Passe um range de anos e deixe a verificação HEAD/`Last-Modified` fazer re-runs baratos:

```bash
# 1ª execução baixa tudo; execuções posteriores buscam só o que mudou.
comex-fetcher sync 2014:2023 -o ./DATA
```

```python
from pathlib import Path
import comex_fetcher

for year in range(2014, 2024):
    comex_fetcher.get_year(Path("./DATA"), year=year)  # HEAD-cached
```

Se quiser sobrepor trabalho não relacionado (download SECEX em paralelo com fetch SIDRA), faça na camada de orquestração com `asyncio` ou `concurrent.futures` — mas mantenha a concorrência em um único nível para evitar explosão de threads.

---

## Parquet em vez de CSV {#parquet-vs-csv}

**Definição:** Parquet é formato colunar otimizado para análise. CSV é formato textual baseado em linhas, dos anos 70.

### Por quê?

- **95%+ menor**: 8 GB CSV → 0,4 GB Parquet.
- **100× mais rápido para ler**: formato colunar permite pular dados irrelevantes.
- **Tipado**: sem adivinhar se uma coluna é string ou número.
- **Comprimido**: compressão embutida; sem `.gz` separado.

### Padrão: converter CSV para Parquet

```python
import polars as pl

# ❌ Lento e grande
df = pl.read_csv("large_file.csv")  # 8 GB, 30 s para ler
df.write_csv("output.csv")          # 4 GB, 60 s para escrever

# ✅ Rápido e pequeno
df = pl.read_csv("large_file.csv")
df.write_parquet("output.parquet")          # 0,4 GB, 2 s para escrever
df = pl.read_parquet("output.parquet")      # 0,5 s para ler
```

### Padrão: leitura seletiva de colunas

```python
import polars as pl

# Lê apenas as colunas necessárias (100× mais rápido que CSV)
df = pl.read_parquet(
    "large_file.parquet",
    columns=["year", "state", "salary", "employee_id"]
)
# CSV obrigaria ler todas as 50 colunas, mesmo precisando de 4
```

### Padrão: bulk convert

```bash
# pdet-fetcher: descompacta cada .7z, faz parse com schema por-ano, escreve Parquet
pdet-fetcher convert -i ./raw -o ./parquet
```

```python
import polars as pl

# Após converter, mantenha tudo em Parquet para análise
df = pl.read_parquet("parquet/rais-vinculos/2023.parquet")
# CSV apenas para compartilhar com stakeholders não-técnicos
```

---

## Lazy evaluation {#lazy-evaluation}

**Definição:** lazy evaluation adia a computação até ser explicitamente requisitada. O otimizador de query simplifica suas operações antes de executá-las.

### Por quê?

- **Otimização**: o otimizador combina múltiplas operações em pass único.
- **Eficiência de memória**: processe 100M linhas sem carregar tudo em RAM.
- **Execução mais rápida**: trabalho desnecessário é eliminado automaticamente.

### Padrão: group-by lazy

```python
import polars as pl

# ❌ Eager: carrega tudo, depois agrega
df = pl.read_parquet("rais_2023.parquet")
result = df.group_by("state").agg(pl.col("salary").mean())
# Memória alta; múltiplas passagens sobre os dados

# ✅ Lazy: optimizer combina filter + aggregation
result = (
    pl.scan_parquet("rais_2023.parquet")
    .filter(pl.col("salary") > 0)
    .group_by("state")
    .agg(pl.col("salary").mean())
    .collect()
)
# Memória baixa; pass único otimizado
```

### Padrão: concatenação multi-ano

```python
import polars as pl

# ❌ Ineficiente: agrega por ano, depois combina (14 agregações)
years_data = []
for year in range(2010, 2024):
    df = pl.read_parquet(f"rais_{year}.parquet")
    agg = df.group_by("sector").agg(pl.col("salary").mean())
    years_data.append(agg)
combined = pl.concat(years_data)

# ✅ Eficiente: concatena primeiro, agrega uma vez
years_data = []
for year in range(2010, 2024):
    df = pl.read_parquet(f"rais_{year}.parquet").with_columns(
        pl.lit(year).alias("year")
    )
    years_data.append(df)

combined = pl.concat(years_data, how="vertical")
by_sector = (
    combined.lazy()
    .group_by(["year", "sector"])
    .agg(pl.col("salary").mean())
    .collect()
)
```

---

## Auto-retry com backoff {#auto-retry}

**Definição:** retentar automaticamente operações falhadas com backoff exponencial. Não falhe em erros transitórios.

### Por quê?

- **Rede é instável**: timeouts, conexões caídas e indisponibilidade temporária são normais.
- **Backoff exponencial**: previne retry storms que sobrecarregam o servidor.
- **Transparente**: você não precisa implementar manualmente lógica de retry.

### Padrão: retries embutidas

`datasus-fetcher` retenta cada transferência FTP até 3× em erros transitórios antes de desistir do arquivo — outras threads continuam. Para um batch long-running sobreviver a falhas intermitentes, basta re-executar o comando; a verificação de idempotência por tamanho retoma de onde parou.

```sh
datasus-fetcher sync -o ./data sim-do-cid10 \
    --start 2023 --end 2023 --threads 5
```

### Padrão: envolver retries em código próprio

```python
import time

def with_retry(func, max_retries=3, backoff_factor=2):
    """Tenta novamente com backoff exponencial."""
    last_exception = None
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = backoff_factor ** attempt
                print(f"Tentativa {attempt + 1} falhou: {e}; retry em {delay}s")
                time.sleep(delay)
    raise last_exception

# Exemplo: envolver chamada SIDRA
from sidra_fetcher.fetcher import SidraClient
client = SidraClient()
result = with_retry(lambda: client.get_agregado(1620), max_retries=5)
```

---

## Validação na fonte {#validacao-na-fonte}

**Definição:** valide dados imediatamente após buscar, antes de transformações caras. Detecte problemas de qualidade cedo.

### Por quê?

- **Falhe rápido**: detecte problemas antes de desperdiçar tempo em análise.
- **Erros melhores**: saiba exatamente qual arquivo está corrompido.
- **Garbage in, garbage out**: dados inválidos não contaminam sua análise.

### Padrão: validação por tamanho

```python
from pathlib import Path

def validate_downloaded_file(expected_size_bytes: int, path: Path) -> None:
    actual = path.stat().st_size
    if actual < expected_size_bytes * 0.95:
        raise ValueError(
            f"Arquivo baixado parece truncado:\n"
            f"  Esperado: {expected_size_bytes} bytes\n"
            f"  Real:     {actual} bytes"
        )
# datasus-fetcher já faz isso para você; aplique o padrão em pipelines próprios.
```

### Padrão: validação de schema com `DataContract`

Em vez de escrever validação ad-hoc, declare um `DataContract` (do `quantilica-io`) e use-o em dois pontos: `cast()` na ingestão para travar tipos, `validate()` em testes para detectar regressões.

```python
import polars as pl
from quantilica_io.schema import DataContract, Field

RAIS_CONTRACT = DataContract(
    dataset_id="rais-vinculos",
    fields=[
        Field(name="year", dtype=pl.Int32),
        Field(name="employee_id", dtype=pl.Utf8),
        Field(name="salary", dtype=pl.Float64),
        Field(name="state", dtype=pl.Utf8),
    ],
)

# Em testes: falha cedo se a fonte mudar
def test_rais_schema_did_not_drift():
    df = pl.read_parquet("rais_2023.parquet")
    RAIS_CONTRACT.validate(df)  # ValueError/TypeError em mudança

# Em pipelines: trava tipos antes de gravar
df = pl.read_csv("rais_2023.csv")
df = RAIS_CONTRACT.cast(df)
df.write_parquet("rais_2023.parquet")
```

Os fetchers que parsam dados (`inmet`, `rtn`, `bcb-sgs`) já expõem seus próprios contratos — ver [`quantilica-io`](../fundacoes/quantilica-io.md#data-contracts).

### Padrão: validação de contagem de linhas

```python
import polars as pl

def validate_rais_row_count(df: pl.DataFrame, year: int) -> bool:
    expected_min, expected_max = 50_000_000, 80_000_000
    n = len(df)
    if n < expected_min or n > expected_max:
        raise ValueError(
            f"Contagem inusitada para RAIS {year}:\n"
            f"  Esperado: {expected_min:,} - {expected_max:,}\n"
            f"  Real: {n:,}"
        )
    return True
```

---

## Gestão de memória para arquivos grandes {#memoria-arquivos-grandes}

**Definição:** processe arquivos grandes sem carregar tudo em RAM. Use streaming/chunking ou lazy evaluation.

### Por quê?

- **RAIS é 50M+ linhas**: não cabe em Pandas em máquinas típicas.
- **Siscomex é GB**: abordagem ingênua causa OOM.
- **Streaming é gratuito**: sem penalidade — frequentemente até mais rápido.

### Padrão: streaming chunks

```python
from pathlib import Path
import comex_fetcher

# comex-fetcher faz stream de cada download em chunks de 8 KiB via urllib —
# memória constante independente do tamanho do arquivo;
# escrita atômica via *.tmp -> rename no sucesso
comex_fetcher.get_year(Path("./DATA"), year=2023)
```

### Padrão: lazy Polars

```python
import polars as pl

# ❌ Eager: carrega arquivo de 8 GB em RAM
df = pl.read_parquet("rais_2023.parquet")
result = df.group_by("state").agg(pl.col("salary").mean())

# ✅ Lazy: processa em modo streaming
result = (
    pl.scan_parquet("rais_2023.parquet")
    .group_by("state")
    .agg(pl.col("salary").mean())
    .collect(engine="streaming")
)
```

### Padrão: CSV em chunks

```python
import polars as pl

chunk_size = 1_000_000

all_results = []
for chunk in pl.read_csv_batched("large_file.csv", batch_size=chunk_size):
    result = chunk.group_by("state").agg(pl.col("salary").mean())
    all_results.append(result)

combined = pl.concat(all_results)
```

---

## Documentação e reprodutibilidade {#documentacao-reprodutibilidade}

**Definição:** documente seus dados — de onde vêm, quando foram buscados, como foram transformados, como reproduzir.

### Por quê?

- **Trilha de auditoria**: saiba exatamente quais dados estão na sua análise.
- **Reprodutibilidade**: outros podem verificar seus resultados.
- **Debugging**: quando algo quebra, você sabe o que mudou.

### Padrão: metadados ao lado do Parquet

```python
import json
from datetime import datetime
from pathlib import Path
import polars as pl

parquet_path = Path("parquet/rais-vinculos/2023.parquet")
df = pl.read_parquet(parquet_path)

metadata = {
    "source": "RAIS 2023 (vinculos)",
    "download_timestamp": datetime.now().isoformat(),
    "fetch_method": "pdet_fetcher.convert_rais",
    "row_count": df.height,
    "columns": df.columns,
    "transformations": [
        "Descomprimido via 7z",
        "CSV parseado com schema por-ano (pdet_fetcher.reader.read_rais)",
        "Cast INTEGER_COLUMNS / NUMERIC_COLUMNS / BOOLEAN_COLUMNS",
        "Escrito Parquet via polars.DataFrame.write_parquet",
    ],
}
parquet_path.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2))
```

### Padrão: extração de documentação na fonte

```sh
# Baixar dados + livros de códigos + tabelas auxiliares juntos
datasus-fetcher sync -o ./data sim-do-cid10 --start 2023 --end 2023 --docs --aux
```

Nomes de arquivo `.dbc` codificam `dataset_uf_period_YYYYMMDD`, então múltiplas revisões DATASUS coexistem em disco. `datasus-fetcher archive --archive-data-dir ./archive` rotaciona versões antigas sem perdê-las.

### Padrão: log de transformação

```python
import logging
import polars as pl

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("pipeline.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

df = pl.read_parquet("rais_2023.parquet")
initial = len(df)
logger.info(f"Carregado RAIS 2023: {initial:,} linhas")

df = df.filter(pl.col("salary") > 0)
logger.info(f"Filtrado para {len(df):,} (removidas {initial - len(df):,} inválidas)")

result = df.group_by("state").agg(pl.col("salary").mean())
logger.info(f"Agregado por estado: {len(result)} estados")

result.write_parquet("output.parquet")
logger.info("Salvo em output.parquet")
```

---

## UX de CLI: progresso vs. logs {#cli-ux}

**Definição:** CLIs de fetchers exibem barras de progresso tqdm por padrão. O flag `--verbose` troca para logs estruturados, sem atalho `-v`.

### Por quê?

- **Progresso é o padrão**: quem roda o CLI interativamente quer saber "quantos arquivos faltam", não timestamps de log.
- **Logs para debugging**: operadores e pipelines automatizados precisam de texto estruturado, não de barras ANSI.
- **Um flag, dois modos**: evita estados inconsistentes onde logs e barras se misturam no terminal.

### Padrão: barra de contagem de arquivos por dataset

Usando `quantilica_core.progress.batch_progress` e suprimindo o logger para `WARNING`:

```python
# downloader.py
from quantilica_core.progress import batch_progress

async def download(dest_dir, dataset_id, show_progress=True):
    resources = await get_dataset_resources(dataset_id)
    remote = _to_remote_resources(resources, repo)

    if show_progress:
        with batch_progress(dataset_id, total=len(remote)) as pbar:
            def _on_file_done(result):
                pbar.update(1)
            return await download_resources(..., on_file_done=_on_file_done)

    # modo verbose: log_step + logger.info
    with log_step(logger, "download-dataset", dataset_id=dataset_id):
        ...
```

```python
# cli.py
parser.add_argument(
    "--verbose",
    action="store_true",
    default=False,
    help="Exibir logs detalhados em vez de barra de progresso",
)

def main():
    ...
    configure_cli_logging(verbose=args.verbose)
    if not args.verbose:
        logging.getLogger("<package>").setLevel(logging.WARNING)
    asyncio.run(run_download(args, show_progress=not args.verbose))
```

### Comportamento esperado

| Invocação | Saída |
|---|---|
| `fetcher sync` | `prices \| 3/7 arquivo [00:10, ...]` |
| `fetcher sync --verbose` | `2025-01-10T14:22:01 INFO ... sync-dataset start` |

### Regras do padrão

- **`--verbose` sem shorthand `-v`**: evita conflito com flags globais em wrappers.
- **Modo padrão silencia INFO**: `logging.getLogger("<pacote>").setLevel(logging.WARNING)` — erros e warnings ainda aparecem.
- **`batch_progress` de `quantilica_core.progress`**: não crie barras tqdm diretamente no CLI.
- **`on_file_done` callback**: atualize a barra conforme cada arquivo termina (incluindo skips), não apenas no final.

### Fetchers que adotam este padrão

- `datasus-fetcher` — implementação de referência
- `tesouro-direto-fetcher` — migrado neste padrão
- `comex-fetcher` — migrado neste padrão
- `inmet-fetcher` — migrado neste padrão
- `rtn-fetcher` — migrado neste padrão
- `pdet-fetcher` — migrado neste padrão
- `sidra-fetcher` — migrado neste padrão (somente comandos de metadados; sem download)

---

## Checklist resumo

Quando construir pipelines com o ecossistema:

- [ ] **Idempotente**: verifique antes de baixar/processar.
- [ ] **Concorrente**: async/multithreaded para I/O.
- [ ] **Parquet**: armazene resultados em Parquet, não CSV.
- [ ] **Lazy**: use lazy evaluation para datasets grandes.
- [ ] **Retry**: configure auto-retry com backoff exponencial.
- [ ] **Valide**: cheque qualidade imediatamente após buscar.
- [ ] **Memória**: stream ou chunk para arquivos grandes.
- [ ] **Documente**: registre transformações e metadados.
- [ ] **CLI UX**: barra de progresso por padrão; `--verbose` para logs.

---

## Saiba mais

- [Princípios de Design](principios.md) — por que estes padrões existem.
- [Arquitetura do Ecossistema](arquitetura.md) — como os padrões se encaixam no sistema.
- [Parquet + Polars](parquet-polars.md) — tutorial focado no formato/biblioteca centrais.
