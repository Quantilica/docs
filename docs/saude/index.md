# Saúde Pública

Dados e microdados de vigilância epidemiológica, natalidade, mortalidade e internações hospitalares brasileiras obtidos a partir dos sistemas do DATASUS (Departamento de Informática do SUS).

## O desafio

Extrair e processar os microdados de saúde do Brasil envolve superar sérias barreiras de infraestrutura e legibilidade:

- **Instabilidade do FTP oficial** — o servidor `ftp.datasus.gov.br` é instável, apresenta quedas frequentes e velocidades de download limitadas por conexão.
- **Formato proprietário `.dbc`** — os arquivos são disponibilizados no formato compactado proprietário `.dbc`. Ele precisa ser descompactado para `.dbf` antes de ser legível por ferramentas tradicionais de dados.
- **Nomenclatura críptica** — os arquivos seguem regras de nomenclatura complexas (ex.: `RDSP2001.dbc` significa Internações Hospitalares Reduzidas, em São Paulo, de janeiro de 2020) que exigem decodificação precisa.
- **Escala de dados** — a base histórica completa ultrapassa 320 GB, exigindo filtros inteligentes (região, período e subsistemas) para downloads viáveis.
- **Mapeamento de códigos** — muitos campos são codificados numericamente e requerem tabelas auxiliares de referência (geralmente distribuídas em PDFs) para se tornarem inteligíveis.

## Pacotes

- **[datasus-fetcher](datasus-fetcher.md)** — Crawler multithread concorrente para extração resiliente dos 113 datasets de saúde brasileiros (SIM, SINASC, SIH, SIA, CNES, SINAN, etc.). Realiza downloads paralelos, retoma transferências interrompidas e resolve o versionamento de arquivos modificados retroativamente.

## Próximos passos

- Para começar a baixar dados de saúde: vá para **[datasus-fetcher](datasus-fetcher.md)**.
- Para cruzar óbitos infantis com dados de saneamento e população: veja o cookbook **[Mortalidade infantil × SUS](../cookbook/mortalidade-sus.md)**.
- Para entender como converter os arquivos `.dbc` em Parquet: veja a documentação do **[quantilica-io](../fundacoes/quantilica-io.md)**.

## Recursos externos

- [Portal oficial do DATASUS](https://datasus.saude.gov.br/)
- [FTP Público do DATASUS](ftp://ftp.datasus.gov.br/)
