# Plataforma Brasileira de Dados Públicos

Um conjunto modular de ferramentas para extrair, processar e analisar datasets públicos brasileiros — endurecido em produção para a infraestrutura real do Estado.

<div align="center">
  <img src="assets/logo.png" alt="Logo" width="200" height="200">
</div>

## O problema

Dados públicos brasileiros estão fragmentados em dezenas de agências, cada uma com sua própria infraestrutura — APIs instáveis, servidores FTP legados, schemas inconsistentes, arquivos que crescem para dezenas de gigabytes. Construir pipelines confiáveis em cima disso exige extração resiliente, validação na fonte, armazenamento estruturado e transformações reproduzíveis.

A maioria das tentativas se quebra cedo: ou a API cai e o pipeline aborta, ou o CSV de 50M linhas estoura a memória, ou um schema muda silenciosamente e a análise fica errada sem ninguém perceber.

## A solução

A plataforma fornece **uma ferramenta especializada por domínio**, cada uma desenhada para o desafio de infraestrutura específico daquela fonte. Tudo segue os mesmos cinco [Princípios de Design](concepts/principios.md): Modularidade, Resiliência, Performance, Reprodutibilidade, Sem Mágica.

| Ferramenta | Padrão | Desafio que resolve |
|---|---|---|
| **sidra-fetcher** | Cliente sync/async com smart caching | API REST IBGE instável, rate limiting |
| **sidra-sql** | ETL baseado em plugins, star schema PostgreSQL | Bulk load streaming + histórico de revisões (SCD II) |
| **tddata** | Engenharia financeira com matching FIFO de lotes | Transações de portfólio streaming, conformidade GIPS |
| **rtnpy** | Cálculo de retornos do RTN brasileiro | Conformidade com normas oficiais |
| **pdet-data** | Big Data com processamento vetorial Polars | CSVs 50M+ linhas que esgotam Pandas |
| **comexdown** | Extração resiliente com idempotência temporal | SSL ruim, arquivos GB, downtime governamental |
| **datasus-fetcher** | Crawler concorrente multithreaded | FTP legado, downloads que tomam semanas |
| **inmet-bdmep-data** | Cliente HTTP estável para metereologia | Granularidade alta, esquema variável |

## Domínios cobertos

- **[IBGE — Macroeconomia](ibge/index.md)** — PIB, IPCA, desemprego, comércio interno via SIDRA.
- **[Tesouro — Finanças](tesouro/index.md)** — yield curve, preços de títulos, retornos GIPS-compliant.
- **[Mercado de Trabalho](trabalho/index.md)** — RAIS (censo anual) + CAGED (fluxos mensais).
- **[Comércio Exterior](comex/comexdown.md)** — Siscomex import/export.
- **[Saúde Pública](saude/datasus-fetcher.md)** — microdados DATASUS (SIM, SINASC, SIA, SIHSUS, CNES).
- **[Clima & Meio Ambiente](clima/inmet-bdmep-data.md)** — séries históricas INMET BDMEP.

## Por onde começar

### Caminho de aprendizado

Se você é novo na plataforma, leia em ordem:

1. **[Arquitetura da Plataforma](concepts/arquitetura.md)** — como as partes se conectam (extração, processamento, armazenamento, análise).
2. **[Princípios de Design](concepts/principios.md)** — por que o sistema tem essa forma.
3. **[Padrões Práticos](concepts/padroes.md)** — receitas táticas que materializam os princípios.
4. **[Parquet + Polars](concepts/parquet-polars.md)** — o tutorial sobre o formato/biblioteca centrais.
5. Escolha um domínio: [IBGE](ibge/index.md), [Tesouro](tesouro/index.md), [Trabalho](trabalho/index.md), [Comércio](comex/comexdown.md), [Saúde](saude/datasus-fetcher.md), [Clima](clima/inmet-bdmep-data.md).
6. **[Cookbook](cookbook/index.md)** — receitas que combinam múltiplos domínios.

### Por caso de uso

| Você quer... | Vá para |
|---|---|
| Indicadores macroeconômicos (PIB, IPCA, desemprego) | [IBGE](ibge/index.md) |
| Yield curve e retornos de portfólio do Tesouro | [Tesouro](tesouro/index.md) |
| Análise de salários e fluxos de emprego | [Trabalho](trabalho/index.md) |
| Fluxos de comércio (import/export) | [Comércio Exterior](comex/comexdown.md) |
| Vigilância epidemiológica | [Saúde Pública](saude/datasus-fetcher.md) |
| Séries climáticas históricas | [Clima](clima/inmet-bdmep-data.md) |
| Combinar múltiplos domínios | [Cookbook](cookbook/index.md) |
