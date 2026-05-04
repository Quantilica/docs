# Guia de Retornos de Portfólio e Duration

Calcule retornos, YTM e sensibilidade de taxa de juros para portfólios de renda fixa.

## Conceitos Principais

### Yield to Maturity (YTM)

Retorno anual se o título for mantido até o vencimento. Contabiliza:

- Preço de mercado atual
- Pagamentos de cupons
- Reembolso de principal no vencimento
- Reinvestimento no mesmo yield

$$
\text{Preço} = \sum_{t=1}^{T} \frac{\text{Cupom}}{(1 + \text{YTM})^t} + \frac{\text{Principal}}{(1 + \text{YTM})^T}
$$

Para títulos brasileiros, YTM já é fornecido por **tddata**.

### Duration Modificada

Medida de sensibilidade de preço do título a mudanças em taxas de juros:

$$
D_{\text{modificada}} = \frac{D_{\text{macaulay}}}{1 + \text{YTM}}
$$

**Regra de ouro:** Aumento de 1% no yield → queda de $D_{\text{modificada}}$% no preço

Exemplo: Título de 5 anos com duration de 5 anos:

- Yield aumenta 1% → Preço cai ~5%
- Yield cai 1% → Preço sobe ~5%

### Juros Acumulados

Juros ganhos desde a última data de cupom mas ainda não pagos:

$$
\text{Acumulados} = \text{Cupom} \times \frac{\text{Dias desde último cupom}}{\text{Dias no período de cupom}}
$$

**Preço clean**: Preço do título cotado (ex-acumulado)

**Preço dirty**: Preço clean + juros acumulados = o que você realmente paga

### Retorno Real (Indexado ao IPCA)

Para títulos NTN-B, separe o yield nominal em componentes:

$$
\text{Yield Nominal} = \text{Yield Real} + \text{Expectativa de Inflação}
$$

Exemplo:

- Yield NTN-B: 5.0%
- IPCA esperado: 3.5%
- Yield real implícito: 1.5%

## Cálculos Rápidos

### Holding de Título Único

```python
import polars as pl
from datetime import date
from pathlib import Path
from tddata import reader
from tddata.constants import Column as C, BondType

# Ler CSV de preços baixado com `tddata download --dataset prices`
prices = reader.read_prices(next(Path("./data").glob("taxas-dos-titulos*.csv")))

# Escolher um título: NTN-B (Tesouro IPCA+ com Juros Semestrais) vencendo 2027-05-15
bond = prices.filter(
    (pl.col(C.BOND_TYPE.value) == BondType.NTNB.value)
    & (pl.col(C.MATURITY_DATE.value) == date(2027, 5, 15))
).sort(C.REFERENCE_DATE.value).tail(1).row(0, named=True)

face_value = 1000.0
purchase_price = bond[C.BUY_PRICE.value]   # ask atual, em BRL
ytm_pct        = bond[C.BUY_YIELD.value]   # já em percentual no CSV

print(f"Preço de compra: R${purchase_price:,.2f}")
print(f"YTM anual:       {ytm_pct:.2f}%")
```

### Yield Médio Ponderado de Portfólio

```python
import polars as pl

# Portfólio
portfolio = pl.DataFrame({
    "bond_name": ["LTN_2025", "NTN-B_2027", "LFT_2026"],
    "quantity": [100, 50, 75],  # Unidades detidas
    "current_price": [97.50, 105.25, 100.10],  # Preço clean
    "ytm": [9.5, 5.8, 10.6]  # YTM anual %
})

# Calcular valor do portfólio e yield ponderado
portfolio = portfolio.with_columns([
    (pl.col("quantity") * pl.col("current_price")).alias("market_value")
])

total_value = portfolio["market_value"].sum()
portfolio_ytm = (
    (portfolio["market_value"] * portfolio["ytm"]).sum() / total_value
)

print(f"Valor total do portfólio: R${total_value:,.2f}")
print(f"YTM do portfólio: {portfolio_ytm:.2f}%")

# Mostrar alocação
portfolio = portfolio.with_columns([
    (pl.col("market_value") / total_value * 100).alias("allocation_%")
])
print(portfolio.select(["bond_name", "allocation_%"]))
```

### Duration de Portfólio (Risco de Taxa de Juros)

