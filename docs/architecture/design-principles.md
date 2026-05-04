# Princípios de Design

Princípios centrais orientando a Plataforma Brasileira de Dados Públicos.

## 1. Modularidade

Cada ferramenta é **independente**, **auto-contida** e **reutilizável**.

### Por Que Modularidade?

- **Escolha o que precisa**: Use apenas as ferramentas relevantes para sua análise
- **Evite dependency hell**: Sem atualizações em cascata quebrando tudo
- **Fácil testar**: Cada ferramenta pode ser testada independentemente
- **Fácil substituir**: Pode trocar uma ferramenta por outra sem reescrever pipelines

### Como Conseguimos

```
sidra-fetcher       tddata               pdet-data            comexdown
├─ httpx, tenacity  ├─ httpx, tqdm       ├─ polars, tqdm      ├─ stdlib only
└─ no cross-deps    └─ no cross-deps     └─ no cross-deps     └─ no cross-deps

datasus-fetcher        inmet-bdmep-data
├─ stdlib only         ├─ httpx, pandas, pyarrow
└─ no cross-deps       └─ no cross-deps

Use APENAS sidra-fetcher sem tocar tddata ou comexdown.
```

### Exemplo: Dois Analistas, Mesma Plataforma, Ferramentas Diferentes

```python
from pathlib import Path

# Economista A: apenas precisa de metadados SIDRA
from sidra_fetcher import SidraClient
with SidraClient() as client:
    agregado = client.get_agregado_metadados(1620)

# Economista B: apenas precisa de dados de mercado de trabalho
from pdet_data import connect, fetch_rais
ftp = connect()
try:
    fetch_rais(ftp=ftp, dest_dir=Path("raw/rais"))
finally:
    ftp.close()

# Economista C: SIDRA + comércio
import comexdown
comexdown.get_year(Path("./DATA"), year=2023)
# Cada ferramenta mantém seu próprio padrão de acesso; sem abstração compartilhada necessária.
```

## 2. Resiliência

Infraestrutura governamental é **imperfeita**. Lidamos com falhas graciosamente.

### Problemas que Abordamos

```
PROBLEMA                    SOLUÇÃO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
API timeout                 Retries automáticos com backoff
Falha de rede               Timeout configurável + recuperação de erro
Rate limiting (429)         Throttling integrado + delay
Resposta malformada         Validação + verificação de schema
API lenta                   Batch de paginação + opção async
Falha parcial               Continue com dados parciais (registrados)
```

### Exemplo de Lógica de Retry

```python
from sidra_fetcher import SidraClient

# SidraClient faz retry em métodos de metadados automaticamente via tenacity
# (3 tentativas; backoff exponencial em get_agregado_periodos)
with SidraClient(timeout=60) as client:
    agregado = client.get_agregado_metadados(1620)
    # Tentativa 1: timeout
    # Tentativa 2: timeout
    # Tentativa 3: sucesso ✓
```

### Filosofia de Error Handling

```python
# NÃO FAÇA: Descartar dados silenciosamente
try:
    data = fetch_data()
except Exception:
    return pd.DataFrame()  # Resultado vazio = falha silenciosa ❌

# FAÇA: Log a falha, deixe o usuário decidir
try:
    data = fetch_data()
except TemporaryFailure as e:
    logger.warning(f"Falha temporária: {e}, tentando novamente...")
    # Auto-retry acontece aqui
except PermanentFailure as e:
    logger.error(f"Não pode recuperar: {e}")
    raise  # Usuário trata ✓
```

## 3. Performance

Datasets brasileiros são **grandes**. Otimizamos para velocidade e memória.

### Armazenamento: Parquet vs CSV

```
CSV: 850 MB
Parquet: 100 MB (12% do tamanho CSV)
↓
Carregamento rápido + uso baixo de disco

Também: Estrutura colunar = consultas analíticas rápidas
```

### Otimização de Consultas: Lazy Evaluation

