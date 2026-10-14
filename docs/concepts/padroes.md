---
title: Padrões práticos de implementação
description: Idempotência, concorrência explícita, Parquet, lazy evaluation, auto-retry e validação — os padrões táticos do ecossistema em código real.
---

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
- **Economiza tempo**: re-execuções sem mudança custam uma consulta ao remoto por arquivo (`comex-fetcher`).
- **Tolerância a falhas**: resume do meio em vez de recomeçar.
- **Seguro para retry**: rodar duas vezes produz o mesmo resultado que rodar uma vez.

### Padrão: verificar antes de baixar

```bash
# O sync consulta o remoto (tamanho, Last-Modified e ETag) antes de cada download
quantilica comex sync trade-exp -o ./DATA
# 1ª execução: baixa os arquivos em streaming
# Re-execuções: os arquivos locais já atualizados são pulados
```

Para re-buscar mesmo assim, use `--force`. Para ver o plano sem baixar, use `quantilica comex check`.

### Padrão: retomada inteligente

```sh
# datasus-fetcher compara tamanho remoto vs. local e pula correspondências
quantilica datasus sync -o ./data sim-do-cid10 \
    --start 2023 --end 2023 --threads 5

# Re-execução após interrupção: arquivos completos são pulados
quantilica datasus sync -o ./data sim-do-cid10 \
    --start 2023 --end 2023 --threads 5
```

### Padrão: pular archives já baixados

```python
from pathlib import Path
# Baixe antes pela CLI: quantilica pdet sync rais -o ./raw  (idempotente: pula arquivos já presentes)
```

### Padrão: dry-run antes de bulk downloads

```sh
# Visualize o que datasus-fetcher baixaria antes de confirmar
quantilica datasus sync -o ./data sim-do-cid10 \
    --start 2018 --end 2023 --regions sp \
    --dry-run
# Imprime nomes de arquivo + tamanhos + total — zero bytes transferidos
```

---

## Concorrência para I/O {#concorrencia-io}

**Definição:** múltiplas operações de I/O (rede, disco) simultâneas em vez de sequenciais.

### Por quê?

