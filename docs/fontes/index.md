---
title: Fontes de dados — catálogo de coletores
description: Todas as fontes públicas brasileiras cobertas pela Quantilica, organizadas por domínio, com o coletor de cada uma.
---

# Fontes de dados

Cada fonte pública tem um coletor próprio, instalado sob demanda com `quantilica install <fonte>`. Todos seguem os mesmos [princípios de design](../conceitos/principios.md): retry com backoff, manifesto SHA-256 e saída pronta para Parquet.

Antes de rodar um download grande, confira o [estado atual das fontes](../status.md).

| Domínio | Coletores | Fonte oficial |
|---|---|---|
| [IBGE (Macroeconomia)](ibge/index.md) | [ibge-sidra-fetcher](ibge/ibge-sidra-fetcher.md) | IBGE SIDRA e Agregados |
| [Tesouro (Finanças)](tesouro/index.md) | [tesouro-direto-fetcher](tesouro/tesouro-direto-fetcher.md), [rtn-fetcher](tesouro/rtn-fetcher.md), [pgfn-fetcher](tesouro/pgfn-fetcher.md) | Tesouro Nacional e PGFN |
| [Banco Central](bcb/index.md) | [bcb-sgs-fetcher](bcb/bcb-sgs-fetcher.md), [bcb-microdados-fetcher](bcb/bcb-microdados-fetcher.md) | BCB SGS e microdados |
| [Mercado de Trabalho](trabalho/index.md) | [pdet-fetcher](trabalho/pdet-fetcher.md) | MTE/PDET (CAGED, RAIS) |
| [Comércio Exterior](comex/index.md) | [comex-fetcher](comex/comex-fetcher.md) | MDIC/Comex Stat |
| [Saúde Pública](saude/index.md) | [datasus-fetcher](saude/datasus-fetcher.md), [sigtap-fetcher](saude/sigtap-fetcher.md) | DATASUS |
| [Clima](clima/index.md) | [inmet-fetcher](clima/inmet-fetcher.md) | INMET BDMEP |
| [Aviação Civil](aviacao/index.md) | [anac-fetcher](aviacao/anac-fetcher.md) | ANAC |
| [Petróleo, Gás e Biocombustíveis](petroleo/index.md) | [anp-fetcher](petroleo/anp-fetcher.md) | ANP |
| [Educação](educacao/index.md) | [inep-fetcher](educacao/inep-fetcher.md), [capes-fetcher](educacao/capes-fetcher.md) | INEP e CAPES |
| [Empresas](empresas/index.md) | [rfb-cnpj-fetcher](empresas/rfb-cnpj-fetcher.md) | Receita Federal |
| [Mercado de Capitais](mercado-capitais/index.md) | [cvm-fetcher](mercado-capitais/cvm-fetcher.md), [b3-fetcher](mercado-capitais/b3-fetcher.md) | CVM e B3 |
| [Política](politica/index.md) | [tse-fetcher](politica/tse-fetcher.md) | TSE |
| [Energia Elétrica](energia/index.md) | [ons-fetcher](energia/ons-fetcher.md) | ONS |
| [Transportes](transportes/index.md) | [antt-fetcher](transportes/antt-fetcher.md), [infosiga-fetcher](transportes/infosiga-fetcher.md) | ANTT e Infosiga-SP (Detran-SP) |
| [Governo e Transparência](governo/index.md) | [transparencia-sp-fetcher](governo/transparencia-sp-fetcher.md) | Portal da Transparência de SP |
| [Loterias](loterias/index.md) | [loterias-fetcher](loterias/loterias-fetcher.md) | Caixa Econômica Federal |
| [Ipeadata](ipea/index.md) | [ipeadata-fetcher](ipea/ipeadata-fetcher.md) | Ipea |

Os domínios do IBGE e do Banco Central também documentam os carregadores SQL e os catálogos de pipelines que vêm depois do coletor.

## Onde está a documentação de cada coisa

- **Instalar e usar um coletor:** a página da fonte (tabela acima).
- **Bibliotecas que todos usam:** [Fundações](../fundacoes/index.md).
- **Cruzar mais de uma fonte:** [Guias](../guias/index.md).
- **Por que o sistema tem essa forma:** [Conceitos](../conceitos/index.md).
