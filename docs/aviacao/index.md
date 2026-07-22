# Aviação Civil

Dados abertos da ANAC (Agência Nacional de Aviação Civil): voos regulares, cadastro de aeronaves, ocorrências aeronáuticas investigadas pelo CENIPA e infraestrutura de aeródromos.

## O desafio

O portal de dados abertos da ANAC é um índice de diretórios simples (`sistemas.anac.gov.br/dadosabertos`), sem API nem catálogo consultável — cada dataset é uma árvore de pastas por área/ano/mês com nomes de arquivo que mudam de convenção ao longo do tempo. Descobrir e baixar tudo programaticamente exige mapear cada área manualmente.

## Pacotes

- **[anac-fetcher](anac-fetcher.md)** — Downloader com catálogo declarativo para VRA (Voo Regular Ativo), RAB (Registro Aeronáutico Brasileiro), Ocorrências Aeronáuticas (CENIPA) e infraestrutura de Aeródromos.

## Próximos passos

- Para começar a baixar dados da ANAC: vá para **[anac-fetcher](anac-fetcher.md)**.

## Recursos externos

- [Portal de Dados Abertos da ANAC](https://www.gov.br/anac/pt-br/acesso-a-informacao/dados-abertos)
- [Índice de arquivos (sistemas.anac.gov.br/dadosabertos)](https://sistemas.anac.gov.br/dadosabertos/)
