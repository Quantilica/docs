---
title: Padrões práticos de execução
description: "Idempotência, concorrência, auto-retry, validação na fonte e UX de CLI: os padrões táticos de execução do ecossistema em código real."
---

# Padrões Práticos de execução

Este guia cobre cinco padrões de **execução** usados em todas as ferramentas do ecossistema. Os padrões de **dados** (Parquet, lazy, memória e documentação) estão em [Padrões Práticos de dados](padroes-dados.md). Cada padrão materializa um ou mais [Princípios de Design](principios.md) em código real.

| Padrão | Princípio principal |
|---|---|
| [Processamento idempotente](#processamento-idempotente) | Resiliência, Reprodutibilidade |
| [Concorrência para I/O](#concorrencia-io) | Performance |
| [Auto-retry com backoff](#auto-retry) | Resiliência |
| [Validação na fonte](#validacao-na-fonte) | Resiliência, Sem Mágica |
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

!!! warning "Abra o cliente com `with` ou `async with`"
    Os clientes HTTP só reaproveitam a conexão dentro do gerenciador de contexto. Fora dele, cada requisição abre e fecha o seu próprio cliente, com novo handshake TLS. Em 15 requisições pequenas seguidas ao SIDRA, a mediana por requisição foi de 139 ms com `with` e 1.154 ms sem, no `SidraClient`; e de 216 ms com `async with` e 829 ms sem, no `AsyncSidraClient` (medição de 2026-10-13; [dados e script](https://github.com/Quantilica/docs/tree/main/benchmarks)).

    Entre síncrono e assíncrono, a busca de metadados de 8 agregados não mostrou diferença consistente: mediana de 1,7 s no síncrono (mínimo 1,4, máximo 7,6) e 1,5 s no assíncrono (mínimo 0,8, máximo 22,4). A variação da API do IBGE entre rodadas é maior que qualquer ganho de concorrência.

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
- [ ] **Retry**: configure auto-retry com backoff exponencial.
- [ ] **Valide**: cheque qualidade imediatamente após buscar.
- [ ] **CLI UX**: barras de progresso Rich sempre; `--verbose` sobe o log para `DEBUG`.
- [ ] **Dados**: Parquet, lazy, memória e documentação, em [Padrões Práticos de dados](padroes-dados.md).

---

## Saiba mais

- [Princípios de Design](principios.md) — por que estes padrões existem.
- [Arquitetura do Ecossistema](arquitetura.md) — como os padrões se encaixam no sistema.
- [Padrões Práticos de dados](padroes-dados.md) — Parquet, lazy evaluation, memória e documentação.
- [Parquet + Polars](parquet-polars.md) — tutorial focado no formato/biblioteca centrais.