```python
import polars as pl

# Portfólio com dados de duration
portfolio = pl.DataFrame({
    "bond_name": ["LTN_2025", "NTN-B_2027", "LFT_2026"],
    "market_value": [97500, 52625, 75075],  # Valor total em Reais
    "duration": [0.9, 4.5, 1.2]  # Duration modificada em anos
})

# Calcular duration do portfólio
total_value = portfolio["market_value"].sum()
portfolio_duration = (
    (portfolio["market_value"] * portfolio["duration"]).sum() / total_value
)

print(f"Duration do portfólio: {portfolio_duration:.2f} anos")
print(f"Se yields subirem 1%, portfólio perde ~{portfolio_duration:.2f}%")
print(f"Se yields caírem 1%, portfólio ganha ~{portfolio_duration:.2f}%")

# Mostrar duration por posição
portfolio = portfolio.with_columns([
    (pl.col("market_value") / total_value * 100).alias("weight_%"),
    (pl.col("duration") * pl.col("market_value") / total_value).alias("duration_contribution")
])

print(portfolio.select(["bond_name", "weight_%", "duration", "duration_contribution"]))
```

### Análise de Choque de Taxa

Como o portfólio se sai se yields mudam?

```python
import polars as pl

bonds = pl.DataFrame({
    "name": ["LTN_2025", "NTN-B_2027"],
    "clean_price": [97.50, 105.25],
    "quantity": [100, 50],
    "duration": [0.9, 4.5],
    "ytm": [9.5, 5.8]
})

# Valor de mercado atual
bonds = bonds.with_columns([
    (pl.col("clean_price") * pl.col("quantity")).alias("market_value")
])

current_value = bonds["market_value"].sum()

# Calcular impacto de preço das mudanças de yield usando duration
# Preço novo ≈ Preço antigo - Duration × Preço × ΔYield
yield_changes = [-1.0, -0.5, 0.0, 0.5, 1.0]  # Pontos percentuais

print(f"Valor atual do portfólio: R${current_value:,.2f}\n")
print("Mudança de yield | Novo valor | P&L")
print("-" * 40)

for dy in yield_changes:
    new_price = bonds.with_columns([
        (pl.col("clean_price") * (1 - pl.col("duration") * dy / 100)).alias("new_price")
    ])
    new_value = (new_price["new_price"] * new_price["quantity"]).sum()
    pnl = new_value - current_value
    
    print(f"{dy:+.1f}% | R${new_value:,.0f} | R${pnl:+,.0f}")
```

## Precificação de Títulos

### Preço Clean vs. Preço Dirty

```python
import polars as pl

bond = pl.DataFrame({
    "bond": ["NTN-B_2027"],
    "clean_price": [105.25],
    "accrued_interest": [1.45],  # Do último cupom
    "quantity": [50]
})

# Calcular custo total
bond = bond.with_columns([
    pl.col("clean_price") + pl.col("accrued_interest"),
    (
        (pl.col("clean_price") + pl.col("accrued_interest")) *
        pl.col("quantity") / 100
    ).alias("total_cost")
])

print(f"Preço clean: R${bond['clean_price'][0]}")
print(f"Juros acumulados: R${bond['accrued_interest'][0]}")
print(f"Preço dirty: R${bond['clean_price'][0] + bond['accrued_interest'][0]}")
print(f"Custo total para {bond['quantity'][0]} unidades: R${bond['total_cost'][0]:,.2f}")
```

## Cálculo de Retorno Real (Títulos Indexados ao IPCA)

### Método 1: Usando YTM Fornecido

```python
import polars as pl

# NTN-B com YTM e inflação realizada
bonds = pl.DataFrame({
    "date": ["2023-01-01", "2024-01-01"],
    "yield": [5.8, 6.2],  # Yield nominal %
    "ipca_realized": [10.1, 4.5]  # IPCA realizado %
})

# Retorno real = (1 + Nominal) / (1 + Inflação) - 1
bonds = bonds.with_columns([
    (
        ((1 + pl.col("yield") / 100) / (1 + pl.col("ipca_realized") / 100)) - 1
    ).alias("real_return")
])

print(bonds.select(["date", "yield", "ipca_realized", "real_return"]))
```

### Método 2: Inflação de Equilíbrio

Qual taxa de inflação deixa indiferente entre prefixado e indexado ao IPCA?

```python
# LTN (prefixado) yield
ltn_yield = 0.095  # 9.5%

# NTN-B (indexado ao IPCA) yield
ntb_yield = 0.058  # 5.8%

# Inflação de equilíbrio = (1 + yield LTN) / (1 + yield NTN-B) - 1
breakeven = ((1 + ltn_yield) / (1 + ntb_yield)) - 1

print(f"Yield LTN: {ltn_yield*100:.1f}%")
print(f"Yield NTN-B: {ntb_yield*100:.1f}%")
print(f"Mercado espera inflação: {breakeven*100:.1f}%")
```

