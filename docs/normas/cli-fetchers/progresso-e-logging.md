---
title: Progresso e logging
description: Callbacks de progresso para operações bulk e níveis de log na lógica de negócio, sem quebrar as barras de progresso.
---

# Progresso e logging

> Parte da norma [Padronização de CLI para Fetchers](../cli-fetchers.md). Os números de seção (§) são os da norma completa.

## 5. Padrão de callbacks para progresso em operações bulk

Quando a lógica de negócio (em `bulk.py` ou equivalente) executa N iterações e o plugin precisa mostrar progresso, use callbacks em vez de barras de progresso dentro da lógica de negócio.

### 5.1 Por que callbacks?

- A lógica de negócio não sabe se está sendo chamada por um CLI interativo, um script, um teste, ou outro contexto.
- Callbacks mantêm a lógica de negócio independente de Rich/tqdm.
- Permitem que o plugin controle 100% da apresentação.

### 5.2 Assinaturas padrão

O ecossistema usa três famílias de callback, escolhidas pelo tipo de operação:

| Família | Assinatura | Quando usar | Referência |
|---|---|---|---|
| **Bulk por item** | `on_progress(processed, total, ok, failed, skipped)` | N itens homogêneos com contadores ok/falha/skip | `bcb-sgs-fetcher bulk.py` |
| **Por grupo/página** | `on_grupo(nome, done, total)` / `on_page(page, n_pages)` | Operações com total descoberto ao vivo | `bcb-sgs-fetcher bulk.py` |
| **Por bytes de arquivo** | `ProgressCallback = (downloaded, total_bytes)` | Download de arquivo único; integra com `download_with_manifest(progress=cb)` | `comex-fetcher plugin.py` |
| **Pós-arquivo** | `on_done(filename, result)` com `result ∈ {"ok","skipped","failed"}` | N downloads paralelos onde cada arquivo reporta seu resultado ao terminar | `rtn-fetcher plugin.py` |

```python
from collections.abc import Callable
from quantilica.core.http import ProgressCallback  # Callable[[int, int], None]

# Bulk por item (N itens com total conhecido)
on_progress: Callable[[int, int, int, int, int], None] | None = None
# args: (processed, total, ok, failed, skipped)

# Por grupo (com total descoberto ao vivo)
on_grupo: Callable[[str, int, int], None] | None = None
# args: (nome_grupo, done, total)

# Por página
on_page: Callable[[int, int], None] | None = None
# args: (page, n_pages)

# Por bytes de arquivo (integra com HttpClient.download_with_manifest)
progress: ProgressCallback | None = None
# args: (downloaded_bytes, total_bytes); total_bytes=0 quando Content-Length ausente

# Pós-arquivo
on_done: Callable[[str, str], None] | None = None
# args: (filename, result) onde result ∈ {"ok", "skipped", "failed"}
```

### 5.3 Implementação na lógica de negócio

```python
def fetch_metadata_bulk(
    series_ids: list[int],
    scraper: ScraperClient,
    dest_dir: Path,
    sleeptime: float = 10,
    skip_existing: bool = False,
    on_progress: (
        Callable[[int, int, int, int, int], None] | None
    ) = None,
) -> tuple[int, int]:
    total = len(series_ids)
    successful = failed = skipped = processed = 0

    for series_id in sorted(series_ids):
        if skip_existing and (dest_dir / f"{series_id:06d}.json").exists():
            skipped += 1
            processed += 1
            if on_progress is not None:
                on_progress(processed, total, successful, failed, skipped)
            continue

        # ... lógica de fetch ...

        processed += 1
        if on_progress is not None:
            on_progress(processed, total, successful, failed, skipped)

    return successful, failed
```

Regras:

- Sempre guarde o callback em parâmetro com valor padrão `None` — a função deve funcionar sem callback.
- Chame o callback **após** atualizar os contadores, nunca antes.
- Chame o callback para **todos** os itens, incluindo pulados (skipped) — assim a barra de progresso avança corretamente.
- Não ponha lógica de display (print, tqdm, Rich) na lógica de negócio.

### 5.4 Consumo no `plugin.py`

```python
with _make_progress() as progress:
    task = progress.add_task("[cyan]0✓  0✗  0 skip[/cyan]", total=len(ids))

    def on_progress(
        processed: int,
        total: int,
        ok: int,
        failed: int,
        skipped: int,
    ) -> None:
        progress.update(
            task,
            completed=processed,
            description=(
                f"[green]{ok}✓[/green]"
                f"  [red]{failed}✗[/red]"
                f"  [dim]{skipped} skip[/dim]"
            ),
        )

    successful, failed_count = bulk.fetch_metadata_bulk(
        ids, scraper, dest_dir,
        sleeptime=sleeptime,
        skip_existing=skip_existing,
        on_progress=on_progress,
    )
```

---

## 6. Logging na lógica de negócio

### 6.1 Níveis permitidos por contexto

| Nível | Quando usar |
|---|---|
| `DEBUG` | Logs de rastreamento por item — "Fetching series 1234", "Skipping file X" |
| `INFO` | Marcos importantes de progresso com contexto amplo |
| `WARNING` | Situações anômalas mas recuperáveis — parse failure, ID mismatch |
| `ERROR` | Falhas que afetam um item mas não encerram o processamento |
| `CRITICAL` | Apenas para falhas que tornam impossível continuar |

### 6.2 O que demover para `DEBUG`

Logs que antes apareciam em `INFO` mas que constituem "barulho" em execuções normais devem ser demovidos para `DEBUG`. Exemplos reais do `bcb-sgs-fetcher`:

```python
# ❌ Antes — INFO emite uma linha por série, quebrando a barra de progresso
logger.info("Fetching metadata for series %d", series_id)

# ✅ Depois — DEBUG só aparece com --verbose
logger.debug("Fetching metadata for series %d", series_id)
```

Critério prático: se o log aparece N vezes dentro de um loop de N iterações, provavelmente deve ser `DEBUG`.

### 6.3 O que manter em `INFO` ou superior

- Marcos do início/fim de fases em pipelines de vários passos.
- Warnings de parsing — arquivos com dados inesperados.
- Session errors e retries.
- Mensagens de erro que identificam qual item falhou.

```python
# Manter em WARNING — o usuário precisa saber
logger.warning(
    "Series ID mismatch for %d (got %d), removing files",
    series_id,
    basic.series_id,
)

# Manter em ERROR — falha de sessão é relevante mesmo sem --verbose
logger.error("Session error for series %d: %s", series_id, exc)
```
