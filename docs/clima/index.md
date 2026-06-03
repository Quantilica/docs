# Clima e Meio Ambiente

Dados meteorológicos e climáticos históricos e em tempo real provenientes das estações automáticas e convencionais do INMET (Instituto Nacional de Meteorologia).

## O desafio

Recuperar e unificar dados climáticos das mais de 500 estações brasileiras apresenta dificuldades recorrentes:

- **Encoding inconsistente** — os arquivos anuais compactados pelo INMET usam codificação `latin-1` com marcas de ordem de byte (BOM) intermitentes, gerando erros de leitura.
- **Cabeçalhos variáveis** — o formato dos arquivos CSV gerados pelas estações varia de ano para ano, possuindo metadados extras na parte superior e separadores de coluna inconsistentes (`,` vs. `;`).
- **Valores nulos ocultos** — o INMET registra a ausência de leitura meteorológica usando a sentinela `-9999`. É necessário substituir explicitamente este valor por nulo para evitar erros de cálculo estatístico.
- **Data e hora separadas** — as observações registram datas e horas em colunas diferentes, exigindo parse e unificação em um campo `datetime` nativo.
- **Tipos de estações** — a rede divide-se em estações automáticas (leituras horárias) e convencionais (leituras manuais diárias/periódicas), que não devem ser misturadas sem um tratamento de reamostragem temporal.

## Pacotes

- **[inmet-fetcher](inmet-fetcher.md)** — Downloader e parser para o BDMEP (Banco de Dados Meteorológicos para Ensino e Pesquisa). Permite a sincronização paralela de arquivos anuais e a exportação direta em arquivos consolidados Parquet, CSV ou JSON com colunas normalizadas em `snake_case` e tipos de dados limpos.

## Próximos passos

- Para começar a baixar dados climáticos: vá para **[inmet-fetcher](inmet-fetcher.md)**.
- Para cruzar temperatura e chuva com índices de preços agrícolas: veja o cookbook **[Estiagem no Nordeste × Preços](../cookbook/estiagem-nordeste.md)**.
- Para entender as vantagens de usar arquivos Parquet na análise climatológica: consulte o tutorial **[Parquet + Polars](../concepts/parquet-polars.md)**.

## Recursos externos

- [Portal oficial do INMET](https://portal.inmet.gov.br/)
- [Banco de Dados Meteorológicos (BDMEP)](https://portal.inmet.gov.br/dadoshistoricos)
