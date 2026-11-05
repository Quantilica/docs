---
title: Montagem, Operação e Automação do Data Lake no Pendulograph
description: "Guia operacional para montagem física, particionamento Hive, perfis DuckDB, automação desacoplada e esteira contínua de marts analíticos."
---

# Montagem, Operação e Automação do Data Lake no Pendulograph

Este guia operacional estabelece o roteiro canônico para montagem, configuração, sincronização e automação industrial do **Universal Hive Parquet Lake** na estação de alta performance **`pendulograph`** (Windows, 96 GB de memória RAM).

---

## 1. Topologia Operacional e Arquitetura de Hardware

A infraestrutura do ecossistema Quantilica divide-se em três máquinas especializadas:
- **`fedora` (Linux local):** Executa os crons diários de coleta dos fetchers (`infra/cron_fetch.sh`), controle de ingestão efêmera e upload seguro para o Google Drive via `rclone`.
- **`pendulograph` (Windows local):** Hospeda o **Data Lake oficial** em Parquet particionado Hive e o acervo bruto imutável. Realiza construções massivas, auditorias de integridade e o cálculo in-memory dos marts analíticos em DuckDB.
- **`VPS` (Linux nuvem):** Hospeda a aplicação web `quantilica-portal` e o banco PostgreSQL de produção (< 90 GB), recebendo exclusivamente tabelas agregadas servidas.

### Especificação de Hardware da Estação (`pendulograph`)

| Recurso | Especificação | Função no Data Lake |
|---|---|---|
| **Memória RAM** | **96 GB DDR5** | Suporta super-paralelismo (6 workers x 14 GB) e agregações massivas in-memory (64 GB) em DuckDB. |
| **Drive F:\ (SSD NVMe)** | **NVMe Gen4 Alta Velocidade** | Hospeda a raiz do Lake (`F:\lake`). |
| **Drive H:\ (DrivePool, HDD)** | **Alta Capacidade (~7,4 TB, discos J: e E:)** | Acervo bruto imutável "Nada se Apaga" (`H:\data\raw`), visão vigente (`H:\data\vigente`) e datasets hipervolumosos (`H:\lake\rfb-cnpj`). Desde nov/2026 o J: é disco membro do pool e não guarda pastas próprias. |
| **Drive C:\** | SSD do sistema | Ambiente Python do lake (`C:\lake-env`) e scratch (`C:\lake-scratch`). |

---

## 2. Arranjo de Armazenamento e NTFS Junctions

Para compatibilizar a altíssima velocidade do SSD NVMe com a grande capacidade do arranjo HDD, adota-se o particionamento híbrido com **NTFS Junctions**:
- A raiz oficial do lake reside em `F:\lake`.
- Tabelas hipervolumosas de menor intensidade de I/O aleatório (especificamente o dataset consolidado de cadastros e sócios do **RFB-CNPJ**, com ~245 GB) residem fisicamente em `H:\lake\rfb-cnpj`.
- Uma junction NTFS conecta os caminhos de forma transparente para motores analíticos:

```cmd
:: Criar junction transparente no Windows (cmd como Administrador):
mklink /J "F:\lake\rfb-cnpj" "H:\lake\rfb-cnpj"
```

Dessa forma, leitores como DuckDB, Polars e Apache Arrow acessam `read_parquet('F:/lake/rfb-cnpj/**/*.parquet')` sem distinguir a fronteira física entre drives.

---

## 3. Variáveis de Ambiente Canônicas

No arquivo `.env` do workspace (ou nas variáveis de ambiente do sistema no Windows):

```env
# Raiz do Lake e Scratch temporário no SSD NVMe
QUANTILICA_LAKE_DIR=F:\lake
QUANTILICA_LAKE_SCRATCH=C:\lake-scratch

# Limites DuckDB para os 96 GB de RAM
QUANTILICA_DUCKDB_MEMORY=64GB
QUANTILICA_DUCKDB_THREADS=16

# Conexão cross-machine ao Ledger do PostgreSQL de ingestão no fedora
INGEST_DATABASE_URI=postgresql+psycopg://postgres:SENHA@fedora.lan:5432/quantilica_ingest
```

---

## 4. Pipeline de Replicação LAN e Visão Vigente (`lake-sync`)

### Replicação Fedora $\to$ Pendulograph
Durante as coletas diárias no `fedora`, cada arquivo bruto e seu sidecar `.manifest.json` são replicados diretamente para `H:\data\raw` no `pendulograph` via compartilhamento CIFS (`/mnt/pendulograph_raw`) ou rsync:
- A exclusão efêmera local no `fedora` exige dupla confirmação (cópia no pendulograph com conferência de SHA-256 e upload no Google Drive).
- Se a estação `pendulograph` estiver desligada, a coleta conclui o upload na nuvem normalmente. Ao ligar a estação, o `lake-sync` baixa apenas os deltas faltantes.

