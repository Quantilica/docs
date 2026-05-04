# Filosofia de Design

A Plataforma Brasileira de Dados Públicos é construída em cinco princípios centrais que orientam cada ferramenta, de sidra-fetcher a datasus-fetcher. Entender esses princípios ajuda você a usar as ferramentas efetivamente e estendê-las para suas próprias necessidades.

## 1. Modularidade

Cada ferramenta é **independente e auto-contida**. Você pode usar apenas o que precisa sem puxar dependências desnecessárias ou acoplamento.

### Por Que Importa

Fontes de dados governamentais brasileiros são diversas e fragmentadas. Forçar uma API única unificada sacrificaria as otimizações especializadas que cada ferramenta necessita.

- **sidra-fetcher** é otimizada para APIs REST IBGE com concorrência assíncrona
- **pdet-data** é otimizada para arquivos CSV massivos com processamento vetorial Polars
- **datasus-fetcher** é otimizada para infraestrutura FTP legada com crawling multithreaded

Cada ferramenta resolve seu desafio de infraestrutura específico. Misturá-las em um "mega-fetcher" monolítico as enfraqueceria todas.

### Como Aplicamos

- Sem dependências internas compartilhadas entre ferramentas
- Cada ferramenta tem sua própria lógica de retry, tratamento de erro e estratégia de caching
- Ferramentas são composáveis: combine sidra-fetcher + tddata + pdet-data em um único pipeline sem conflitos

### Exemplo: Usando Múltiplas Ferramentas

```python
import asyncio
from sidra_fetcher import AsyncSidraClient
from pdet_data.fetch import connect, fetch_rais
from tddata.analytics import calculate_portfolio_monthly_returns

# Three independent tools, zero coupling
async def multi_source_analysis():
    # 1. SIDRA metadata via async client
    async with AsyncSidraClient(timeout=60) as sidra:
        agregado = await sidra.get_agregado(1620)

    # 2. RAIS labor data via FTP
    ftp = connect()
    rais = fetch_rais(ftp, dest_dir="raw/rais")

    # 3. Treasury portfolio returns
    returns = calculate_portfolio_monthly_returns(my_transactions)

    return agregado, rais, returns
```

## 2. Performance

**Velocidade importa**. Todas as ferramentas são projetadas para velocidade em escala:

- Concorrência multithreaded onde aplicável (datasus-fetcher: speedup 6-10x)
- Async/await onde aplicável (sidra-fetcher: speedup 3x em harvest de metadata)
- Processamento vetorial onde aplicável (pdet-data: speedup 10x)
- Smart caching e verificações de idempotência (comexdown: speedup 57x em re-runs)
- Processamento streaming/chunked para arquivos grandes (comexdown: overhead de memória constante)
- Formatos de armazenamento colunares (Parquet: compressão 95%+ vs CSV)

### Por Que Importa

Quando você está processando datasets de mercado de trabalho 50M+ linhas ou baixando gigabytes de dados comerciais, performance não é luxo—é pré-requisito. Ferramentas legadas como Pandas esgotam memória. Downloads sequenciais levam semanas. Escolhas ruins aqui o trancam em infraestrutura lenta e cara.

### Como Aplicamos

Cada ferramenta é benchmarked. Métricas de performance são documentadas. Quando uma abordagem mais rápida existe, a usamos:

- **RAIS (50M linhas)**: Processamento vetorial Polars, não Pandas
- **Microdados DATASUS (100+ GB)**: Crawling concorrente multithreaded, não FTP sequencial
- **Títulos de Tesouro (100k+ transações)**: Fetches concorrentes assíncronos, não requisições sync
- **Siscomex (arquivos gigabyte)**: Chunks streaming, não buffering em memória

### Exemplo: Processamento Idempotente com HEAD + `Last-Modified`