```python
# Eager (tradicional): Carregar tudo, depois filtrar
df = pd.read_csv("huge_file.csv")  # 10 segundos
result = df[df["state"] == "SP"]   # 5 segundos mais

# Lazy (Polars): Otimizar plano de consulta primeiro
df = pl.scan_csv("huge_file.csv")
result = df.filter(pl.col("state") == "SP").collect()
# Polars: Empurrar filtro → ler apenas linhas correspondentes
# ↓ 1 segundo total
```

### Streaming para Arquivos Grandes

```python
# Processar arquivos grandes em batches, não tudo-de-uma-vez

import polars as pl

reader = pl.read_parquet("rais_2023.parquet")

batch_size = 100_000
for i in range(0, len(reader), batch_size):
    batch = reader[i:i+batch_size]
    # Processar este batch
    result = batch.group_by("sector").agg(...)
    # Salvar resultado intermediário
```

## 4. Reprodutibilidade

Todas as transformações são **determinísticas**. Mesma entrada = mesma saída, sempre.

### Por Que Reprodutibilidade Importa

```
Cenário: Construir um modelo com dados de PIB 2023
↓
Deploy do modelo para produção
↓
Depois: Executar modelo novamente nos mesmos dados
↓
Resultado: Saída diferente (porque dados mudaram)
↓
Problema: Não consegue debugar (código quebrado? Dados mudaram?)

Solução: Versioná tudo
```

### Melhores Práticas

```python
from datetime import datetime

# 1. Versionar seus dados
gdp_file = f"data/gdp_{datetime.now():%Y_%m_%d}.parquet"

# 2. Log source e time
data_metadata = {
    "source": "Tabela IBGE SIDRA 1620, variável 116",
    "fetch_date": "2024-01-15T14:32:00Z",
    "rows": 348,
    "date_range": ["2000-01-01", "2024-10-01"],
    "crc32": "0x1a2b3c4d"  # Checksum
}

# 3. Documentar transformações
"""
Pipeline:
1. Buscar do IBGE SIDRA
2. Normalizar datas para formato ISO
3. Casting de tipo (string → float)
4. Remover valores faltantes (status="." → None)
5. Salvar em Parquet
"""

# 4. Fazer operações idempotentes
# (Seguro executar novamente sem efeitos colaterais)
df.write_parquet("output.parquet")  # Sobrescreve OK
# vs
df.write_parquet("output_append.parquet", append=True)  # Risco: duplicatas
```

## 5. Sem Mágica

**Explícito é melhor que implícito.**

### Anti-Padrão: Mágica Acontece Invisível

```python
# Ruim: Suposições silenciosas
df = fetch_gdp()  # De onde? Atualizado quando? Cacheado?
# E se API falha? E se sem dados?
# Usuário não sabe.
```

### Padrão: Explícito Tudo

```python
import polars as pl
from sidra_fetcher import SidraClient
from sidra_fetcher.sidra import Parametro, Formato, Precisao

# Bom: todo parâmetro é nomeado e visível
param = Parametro(
    agregado="1620",                      # Tabela de PIB
    territorios={"1": ["all"]},           # Total Brasil
    variaveis=["116"],                    # PIB Real
    periodos=["202001", "202002", "202003", "202004"],
    classificacoes={},
    formato=Formato.A,
    decimais={"": Precisao.M},
)

with SidraClient(timeout=60) as client:
    rows = client.get(param.url())

# Tratamento de falha explícito
if not rows:
    raise ValueError("Sem dados retornados do IBGE")

# Output explícito
gdp = pl.DataFrame(rows)
gdp.write_parquet("gdp_data.parquet")
print(f"Salvos {len(gdp)} observações de PIB em gdp_data.parquet")
```

### Checklist de Transparência

- [ ] **O quê**: Quais dados estão sendo buscados?
- [ ] **Onde**: Qual API/banco de dados/arquivo?
- [ ] **Quando**: Qual intervalo de datas?
- [ ] **Quanto**: Quantas linhas?
- [ ] **Falhas**: O que acontece se API falha?
- [ ] **Output**: Para onde vai resultado?
- [ ] **Formato**: Qual formato (Parquet/CSV/Banco de dados)?

