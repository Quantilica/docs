---
title: rfb-cnpj-fetcher — Base de CNPJs da Receita Federal
description: Baixa os ZIPs da base pública de CNPJs da Receita Federal e lê cada grupo em Polars, com códigos como texto e capital social em Decimal.
---

# `rfb-cnpj-fetcher`

O `rfb-cnpj-fetcher` baixa, em paralelo, os ZIPs da base pública de CNPJs da Receita Federal e, com o extra `analysis`, lê cada ZIP em um DataFrame do Polars com tipos corretos.

| | |
|---|---|
| **Fonte** | Receita Federal, dados abertos do CNPJ (`arquivos.receitafederal.gov.br`) |
| **Volume** | 37 ZIPs: cerca de **7,8 GB** compactados e **28,7 GB** descompactados (referência de setembro de 2026) |
| **Atualização** | mensal, com partição `AAAA-MM` |
| **Grupos** | `empresas`, `estabelecimentos`, `socios`, `simples`, `cnaes`, `naturezas`, `qualificacoes`, `municipios`, `paises`, `motivos` |
| **Escopo do pacote** | download, leitura tipada e conversão para Parquet. A extração dos ZIPs em disco e a carga em banco não fazem parte dele |

!!! warning "Pegadinhas da fonte"

    - **CSV sem cabeçalho.** Cada ZIP traz um CSV em `latin-1`, separado por `;`, com todos os campos entre aspas, e os campos podem conter `;`, aspas e quebras de linha. O layout de colunas vem do documento de metadados da Receita, e o `reader` o aplica por grupo.
    - **Zeros à esquerda importam.** Partes do CNPJ e códigos de CNAE, natureza e município ficam como **texto**. Converter para número destrói a chave.
    - **"Sem data" não é nulo.** A Receita usa `0`, `00000000` ou vazio para datas ausentes. Só esses valores viram nulo. Qualquer outra data inválida levanta erro.
    - **Código de município da Receita não é o do IBGE.** O grupo `municipios` traz o código de 4 dígitos da Receita.
    - **Servidor lento.** Cada requisição leva cerca de 20 s, então o ganho vem do paralelismo (`--workers`).

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install rfb-cnpj

# Ou como biblioteca no seu projeto
uv add rfb-cnpj-fetcher --index https://index.quantilica.com/simple/
```

A leitura (`rfb_cnpj_fetcher.reader`) exige o extra `analysis`:

```bash
quantilica install rfb-cnpj --extra analysis
# ou, no seu projeto:
uv add 'rfb-cnpj-fetcher[analysis]' --index https://index.quantilica.com/simple/
```

**Requisitos:** Python 3.12+

## Primeiro dado

Os grupos pequenos (`cnaes`, `naturezas`, `paises`) servem para testar o fluxo sem baixar a base inteira:

```bash
quantilica rfb-cnpj sync cnaes naturezas -o ./data/rfb
```

## Comandos

| Comando | O que faz |
|---|---|
| `quantilica rfb-cnpj list` | Lista os arquivos de cada grupo, com a partição mensal e a URL |
| `quantilica rfb-cnpj check` | Compara o disco com o remoto e mostra o plano, sem baixar. `--json` e `--out` exportam o plano |
| `quantilica rfb-cnpj sync` | Baixa os grupos pedidos (padrão: todos). `--workers` (padrão 4), `--dry-run`, `--force` e `--from-plan` |

Sincronizar a base inteira:

```bash
quantilica rfb-cnpj sync -o ./data/rfb
```

!!! note "Espaço em disco"

    A base ocupa cerca de 8 GB em ZIP, e 29 GB depois de extraída. Garanta espaço no diretório de destino antes de sincronizar tudo.

## Lendo os dados

```python
from pathlib import Path

from rfb_cnpj_fetcher.reader import read_file, write_parquet

zip_path = Path("data/rfb/cnaes/<arquivo>.zip")
df = read_file(zip_path)            # o grupo é inferido do diretório pai
write_parquet(df, Path("data/rfb/parquet/cnaes.parquet"), source_path=zip_path)
```

`read_file(path, group=None)` lê um ZIP baixado e devolve um DataFrame tipado:

| Tipo de campo | Resultado |
|---|---|
| Códigos (CNPJ, CNAE, natureza, município, país) | texto, com zeros à esquerda preservados |
| `capital_social` | `Decimal(20, 2)` |
| Datas `AAAAMMDD` | `Date` |
| Campo de texto vazio | nulo |

As conversões são estritas. Uma linha com número de campos diferente do layout, uma data inválida ou um capital não numérico levantam `ValueError` em vez de deslocar colunas ou virar nulo em silêncio. Com `source_path`, o `write_parquet` copia o manifest do ZIP para os metadados do Parquet.

## Saiba mais

- [Changelog do pacote](https://github.com/Quantilica/rfb-cnpj-fetcher/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/rfb-cnpj-fetcher)
- [Proveniência e manifestos](../../conceitos/proveniencia.md) e [Parquet + Polars](../../conceitos/parquet-polars.md)