## Pipeline de Produção

### Script de Atualização Diária

```python
import asyncio
import polars as pl
from pathlib import Path
from tddata import downloader, reader
from tddata.constants import Column as C

data_dir = Path("data/treasury")
data_dir.mkdir(parents=True, exist_ok=True)

# 1. Buscar CSV de preços mais recente (idempotente em Last-Modified)
asyncio.run(
    downloader.download(
        data_dir,
        dataset_id="taxas-dos-titulos-ofertados-pelo-tesouro-direto",
        max_concurrency=3,
    )
)

# 2. Ler CSV mais novo
latest_csv = max(data_dir.glob("taxas-dos-titulos*.csv"), key=lambda p: p.stat().st_mtime)
prices = reader.read_prices(latest_csv)

# 3. Anexar ao histórico em execução (dedup por reference_date + bond_type + maturity)
history_file = data_dir / "prices_history.parquet"
if history_file.exists():
    existing = pl.read_parquet(history_file)
    prices = pl.concat([existing, prices]).unique(
        subset=[C.REFERENCE_DATE.value, C.BOND_TYPE.value, C.MATURITY_DATE.value]
    )

prices.write_parquet(history_file)

# 4. Snapshot da data de referência mais recente
latest_date = prices[C.REFERENCE_DATE.value].max()
latest = prices.filter(pl.col(C.REFERENCE_DATE.value) == latest_date)
latest.write_parquet(data_dir / "latest_snapshot.parquet")

print(f"Atualizado {prices.height:,} linhas; data de referência mais recente {latest_date}")

# 5. Agregados por tipo de título
metrics = (
    latest.group_by(C.BOND_TYPE.value)
    .agg(
        avg_buy_yield=pl.col(C.BUY_YIELD.value).mean(),
        avg_buy_price=pl.col(C.BUY_PRICE.value).mean(),
        n_maturities=pl.col(C.MATURITY_DATE.value).n_unique(),
    )
)
metrics.write_parquet(data_dir / "portfolio_metrics.parquet")
```

### Métricas de Dashboard de Monitoramento

```python
import polars as pl
from datetime import datetime

# Carregar dados mais recentes
bonds = pl.read_parquet("data/treasury/latest_snapshot.parquet")

# Métricas-chave por tipo de título
metrics = bonds.group_by("bond_type").agg([
    pl.col("yield").mean().alias("avg_ytm"),
    pl.col("duration").mean().alias("avg_duration"),
    pl.col("volume").sum().alias("total_volume"),
    pl.col("bond_id").count().alias("num_bonds")
]).sort("bond_type")

print(f"Dashboard Tesouro - {datetime.now().strftime('%Y-%m-%d')}\n")
print(metrics)

# Curva de yield (exemplo NTN-B)
ntb = bonds.filter(pl.col("bond_type") == "NTN-B").sort("maturity_date")
print("\nCurva de Yield NTN-B:")
print(ntb.select(["maturity_date", "yield", "duration"]))
```

## Armadilhas Comuns

### Erro 1: Confundir Preço Clean com Preço Dirty

Sempre lembre: **você paga preço dirty** mas cotações de títulos são preço clean.

```python
# Errado: Comprando 50 títulos cotados em 105.25
cost = 50 * 105.25 * 10  # Errado: não inclui juros acumulados

# Certo: Adicionar juros acumulados
cost = 50 * (105.25 + 1.45) * 10  # Correto
```

### Erro 2: Ignorar Datas de Cupom

Cupons são pagos em datas específicas. Se compra entre datas de cupom, vendedor leva seus juros acumulados:

```python
# Se compra título entre datas de cupom
# 1. Você paga juros acumulados ao vendedor
# 2. Na próxima data de cupom, recebe cupom cheio
# 3. Efeito líquido: você ganha juros acumulados até data de cupom
```

### Erro 3: Usar YTM para Retornos de Curto Prazo

YTM assume manutenção até vencimento. Para trades de curto prazo, use:

```
Retorno de preço = (Preço novo - Preço de compra) / Preço de compra
Retorno total = Retorno de preço + Cupom recebido / Preço de compra
```

### Erro 4: Esquecer Risco de Reinvestimento

YTM assume que cupons são reinvestidos no mesmo yield. Na realidade:

```python
# Yields menores ao reinvestir cupons
current_yield = 5.8  # %
coupon_yield = 4.5   # % para reinvestimento

# Retorno real < YTM
```

## Saiba Mais

- [Visão Geral do Tesouro](index.md)
- [Ferramenta tddata](tddata.md)
- [Dados IBGE](../ibge/index.md) — Para dados de inflação