## 6. Controle do Usuário

Usuários, não bibliotecas, decidem **o que fazer com dados**.

### Anti-Padrão: Biblioteca Decide

```python
# Ruim: Biblioteca faz suposições
gdp.save()  # Onde? Qual formato? Sobrescrever?

# Ruim: Opções limitadas
client.fetch(cache=True)  # Não pode controlar localização cache
```

### Padrão: Usuário Decide

```python
# Bom: usuário escolhe formato de output e destino
gdp.write_parquet("gdp.parquet")
gdp.write_csv("gdp.csv")
gdp.write_database("gdp_table", connection="postgresql://...")

# Bom: client expõe conjunto de botões pequeno e explícito
client = SidraClient(timeout=120)
```

## 7. Integridade de Dados

**Nunca perca dados silenciosamente.**

### Verificações de Validação

```python
# Check 1: Validação de schema
expected_columns = {"date", "value", "status_code"}
actual_columns = set(df.columns)
assert expected_columns.issubset(actual_columns)

# Check 2: Sem nulos inesperados
null_rate = df["value"].is_null().sum() / len(df)
if null_rate > 0.10:
    logger.warning(f"Taxa alta de nulos: {null_rate*100:.1f}%")

# Check 3: Cobertura de datas
first_date = df["date"].min()
last_date = df["date"].max()
expected_rows = (last_date - first_date).days / 90  # Trimestral

if len(df) < expected_rows * 0.8:
    logger.warning(f"Possível dados faltantes (esperado ~{expected_rows}, obtido {len(df)})")
```

### Idempotência

Operações devem ser seguras para re-executar:

```python
# Seguro para re-executar
df.write_parquet("output.parquet")  # Sobrescreve ✓

# Perigoso para re-executar
df.write_parquet("output.parquet", append=True)
# Segunda execução = duplicatas ❌

# Melhor: Com deduplicação
combined = pl.concat([existing, new])
combined.unique().write_parquet("output.parquet")
```

## Matriz de Decisão

### Quando Usar Cada Ferramenta

| Necessidade | Ferramenta |
|------|------|
| Dados macroeconômicos IBGE | sidra-fetcher |
| Títulos do governo brasileiro | tddata |
| Emprego & mercado de trabalho | pdet-data |
| Fluxos de comércio (import/export) | comexdown |
| Dados vigilância de saúde | datasus-fetcher |
| Processamento de arquivos grandes | Polars |
| Análise estatística | Pandas / NumPy / Statsmodels |
| Dashboarding | PostgreSQL + ferramenta BI |
| Previsão de séries temporais | Prophet / ARIMA / ML |

## Checklist de Implementação

Ao construir ferramentas para este suite:

- [ ] **Modularidade**: Sem dependências desnecessárias em outras ferramentas
- [ ] **Error handling**: Tipos específicos de erro, mensagens acionáveis
- [ ] **Retries**: Lidar com falhas transitórias graciosamente
- [ ] **Validação**: Verificar schema de dados e integridade
- [ ] **Logging**: Output amigável para debug
- [ ] **Performance**: Otimizar para datasets grandes
- [ ] **Testing**: Testes unitários + integração abrangentes
- [ ] **Documentation**: Exemplos claros e docs de API
- [ ] **Backwards compatibility**: Não quebrar código existente
- [ ] **Reproducibility**: Output determinístico

## Filosofia

> **Construa para o mundo real.**
>
> Dados governamentais são bagunçados. APIs são não confiáveis. Redes são lentas.
>
> Não assuma perfeição. Trate falhas. Valide dados. Log decisões.
>
> Torne usuários produtivos, não frustrados.

---

## Saiba Mais

- [Architecture Overview](overview.md)
- [Concepts - Data Engineering](../concepts/data-engineering.md)
