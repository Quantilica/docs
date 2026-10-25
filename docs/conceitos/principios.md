---
title: Princípios de design da Quantilica
description: Modularidade, resiliência, performance, reprodutibilidade e sem mágica — os cinco princípios que orientam cada ferramenta.
---

# Princípios de Design

O Ecossistema Quantilica é construído sobre cinco princípios que orientam cada ferramenta — de `sidra-fetcher` a `datasus-fetcher`. Entendê-los ajuda a usar as ferramentas com eficácia e a estendê-las para necessidades próprias.

> **Construa para o mundo real.** Dados governamentais são bagunçados. APIs são instáveis. Redes são lentas. Não assuma perfeição: trate falhas, valide dados, registre decisões. Torne usuários produtivos, não frustrados.

Os cinco princípios funcionam como um conjunto:

1. **[Modularidade](#modularidade)** — escolha a ferramenta certa para cada fonte sem dependências cruzadas.
2. **[Resiliência](#resiliência)** — pipelines funcionam apesar da instabilidade da infraestrutura.
3. **[Performance](#performance)** — datasets massivos são tratados com rapidez e baixa memória.
4. **[Reprodutibilidade](#reprodutibilidade)** — toda transformação é determinística e auditável.
5. **[Sem Mágica](#sem-mágica)** — o usuário entende, controla e consegue depurar tudo.

Cada seção termina com links para os [Padrões Práticos](padroes.md) que materializam o princípio em código.

---

## Modularidade

Cada ferramenta é **independente, auto-contida e reutilizável**. Você usa apenas o que precisa — sem dependências cruzadas, sem atualizações em cascata.

### Por quê?

Fontes de dados governamentais brasileiros são diversas e fragmentadas. Forçar uma API monolítica única sacrificaria as otimizações especializadas que cada fonte exige:

- `sidra-fetcher` é otimizada para a API REST do IBGE com concorrência assíncrona.
- `pdet-fetcher` é otimizada para CSVs massivos da RAIS/CAGED com processamento vetorial Polars.
- `datasus-fetcher` é otimizada para a infraestrutura FTP legada do DATASUS com crawling multithreaded.
- `comex-fetcher` é otimizada para arquivos GB do Siscomex com streaming chunked sem dependências externas.

Misturar tudo em um "mega-fetcher" enfraqueceria todas. Modularidade preserva a otimização local.

### Como aplicamos

| Fetcher | Dependências de runtime | Extra `analysis` |
|---|---|---|
| `sidra-fetcher` | `quantilica-core` | — |
| `tesouro-direto-fetcher` | `quantilica-core` | `altair`, `quantilica-analytics` |
| `pdet-fetcher` | `quantilica-core` | `polars` |
| `comex-fetcher` | `quantilica-core` | — |
| `datasus-fetcher` | `quantilica-core` | `polars`, `pyarrow`, `fastdbf`, `dbfread` |
| `inmet-fetcher` | `quantilica-core` | `polars`, `quantilica-analytics` |
| `rtn-fetcher` | `quantilica-core`, `beautifulsoup4`, `openpyxl` | `quantilica-analytics` |
| `bcb-sgs-fetcher` | `quantilica-core`, `httpx2`, `beautifulsoup4`, `lxml`, `markdownify` | — |

Nenhum fetcher depende de outro fetcher.

- Sem dependências internas compartilhadas entre ferramentas.
- Cada uma tem sua própria lógica de retry, tratamento de erro e estratégia de cache.
- Ferramentas são **composáveis**: combine `sidra-fetcher` + `tesouro-direto-fetcher` + `pdet-fetcher` no mesmo pipeline sem conflito.

### Exemplo: três fontes, zero acoplamento

```python
import asyncio
from sidra_fetcher.fetcher import AsyncSidraClient
from pathlib import Path
from tesouro_direto_fetcher.analytics import calculate_portfolio_monthly_returns

async def multi_source_analysis(my_transactions):
    # 1. SIDRA metadata via async client
    async with AsyncSidraClient(timeout=60) as sidra:
        agregado = await sidra.get_agregado(1620)

    # 2. RAIS: baixado antes pela CLI (quantilica pdet sync rais -o raw/rais) e lido de disco
    rais = Path("raw/rais")

    # 3. Tesouro portfolio returns
    returns = calculate_portfolio_monthly_returns(my_transactions)

    return agregado, rais, returns
```

> **Padrões relacionados:** [Use cada ferramenta isoladamente](padroes.md), [Composição em pipelines](padroes.md).

---

## Resiliência

**Falhas acontecem.** APIs governamentais caem, servidores FTP expiram, certificados SSL falham, conexões de rede abortam. Toda ferramenta é projetada para lidar com isso graciosamente — incluindo a integridade dos dados na origem.

### Por quê?

Infraestrutura legada é instável. Ferramentas que caem em falhas transitórias são inutilizáveis em produção. E perder dados silenciosamente é pior que falhar — uma análise sobre dados truncados produz conclusões erradas com aparência de corretude.

### Como aplicamos

- **Auto-retry com backoff exponencial**: falhas transitórias são retentadas (3 tentativas por padrão) com delays crescentes, via `quantilica.core.retry`.
- **Smart resume**: downloads HTTP interrompidos são retomados por `Range` a partir do arquivo parcial, em vez de recomeçar.
- **Resiliência SSL**: a verificação de certificado do `quantilica-core` é configurável (variável `QUANTILICA_SSL_VERIFY`), para lidar com certificados governamentais mal configurados.
- **Idempotência baseada em tamanho**: comparamos tamanho remoto vs. local; pulamos se idêntico (`datasus-fetcher`).
- **Validação na fonte**: detectamos corrupção/truncamento imediatamente, antes de transformações caras.
- **Tolerância a falha parcial**: continuamos com dados parciais (registrados), em vez de abortar tudo.

### Problemas e soluções

```
PROBLEMA                    SOLUÇÃO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
API timeout                 Retries automáticos com backoff exponencial
Falha de rede               Timeout configurável + recuperação de erro
Rate limiting (429)         Throttling integrado + delay
Resposta malformada         Validação + verificação de schema
API lenta                   Paginação em batch + opção async
Falha parcial               Continue com dados parciais (registrados)
Certificado SSL ruim        Configuração explícita (comex-fetcher)
Truncamento silencioso      Validação de tamanho/checksum na fonte
```

### Exemplo: retry automático

```python
from sidra_fetcher.fetcher import SidraClient

# tenacity faz 3 tentativas com backoff exponencial
with SidraClient(timeout=60) as client:
    agregado = client.get_agregado_metadados(1620)
    # Tentativa 1: timeout
    # Tentativa 2: timeout
    # Tentativa 3: sucesso ✓
```

### Exemplo: idempotência por tamanho

```sh
# Primeira execução: baixa tudo
quantilica datasus sync -o ./data sim-do-cid10 --start 2023 --end 2023

# Re-execução após falha parcial: tamanho remoto é comparado ao local;
# apenas arquivos faltantes ou com mismatch são re-buscados.
quantilica datasus sync -o ./data sim-do-cid10 --start 2023 --end 2023
```

### Filosofia de tratamento de erro

```python
# ❌ NÃO FAÇA: descartar dados silenciosamente
try:
    data = fetch_data()
except Exception:
    return pd.DataFrame()  # Resultado vazio = falha silenciosa

# ✅ FAÇA: registre e deixe o usuário decidir
try:
    data = fetch_data()
except TemporaryFailure as e:
    logger.warning(f"Falha temporária: {e}, tentando novamente...")
    # auto-retry roda aqui
except PermanentFailure as e:
    logger.error(f"Não pode recuperar: {e}")
    raise
```

> **Padrões relacionados:** [Auto-retry com backoff](padroes.md), [Validação de dados](padroes.md), [Idempotência por checksum/tamanho](padroes.md).

---

## Performance

Datasets brasileiros são **grandes**. Quando você está processando 50M+ linhas da RAIS ou GBs do Siscomex, performance não é luxo — é pré-requisito. Ferramentas legadas como Pandas esgotam memória; downloads sequenciais levam semanas.

### Por quê?

Escolhas ruins aqui prendem você em infraestrutura lenta e cara. Toda ferramenta é benchmarked, e quando uma abordagem mais rápida existe, é ela que usamos.

### Como aplicamos

- **Concorrência multithreaded** onde aplicável (`datasus-fetcher`).
- **Async/await** onde aplicável (`sidra-fetcher`, na coleta de metadados).
- **Processamento vetorial Polars** onde aplicável (`pdet-fetcher`).
- **Cache + verificações de idempotência** (`comex-fetcher`: re-runs sem mudança custam uma consulta ao remoto por arquivo).
- **Streaming/chunked** para arquivos grandes (`comex-fetcher`, em chunks de 64 KiB).
- **Formatos colunares** (Parquet comprime muito mais que CSV).

### Volumes típicos

Compressão típica: 80-90% vs. CSV (ordem de grandeza ilustrativa). Volumes completos em [Parquet + Polars](parquet-polars.md#por-que-parquet).

### Exemplo: lazy evaluation com Polars

```python
import polars as pl

# Eager (Pandas tradicional): carrega tudo, depois filtra
df = pd.read_csv("huge_file.csv")        # 10s
result = df[df["state"] == "SP"]         # +5s

# Lazy (Polars): otimiza plano antes de executar
df = pl.scan_csv("huge_file.csv")
result = df.filter(pl.col("state") == "SP").collect()
# Polars empurra o filtro para a leitura → lê só linhas correspondentes
# Total: ~1s
```

### Exemplo: idempotência com `HEAD` + `Last-Modified`

```bash
# Primeira execução: baixa os CSVs do SECEX em streaming
quantilica comex sync trade-exp -o ./DATA

# Segunda execução: o remoto é consultado e, se tamanho e Last-Modified não mudaram, o arquivo é pulado
quantilica comex sync trade-exp -o ./DATA
# Re-execuções custam apenas uma consulta ao remoto por arquivo quando nada mudou.
```

> **Padrões relacionados:** [Lazy evaluation](padroes.md), [Concorrência explícita](padroes.md), [Streaming chunked](padroes.md), [Parquet em vez de CSV](padroes.md).

---

## Reprodutibilidade

**Toda transformação é determinística e auditável.** Você pode reexecutar qualquer pipeline a partir de dados brutos e obter resultados idênticos.

### Por quê?

Em pesquisa, finanças e saúde pública, reprodutibilidade é inegociável. Se você não consegue explicar exatamente quais dados foram buscados, transformados e armazenados, sua análise não vale nada. E cenários típicos — re-rodar um modelo meses depois e obter saída diferente — tornam debug impossível: foi o código? Foram os dados? Sem versionamento, ninguém sabe.

### Como aplicamos

- **Outputs versionados**: cada download inclui metadados (timestamp, versão da fonte, schema).
- **Ordenação determinística**: resultados sempre ordenados de forma consistente.
- **Linhagem completa**: rastreamos quais arquivos brutos produziram quais Parquet.
- **Trilhas de auditoria**: cada transformação é registrada; nada é descartado silenciosamente.
- **Documentação extraída na fonte**: layouts, PDFs e tabelas de lookup baixados junto aos dados (`datasus-fetcher`).
- **Idempotência**: operações são seguras para re-executar — `write_parquet()` sobrescreve previsivelmente; nunca usamos append cego.

### Exemplo: outputs versionados com nome datado

```sh
# Microdados + livros de códigos + tabelas de referência
quantilica datasus sync -o ./data sim-do-cid10 --start 2023 --end 2023 --docs --aux
```

Cada `.dbc` baixado é nomeado `{dataset}_{AAAAMM}-{uf}@{AAAAMMDD}.dbc`, então múltiplas revisões do DATASUS coexistem no disco. `datasus-fetcher archive` move versões antigas para auditoria.

### Exemplo: linhagem completa em JSON

```python
import json, hashlib, polars as pl
from datetime import datetime, timezone
from pathlib import Path

raw = Path("raw/rais-vinculos/rais-vinculos_2023@20240410.7z")
out = Path("parquet/rais-vinculos/2023.parquet")

lineage = {
    "input_file":   str(raw),
    "input_size":   raw.stat().st_size,
    "input_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
    "output_file":  str(out),
    "output_size":  out.stat().st_size,
    "row_count":    pl.scan_parquet(out).select(pl.len()).collect().item(),
    "processed_at": datetime.now(timezone.utc).isoformat(),
    "tool":         "pdet_fetcher.convert_rais",
}
out.with_suffix(".lineage.json").write_text(json.dumps(lineage, indent=2))
```

### Exemplo: idempotência segura

```python
# ✅ Seguro re-executar — sobrescreve previsivelmente
df.write_parquet("output.parquet")

# ❌ Perigoso — acumula duplicatas sem controle
# (Polars não tem write_parquet com append; o padrão abaixo simula o risco)
existing = pl.read_parquet("output.parquet")
pl.concat([existing, df]).write_parquet("output.parquet")  # sem deduplication

# ✅ Quando precisa acumular: deduplique explicitamente
combined = pl.concat([existing, df]).unique()
combined.write_parquet("output.parquet")
```

> **Padrões relacionados:** [Linhagem em JSON](padroes.md), [Versionamento por timestamp](padroes.md), [Documentação como código](padroes.md).

---

## Sem Mágica

**Explícito é melhor que implícito.** Você deve entender quais dados estão sendo buscados, como são transformados, onde são armazenados — e ter controle direto sobre tudo isso.

### Por quê?

"Mágica" é tentadora para designers de API: "apenas chame `fetch_all()` e funciona!" Mas quando algo quebra, mágica invisível torna debug impossível. Quando você precisa modificar comportamento, mágica te bloqueia. E em engenharia de dados, transparência é crítica — você precisa saber:

- Quais endpoints estão sendo chamados.
- Quais linhas estão sendo filtradas ou transformadas.
- Por que um pipeline teve sucesso ou falhou.
- Como adaptar o comportamento para suas necessidades específicas.

Por isso, **usuários — não bibliotecas — decidem o que fazer com os dados**.

### Como aplicamos

- **Sem conversões implícitas**: strings de data permanecem strings até serem explicitamente convertidas.
- **Sem filtragem silenciosa**: se dados são descartados, é registrado e reversível.
- **Concorrência explícita**: `num_workers=5`, não auto-detect de CPU.
- **Mensagens de erro acionáveis**: dizem por que falhou e como corrigir.
- **Output controlado pelo usuário**: você escolhe formato (Parquet, CSV, PostgreSQL) e destino — a biblioteca não assume.
- **Conjunto pequeno e visível de botões**: clientes expõem opções nomeadas, não comportamento mágico.
- **Algoritmos complexos documentados** (matching FIFO de lotes, Modified Dietz) com comentários inline.

### Anti-padrão vs. padrão

```python
# ❌ Mágica: suposições silenciosas
df = fetch_gdp()  # De onde? Atualizado quando? Cacheado?
                  # E se falhar? E se não houver dados?

# ✅ Explícito: cada parâmetro é nomeado e visível
import polars as pl
from sidra_fetcher.fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao

param = Parametro(
    agregado="1620",                            # Tabela de PIB
    territorios={"1": ["all"]},                 # Total Brasil
    variaveis=["116"],                          # PIB Real
    periodos=["202001", "202002", "202003", "202004"],
    classificacoes={},
    formato=Formato.A,
    decimais={"": Precisao.M},
)

with SidraClient(timeout=60) as client:
    rows = client.get(param.url())

if not rows:
    raise ValueError("Sem dados retornados do IBGE")

gdp = pl.DataFrame(rows)
gdp.write_parquet("gdp_data.parquet")
print(f"Salvas {len(gdp)} observações em gdp_data.parquet")
```

### Anti-padrão vs. padrão (output)

```python
# ❌ Biblioteca decide
gdp.save()                  # Onde? Qual formato? Sobrescrever?

# ✅ Usuário decide
gdp.write_parquet("gdp.parquet")
gdp.write_csv("gdp.csv")
gdp.write_database("gdp_table", connection="postgresql://...")
```

### Filtragem explícita

```python
# ❌ Mágica: dados descartados são invisíveis
df_filtered = df.filter(lambda row: row["salary"] > 0)

# ✅ Explícito: registre o que foi filtrado e por quê
invalid_count = len(df.filter(pl.col("salary") <= 0))
df_filtered = df.filter(pl.col("salary") > 0)
print(f"Filtradas {invalid_count} linhas com salário ≤ 0")
```

### Mensagens de erro

```
# ✅ Claro
FTP connection timeout after 60 seconds.
  Server: ftp.datasus.gov.br
  Path: /dissemin/arquivos/SIM/
  Tentativa 2/5 com backoff de 2 segundos...

# ❌ Inútil
Error: Connection failed
```

### Checklist de transparência

Antes de rodar qualquer pipeline, você deve conseguir responder:

- [ ] **O quê** — quais dados estão sendo buscados?
- [ ] **Onde** — qual API/banco/arquivo?
- [ ] **Quando** — qual intervalo temporal?
- [ ] **Quanto** — quantas linhas?
- [ ] **Falhas** — o que acontece se a API cair?
- [ ] **Output** — para onde vai o resultado?
- [ ] **Formato** — Parquet, CSV, banco?

> **Padrões relacionados:** [Configuração explícita](padroes.md), [Filtragem rastreável](padroes.md), [Mensagens de erro acionáveis](padroes.md), [Documente seu pipeline](padroes.md).

---

## Como estes princípios se compõem

Os princípios não são independentes — reforçam-se mutuamente:

- **Modularidade** + **Resiliência**: cada ferramenta tem sua própria lógica de retry adequada à sua infraestrutura.
- **Performance** + **Reprodutibilidade**: Parquet é rápido *e* preserva schema para auditoria.
- **Sem Mágica** + **Resiliência**: erros explícitos permitem o usuário decidir como reagir.
- **Reprodutibilidade** + **Sem Mágica**: linhagem em JSON é rastreabilidade *e* transparência.

Quando você constrói em cima destas ferramentas, siga os mesmos princípios em seu código. O resultado é um ecossistema de dados rápido, confiável, transparente e mantenível.

---

## Saiba mais

- [Arquitetura do Ecossistema](arquitetura.md) — como os componentes se conectam.
- [Padrões Práticos](padroes.md) — as receitas táticas que materializam estes princípios em código.
- [Parquet + Polars](parquet-polars.md) — o tutorial específico sobre o formato/biblioteca centrais.