- **Network I/O é lenta**: uma requisição pode levar 1 s. Enquanto espera resposta, você pode iniciar mais 5.
- **O ganho depende do servidor.** Em 12 ZIPs de cerca de 11 MiB da CVM, 4 threads levaram mediana de 68,6 s contra 98,7 s com uma (1,4×), e 8 threads não melhoraram (74,4 s). A variação entre rodadas foi maior que o ganho: de 66 s a 136 s com uma thread ([dados e script](https://github.com/Quantilica/docs/tree/main/benchmarks)).
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

# As três chamadas saem juntas. O ganho depende da API: veja a medição abaixo.
agregados = asyncio.run(fetch_multiple_metadata())
```

!!! warning "Meça antes de assumir ganho"
    Ao buscar os metadados de 8 agregados (`get_agregado_metadados`), o `AsyncSidraClient` levou mediana de 6,6 s, contra 1,9 s do `SidraClient` em sequência (medição de 2026-10-13, 5 rodadas alternadas; [dados e script](https://github.com/Quantilica/docs/tree/main/benchmarks)). Chamado uma requisição por vez, o cliente assíncrono já foi mais lento que o síncrono, então o custo está no cliente, não na falta de paralelismo.

### Padrão: crawling FTP multithreaded

```sh
# 5 fetchers FTP concorrentes
quantilica datasus sync -o ./data sim-do-cid10 \
    --start 2018 --end 2023 \
    --threads 5

# --threads 1 baixa um arquivo por vez; --threads 5 baixa cinco juntos.
# O ganho depende do servidor FTP: meça com a sua fonte.
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

O `comex-fetcher` baixa em paralelo (`--workers`, padrão 4) e usa a verificação de frescor (tamanho, `Last-Modified` e `ETag`) para fazer re-runs baratos. Não há recorte por ano: a seleção é por grupo.

```bash
# 1ª execução baixa tudo; execuções posteriores buscam só o que mudou.
quantilica comex sync trade-exp trade-imp -o ./DATA
```

Se quiser sobrepor trabalho não relacionado (download SECEX em paralelo com fetch SIDRA), faça na camada de orquestração com `asyncio` ou `concurrent.futures` — mas mantenha a concorrência em um único nível para evitar explosão de threads.

---

## Parquet em vez de CSV {#parquet-vs-csv}

**Definição:** Parquet é formato colunar otimizado para análise. CSV é formato textual baseado em linhas, dos anos 70.

### Por quê?

- **82% a 87% menor** nos dados medidos (RAIS 2024, Centro-Oeste: 2,2 GiB de CSV → 406 MiB de Parquet).
- **Rápido para ler o que importa**: o formato colunar pula colunas e linhas irrelevantes; com filtro e 3 colunas, a leitura foi 51× a 100× mais rápida que a do CSV tipado nos dados medidos.
- **Tipado**: sem adivinhar se uma coluna é string ou número.
- **Comprimido**: compressão embutida; sem `.gz` separado.

### Padrão: converter CSV para Parquet

```python
import polars as pl

# CSV: texto sem tipos; toda leitura repete o parse e a conversão
df = pl.read_csv("large_file.csv")
df.write_csv("output.csv")

# Parquet: tipado e comprimido (5× a 8× menor nos dados medidos)
df = pl.read_csv("large_file.csv")
df.write_parquet("output.parquet")
df = pl.read_parquet("output.parquet")      # já vem tipado
```

### Padrão: leitura seletiva de colunas

```python
import polars as pl

# Lê apenas as colunas necessárias
df = pl.read_parquet(
    "large_file.parquet",
    columns=["year", "state", "salary", "employee_id"]
)
# CSV obrigaria ler todas as 50 colunas, mesmo precisando de 4
```

### Padrão: bulk convert

```bash
# pdet-fetcher: descompacta cada .7z, faz parse com schema por-ano, escreve Parquet
quantilica pdet convert -i ./raw -o ./parquet
```

```python
import polars as pl

# Após converter, mantenha tudo em Parquet para análise
df = pl.read_parquet("parquet/rais-vinculos/rais-vinculos_2023@*.parquet")
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
quantilica datasus sync -o ./data sim-do-cid10 \
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

Em vez de escrever validação ad-hoc, declare um `DataContract` (do `quantilica-analytics`) e use-o em dois pontos: `cast()` na ingestão para travar tipos, `validate()` em testes para detectar regressões.

```python
import polars as pl
from quantilica.analytics.schema import DataContract, Field

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

Os fetchers que parsam dados (`inmet` e `rtn`) já expõem seus próprios contratos — ver [`quantilica-analytics`](../fundacoes/quantilica-analytics.md#data-contracts).

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

```bash
# O download é feito em streaming (chunks de 64 KiB) pelo cliente HTTP do core:
# memória constante, independente do tamanho do arquivo, e escrita atômica
# via arquivo temporário renomeado no sucesso.
quantilica comex sync trade-exp -o ./DATA
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

parquet_path = next(Path("parquet/rais-vinculos").glob("rais-vinculos_2023@*.parquet"))
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
quantilica datasus sync -o ./data sim-do-cid10 --start 2023 --end 2023 --docs --aux
```

Os arquivos `.dbc` são gravados como `{dataset}_{AAAAMM}-{uf}@{AAAAMMDD}.dbc`, com a data de modificação da fonte após o `@`, então múltiplas revisões DATASUS coexistem em disco. `datasus-fetcher archive --archive-data-dir ./archive` rotaciona versões antigas sem perdê-las.

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

**Definição:** Os comandos de fetchers exibem barras de progresso Rich e só deixam passar logs de `WARNING` para cima. O flag `--verbose` baixa o nível para `DEBUG`, sem atalho `-v`; as barras continuam na tela e os logs aparecem entre elas.

### Por quê?

- **Progresso é o padrão**: quem roda o CLI interativamente quer saber "quantos arquivos faltam", não ler timestamps de log.
- **Logs para debugging**: operadores e pipelines automatizados precisam de texto estruturado, não de barras ANSI.
- **Um flag, dois níveis**: logs e barras passam pelo mesmo `Console` do Rich, então nunca se atropelam, nem com `--verbose`.

### Padrão: uma barra de lote e um pool fixo de barras por worker

O `sync` do `FetcherApp` já implementa o padrão, então todo fetcher que usa o SDK o herda sem escrever código. Só `sidra-fetcher` e `bcb-sgs-fetcher`, que não usam `FetcherApp`, o implementam no próprio `plugin.py`. Os helpers vêm de `quantilica.cli.ui`, que só o `plugin.py` de um fetcher pode importar:

```python
# plugin.py
from quantilica.cli.ui import (
    ProgressPool,
    get_console,
    make_batch_progress,
    make_download_progress,
    setup_rich_logging,
)
from rich.console import Group
from rich.live import Live

console = get_console()

def sync(entries, workers=4, verbose=False):
    setup_rich_logging(verbose, console=console)  # WARNING; DEBUG com --verbose

    batch = make_batch_progress(console)          # arquivos concluídos / total
    files = make_download_progress(console)       # bytes e velocidade
    pool = ProgressPool(workers=workers, file_prog=files)

    with Live(Group(batch, files), console=console, refresh_per_second=10):
        task = batch.add_task("Arquivos", total=len(entries))
        for entry in entries:  # em produção, dentro de um ThreadPoolExecutor
            with pool.acquire(description=entry["id"]) as on_progress:
                ...  # client.download_with_manifest(..., progress=on_progress)
            batch.update(task, advance=1)
```

`ProgressPool` cria `workers` barras fixas. Cada thread pega uma barra ociosa com `acquire()`, que devolve o callback `(baixado, total)` aceito pelo parâmetro `progress` de `HttpClient.download_with_manifest`, e a devolve ao pool ao terminar. Assim o terminal nunca tem mais barras que workers.

### Comportamento esperado

| Invocação | Saída |
|---|---|
| `quantilica <fonte> sync` | barra de lote (`MofN`, tempo restante) e uma barra por worker; só `WARNING` e erros |
| `quantilica <fonte> sync --verbose` | as mesmas barras, mais logs `DEBUG` formatados pelo `RichHandler` |

### Regras do padrão

- **`--verbose` sem shorthand `-v`**: evita conflito com flags globais em wrappers.
- **Sem `--verbose`, o nível é `WARNING`**: `setup_rich_logging(verbose=False)` cuida disso; erros e warnings ainda aparecem.
- **Use os helpers de `quantilica.cli.ui`**: não crie barras `tqdm` nem instâncias próprias de `Progress`.
- **Conte todo arquivo concluído**: atualize a barra de lote também para os que foram ignorados por já estarem atualizados, não só ao final.

Este padrão descreve o *porquê* e a forma geral. As regras completas de implementação —
estrutura de `cli.py`/`plugin.py`, logging, Rich, registro de entry points e checklist —
estão na referência do contribuidor [Padronização de CLI para Fetchers](../normas/cli-fetchers.md).

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
- [ ] **CLI UX**: barras de progresso Rich sempre; `--verbose` sobe o log para `DEBUG`.

---

## Saiba mais

- [Princípios de Design](principios.md) — por que estes padrões existem.
- [Arquitetura do Ecossistema](arquitetura.md) — como os padrões se encaixam no sistema.
- [Parquet + Polars](parquet-polars.md) — tutorial focado no formato/biblioteca centrais.