### Materialização da Visão Vigente
No `pendulograph`, a sincronização unificada é disparada por:

```powershell
uv run python -m workers.cli ingest lake-sync `
    --sources datasus,rfb-cnpj,pdet,tesouro-direto,inmet,anp,anac,cvm `
    --raw "H:\data\raw" `
    --view "H:\data\vigente" `
    --lake "F:\lake" `
    --pull-missing `
    --profile 96gb-batch
```

O comando:
1. Conecta-se ao PostgreSQL de ingestão via rede local;
2. Monta ~480.000 hardlinks na visão vigente `H:\data\vigente`;
3. Exclui arquivos quarentenados em `ingest.file_exclusion`;
4. Baixa do remote rclone quaisquer deltas pendentes (`--pull-missing`);
5. Constrói e audita o Lake Parquet com relatório auditável.

> **Aposentadoria de `_jobs`:** Os antigos scripts manuais de `H:\data\_jobs` (antes `J:\data\_jobs`; `linklatest.py`, `footers.py`, etc.) foram aposentados e substituídos integralmente por este comando.

---

## 5. Perfis de Memória e Otimização para 96 GB de RAM

O `quantilica lake build` e o `workers.cli ingest lake-sync` dispõem de perfis otimizados:

### 1. Perfil em Lote Multiprocesso (`--profile 96gb-batch`)
- **Alocação:** 6 workers x 14 GB = **84 GB alocados**, mantendo 12 GB livres para buffers do sistema operacional.
- **Uso:** Construção paralela de fontes com múltiplas tabelas médias (CVM, DATASUS, INMET, ANAC, TSE).

### 2. Perfil Monolítico Dedicado (`--profile 96gb-monolithic`)
- **Alocação:** 1 worker x **64 GB de RAM**, 16 threads.
- **Uso:** Datasets hipervolumosos (`sia-pa` com 203 GB de DBCs brutos ou `rfb-cnpj`).
- **Impacto:** O DuckDB retém hash tables e ordenações diretamente na memória RAM, reduzindo a escrita no SSD NVMe em 80% e cortando o tempo de processamento de `sia-pa` de 15 horas para menos de 2 horas.

---

## 6. Blindagem de Runtime no Windows (`run-lake-job.ps1`)

Para evitar que desconexões acidentais da sessão OpenSSH encerrem tarefas longas:

```powershell
# Disparo desacoplado imune ao fechamento do terminal SSH:
.\infra\run-lake-job.ps1 -Action build -Profile 96gb-batch -Detached
```

O launcher:
- Despacha o comando através do WMI (`[wmiclass]"Win32_Process".Create`), desacoplando-o da árvore da sessão SSH;
- Chama a Win32 API `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED)`, impedindo suspensão ou repouso do Windows;
- Grava logs de execução em `F:\lake\.build\logs\`.

---

## 7. Auditoria Semanal e Auto-Cura de Retificações Silenciosas

Determinadas fontes governamentais (ex.: ANP e ANAC) republicam ou retificam dados históricos mantendo o mesmo nome de arquivo. Para detectar e auto-curar essas divergências:

1. **Agendamento no Task Scheduler:**
   ```powershell
   .\infra\register-lake-tasks.ps1 -TaskName "Quantilica-Lake-Audit-Weekly" -DayOfWeek Sunday -ExecutionTime "03:00"
   ```
2. **Ciclo de Auto-Cura:**
   O script `infra\scheduled-lake-audit.ps1` roda semanalmente. Se encontrar divergência de SHA-256 (`sha256_divergente`, `origem_superada`, `sem_parquet`), ele aciona o módulo cirúrgico:
   ```powershell
   uv run python -m workers.cli ingest lake-heal --lake "F:\lake" --view "H:\data\vigente" --report-json "F:\lake\.build\reports\audit-weekly-latest.json"
   ```
   Reconstruindo com `force=True` estritamente os datasets retificados.

---

## 8. Esteira de Marts Analíticos DuckDB e Carga Atômica no Portal

Os 5 marts analíticos prioritários do Subplano 6 do Portal são calculados sobre o Lake local e publicados no PostgreSQL da VPS:

```bash
# Executado no Pendulograph (ou Linux com acesso ao lake):
infra/lake-marts.sh
```

Fluxo de Execução:
1. Abre um túnel SSH autenticado (`15433:5432`) com a VPS de produção;
2. DuckDB aloca 64 GB de RAM e executa os joins analíticos sobre `F:\lake` e as dimensões canônicas;
3. O resultado é carregado via COPY em tabelas temporárias `marts.<tabela>__new`;
4. Índices e constraints são criados na tabela temporária;
5. Uma transação atômica realiza o swap com a tabela de produção, garantindo zero indisponibilidade para os usuários do portal.