```python
from pathlib import Path
import comexdown

# Primeira execução: transmite os CSVs do SECEX em chunks de 8 KiB
comexdown.get_year(Path("./DATA"), year=2023)

# Segunda execução: HEAD mostra Last-Modified == mtime local, GET é pulado inteiramente
comexdown.get_year(Path("./DATA"), year=2023)

# Re-execuções custam apenas um round-trip HEAD por arquivo quando nada mudou.
```

## 3. Resiliência

**Falhas acontecem**. Todas as ferramentas são projetadas para lidar com elas graciosamente.

### Por Que Importa

APIs governamentais caem. Servidores FTP expiram. Certificados SSL expiram. Conexões de rede caem. Infraestrutura legada é instável. Ferramentas que caem em falhas transitórias são inutilizáveis em produção.

### Como Aplicamos

- **Auto-retry com backoff exponencial**: Falhas transitórias são retentadas 3-5 vezes com delays crescentes
- **Smart resume**: Se um download falha a 70%, execuções subsequentes resumem daquele ponto, não do começo
- **Resiliência SSL**: Lidar graciosamente com certificados governamentais expirados/mal configurados (comexdown)
- **Idempotência baseada em tamanho**: Compare tamanho de arquivo remoto com arquivo local; pule se idêntico (datasus-fetcher)
- **Validação na fonte**: Detecte corrupção/truncamento imediatamente, não após transformação cara

### Exemplo: Auto-Retry em Falhas FTP Transitórias

```sh
# datasus-fetcher retenta cada arquivo até 3 vezes em erros FTP
# Se uma conexão cai, as outras threads continuam baixando.
datasus-fetcher data --data-dir ./data sim-do-cid10 \
    --start 2023 --end 2023 --threads 5
```

Internamente, cada thread `Fetcher` reconecta e retenta transferências falhadas sem abortar o batch.

### Exemplo: Idempotência Baseada em Tamanho

```sh
# Primeira execução: baixa tudo
datasus-fetcher data --data-dir ./data sim-do-cid10 --start 2023 --end 2023

# Re-execução após falha parcial: tamanho remoto é comparado ao tamanho local,
# e apenas arquivos faltando ou com mismatch são re-buscados.
datasus-fetcher data --data-dir ./data sim-do-cid10 --start 2023 --end 2023
```

## 4. Reprodutibilidade

**Toda transformação é determinística e auditável**. Você pode reexecutar qualquer pipeline a partir de dados brutos e obter resultados idênticos.

### Por Que Importa

Em pesquisa, finanças e saúde pública, reprodutibilidade é inegociável. Se você não consegue explicar exatamente quais dados foram buscados, transformados e armazenados, sua análise não vale nada.

### Como Aplicamos

- **Outputs versionados**: Cada download inclui metadados (timestamp, versão da fonte, versão do schema)
- **Ordenação determinística**: Resultados são sempre ordenados consistentemente; sem variação aleatória
- **Linhagem completa**: Rastreie quais arquivos brutos produziram quais arquivos Parquet
- **Trilhas de auditoria**: Registre cada passo de transformação; nunca descarte ou modifique dados silenciosamente
- **Extração de documentação**: Baixe layouts, PDFs e tabelas de lookup junto aos dados (datasus-fetcher)

### Exemplo: Outputs Versionados com Metadados

```sh
# Microdados + livros de códigos + tabelas de referência, cada um com nomes de arquivo datados
datasus-fetcher data --data-dir ./data sim-do-cid10 --start 2023 --end 2023
datasus-fetcher docs --data-dir ./docs sim
datasus-fetcher aux  --data-dir ./aux  sim
```

Cada `.dbc` baixado é nomeado como `dataset_uf_periodo_YYYYMMDD.dbc`, de modo que múltiplas revisões do DATASUS do mesmo período coexistem no disco. Use `datasus-fetcher archive` para mover versões antigas para fora da árvore ativa, preservando-as para auditoria.

### Exemplo: Linhagem Completa

```bash
# Raw RAIS .7z → typed Parquet
pdet-data fetch ./raw          # idempotent: skips files already on disk
pdet-data convert ./raw ./parquet
```

