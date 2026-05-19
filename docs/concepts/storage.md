# Convenções de Armazenamento — Fetchers

Esta página cobre a perspectiva do **usuário final**: como os arquivos são nomeados, como as pastas são organizadas e como a flag `-o` funciona. Para a perspectiva do **contribuidor** (como implementar essas convenções num novo fetcher), veja [Padronização de CLI](../normas/cli-fetchers.md).

Este documento define os padrões de nomenclatura de arquivos, estrutura de pastas e interface CLI adotados por todos os pacotes fetcher da Quantilica.

---

## Nomenclatura de Arquivos

O nome de cada arquivo baixado incorpora um timestamp extraído do servidor de origem (cabeçalho `Last-Modified` ou equivalente). A função `stamp_filename()` de `quantilica_core.storage` implementa o padrão.

### Formato

```
{base}@{timestamp}.{ext}
```

O separador entre a base e o timestamp é sempre `@`. A base codifica o conjunto de dados e a partição; o timestamp indica quando o arquivo foi publicado na origem, não quando foi baixado.

### Precisão do timestamp

| Precisão | Formato | Quando usar |
|---|---|---|
| `date` (padrão) | `YYYYMMDD` | Fontes com granularidade diária |
| `datetime` | `YYYYMMDDTHHMMSS` | Fontes com múltiplas versões no mesmo dia |

Quando o servidor não retorna timestamp, o arquivo é salvo sem `@` — sem inventar uma data.

### Exemplos por pacote

| Pacote | Exemplo de nome |
|---|---|
| `comex-fetcher` | `exp_2023@20240315.csv` |
| `datasus-fetcher` | `sih-rd_202001-sp@20240115.dbc` |
| `inmet-fetcher` | `inmet-bdmep_2023@20240101.zip` |
| `pdet-fetcher` | `caged_202001@20210315.csv` |
| `rtn-fetcher` | `rtn@20240315T101500.xlsx` |
| `tesouro-direto-fetcher` | `taxas-dos-titulos-ofertados-pelo-tesouro-direto@20240315T101530.csv` |

### Implementação

```python
from quantilica_core.storage import stamp_filename

# Precisão date (padrão)
stamp_filename("exp_2023", "csv", date(2024, 3, 15))
# → "exp_2023@20240315.csv"

# Precisão datetime
stamp_filename("rtn", "xlsx", datetime(2024, 3, 15, 10, 15), precision="datetime")
# → "rtn@20240315T101500.xlsx"

# Sem timestamp
stamp_filename("rtn", "xlsx", None)
# → "rtn.xlsx"
```

---

## Estrutura de Pastas

Os arquivos são organizados em pastas diretamente nomeadas pelo `dataset_id`, sem camada intermediária de categoria (sem `raw/`/`processed/`/`docs/`). Esta é a estrutura adotada por todos os fetchers e implementada pelo método `BaseDataRepository.dataset_path()` do `quantilica-core`.

### Princípio

```
{output}/
├── {dataset_id}/
│   ├── {partição}/      ← opcional; usada quando há agrupamento temporal ou geográfico
│   │   └── arquivo@timestamp.ext
│   └── arquivo@timestamp.ext
└── ...
```

O diretório raiz (`{output}`) é o único caminho fornecido pelo usuário. A estrutura interna é de responsabilidade exclusiva do pacote.

### API do quantilica-core

```python
from quantilica_core.storage import BaseDataRepository

class FooRepository(BaseDataRepository):
    def file_path(self, dataset_id: str, filename: str) -> Path:
        return self.dataset_path(dataset_id, filename)
        # → {root}/{dataset_id}/{filename}
```

Categorias adicionais (documentação, dados processados, etc.) são responsabilidade do fetcher — use `self.storage.path_for(...)` diretamente.

### Exemplos por pacote

**comex-fetcher**
```
{output}/
├── exp/
│   └── exp_2023@20240315.csv
├── imp/
│   └── imp_2023@20240315.csv
├── exp-mun/
├── imp-mun/
├── auxiliary-tables/
│   └── ncm@20240315.csv
├── repetro/
└── validacao/
```

**datasus-fetcher**
```
{output}/
├── sih-rd/
│   ├── 202001/
│   │   └── sih-rd_202001-sp@20240115.dbc
│   └── 202002/
├── sinasc-dn/
│   └── 2023/
│       └── sinasc-dn_2023@20240115.dbc
├── _documentacao/
│   ├── sih/
│   │   └── estrutura@20240115.pdf
│   └── sinasc/
└── _auxiliar/
    └── sih/
        └── cid10@20240115.dbf
```

Documentação e tabelas auxiliares são agrupadas pelo **sistema** (ex: `sih`, `cnes`), não pelo subsistema (ex: `sih-rd`, `cnes-dc`), pois um mesmo conjunto de documentos cobre todos os subsistemas de um sistema. O prefixo `_` faz essas pastas aparecerem antes das pastas de dados em qualquer ordenação alfabética e evita nomes reservados do Windows (como `aux`).

Para a estrutura detalhada de todos os demais pacotes (`inmet-fetcher`, `pdet-fetcher`, `rtn-fetcher`, `tesouro-direto-fetcher`), veja a seção de exemplos em [Padronização de CLI](../normas/cli-fetchers.md).

---

## Interface CLI

Todos os fetchers expõem o diretório de saída pelo argumento `-o` / `--output`.

### Especificação

| Propriedade | Valor |
|---|---|
| Nomes | `-o`, `--output` |
| Tipo | `Path` (via `type=Path` no argparse) |
| Padrão | `Path("/data/<fonte>")` |
| Obrigatoriedade | Opcional (o padrão é suficiente para uso imediato) |

### Padrões por pacote

| Pacote | Default de `--output` |
|---|---|
| `comex-fetcher` | `/data/secex-comex` |
| `datasus-fetcher` | `/data/datasus` |
| `inmet-fetcher` | `/data/inmet` |
| `pdet-fetcher` | `/data/pdet` |
| `rtn-fetcher` | `/data/rtn` |
| `tesouro-direto-fetcher` | `/data/tesouro-direto` |

### Implementação

```python
parser.add_argument(
    "-o", "--output",
    type=Path,
    default=Path("/data/secex-comex"),
    help="Diretório de saída.",
)
```

### Notas

- Comandos que recebem um diretório de **entrada** (leitura de arquivos já baixados) devem usar `--input` ou argumento posicional — nunca reutilizar `--output` para esse fim.
- Subcomandos de uma mesma CLI devem todos aceitar `--output` com o mesmo default; não é necessário repetir o default em cada subcomando se o parser raiz o define.
- O argumento `--archive-dir` do `datasus-fetcher` (diretório de arquivamento de versões antigas) é um segundo diretório de saída para operação específica — mantém nome próprio sem conflitar com `--output`.

---

*Atualizado em: 11 de maio de 2026*
