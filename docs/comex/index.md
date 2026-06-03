# Comércio Exterior

Dados detalhados sobre as exportações e importações brasileiras, consolidados pela Secretaria de Comércio Exterior (SECEX/MDIC) através do Siscomex.

## O desafio

Consumir dados de comércio exterior programaticamente apresenta desafios específicos de infraestrutura e formato:

- **Volume colossal** — arquivos CSV em nível de transação que cobrem anos inteiros podem superar facilmente 1 GB por arquivo, estourando a memória ao usar leituras brutas (como `pd.read_csv`).
- **SSL quebrado** — os servidores do governo (SECEX/MDIC) frequentemente operam com cadeias de certificados incompletas ou expiradas em janelas curtas, causando erros em requisições HTTP normais.
- **Redundância de rede** — sem APIs modernas, as execuções repetidas de pipelines de dados costumam baixar novamente centenas de megabytes de arquivos inalterados.
- **Estruturas históricas distintas** — transações a partir de 1997 usam a classificação NCM (Nomenclatura Comum do Mercosul), enquanto anos de 1989 a 1996 utilizam a antiga classificação NBM (Nomenclatura Brasileira de Mercadorias), que possui colunas e formatos diferentes.

## Pacotes

- **[comex-fetcher](comex-fetcher.md)** — Downloader unificado e resiliente para transações mensais de exportação/importação (com breakdowns municipais e REPETRO) e tabelas de códigos auxiliares (NCM, países, vias, etc.). Oferece idempotência temporal, suporte a SSL mal configurado e downloads streaming chunked.

## Próximos passos

- Para começar a baixar dados Siscomex: vá para **[comex-fetcher](comex-fetcher.md)**.
- Para cruzar balança comercial com o DuckDB: veja o cookbook **[Balança comercial em DuckDB](../cookbook/balanca-duckdb.md)**.
- Para uma análise combinada de comércio, PIB e outras séries: veja a receita **[Análise Econômica Multi-Fonte](../cookbook/analise-economica-multi-fonte.md)**.

## Recursos externos

- [Base de dados bruta da SECEX (MDIC)](https://www.gov.br/produtividade-e-comercio-exterior/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta)
- [Portal Comex Stat](http://comexstat.mdic.gov.br/pt/home)