```python
# Capturar linhagem junto ao Parquet convertido
import json, hashlib, polars as pl
from datetime import datetime, timezone
from pathlib import Path

raw  = Path("raw/rais-vinculos/rais-vinculos_2023@20240410.7z")
out  = Path("parquet/rais-vinculos/2023.parquet")

lineage = {
    "input_file":  str(raw),
    "input_size":  raw.stat().st_size,
    "input_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
    "output_file": str(out),
    "output_size": out.stat().st_size,
    "row_count":   pl.scan_parquet(out).select(pl.len()).collect().item(),
    "processed_at": datetime.now(timezone.utc).isoformat(),
    "tool": "pdet_data.convert_rais",
}
out.with_suffix(".lineage.json").write_text(json.dumps(lineage, indent=2))
```

## 5. Sem Mágica

**Explícito é melhor que implícito**. Você deve entender quais dados estão sendo buscados, como são transformados e onde são armazenados.

### Por Que Importa

"Mágica" é tentadora para designers de API. "Apenas chame `fetch_all()` e funciona!" Mas quando algo quebra, a mágica invisível torna debugging impossível. Quando você precisa modificar comportamento, a mágica o impede.

Em engenharia de dados, transparência é crítica. Você precisa saber:

- Exatamente quais endpoints de API estão sendo chamados
- Quais linhas estão sendo filtradas ou transformadas
- Por que um pipeline succeeded ou falhou
- Como modificar comportamento para suas necessidades específicas

### Como Aplicamos

- **Sem conversões de tipo implícitas**: Strings de data permanecem strings até serem explicitamente convertidas
- **Sem filtragem silenciosa**: Se dados são descartados, é registrado e reversível
- **Concorrência explícita**: Especifique `num_workers=5` ao invés de auto-detectar contagem de CPU
- **Mensagens de erro claras**: Quando algo falha, a mensagem de erro lhe diz por quê e como corrigir
- **Código legível**: Algoritmos complexos (matching FIFO de lotes, Modified Dietz) são documentados com comentários

### Exemplo: Configuração Explícita

```sh
# ✅ Claro: cada flag é explícito
datasus-fetcher data \
    --data-dir ./data sim-do-cid10 \
    --start 2023 --end 2023 \
    --regions sp rj mg \
    --threads 5

# ❌ Implícito: padrões escondem o que realmente está sendo buscado
datasus-fetcher data --data-dir ./data    # todos os 113 datasets, ~320 GB
```

### Exemplo: Transformações Explícitas

```python
# ❌ Mágica: Dados perdidos são invisíveis
df_filtered = df.filter(lambda row: row["salary"] > 0)  # Silenciosamente descarta linhas

# ✅ Claro: Rastrear explicitamente o que foi filtrado e por quê
invalid_count = len(df.filter(pl.col("salary") <= 0))
df_filtered = df.filter(pl.col("salary") > 0)
print(f"Filtradas {invalid_count} linhas com salário ≤ 0")  # Você sabe o que aconteceu
```

### Exemplo: Mensagens de Erro Explícitas

```python
# ✅ Mensagem de erro clara
# "FTP connection timeout after 60 seconds.
#  Server: ftp.datasus.gov.br
#  Path: /dissemin/arquivos/SIM/
#  Tentando novamente (tentativa 2/5) com backoff de 2 segundos..."

# ❌ Mensagem de erro pouco clara
# "Error: Connection failed"
```

## Resumo

Esses cinco princípios funcionam juntos:

1. **Modularidade** deixa você escolher a ferramenta certa para sua fonte de dados
2. **Performance** significa que você pode lidar com datasets massivos do Brasil
3. **Resiliência** significa que seus pipelines funcionam apesar da instabilidade de infraestrutura
4. **Reprodutibilidade** significa que sua análise é auditável e reexecutável
5. **Sem Mágica** significa que você entende e consegue fazer troubleshoot de tudo

Quando você constrói em cima dessas ferramentas, siga os mesmos princípios em seu próprio código. O resultado é uma plataforma de dados que é rápida, confiável, transparente e mantenível.
