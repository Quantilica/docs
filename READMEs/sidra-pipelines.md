# Sidra Standard Pipelines 🚀

**O catálogo oficial de pipelines ETL para o motor [sidra-sql](https://github.com/Quantilica/sidra-sql).**

Este repositório contém o conjunto padrão de definições (fetch + transform) para baixar, normalizar e carregar as principais pesquisas do IBGE (SIDRA) diretamente em um banco de dados PostgreSQL.

---

## 📋 Índice

- [O que é este repositório?](#-o-que-é-este-repositório)
- [Pipelines Disponíveis](#-pipelines-disponíveis)
  - [Economia e Preços](#economia-e-preços)
  - [Demografia](#demografia)
  - [Agropecuária e Florestal](#agropecuária-e-florestal)
- [Instalação](#-instalação)
- [Como Usar](#-como-usar)
- [Estrutura de uma Pipeline](#-estrutura-de-uma-pipeline)
- [Contribuindo](#-contribuindo)
- [Licença](#-licença)

---

## 🎯 O que é este repositório?

O `sidra-pipelines` funciona como um **hub de plugins** para o motor `sidra-sql`. Ele separa a lógica de execução (o motor) da declaração dos dados (os metadados das tabelas do IBGE e as queries SQL de transformação).

Ao instalar este repositório como um plugin, você ganha acesso imediato a uma série de tabelas analíticas prontas para uso em ferramentas como Power BI, Metabase ou Excel, sem precisar escrever uma única linha de código Python.

---

## 📊 Pipelines Disponíveis

Atualmente, o catálogo cobre **14 pesquisas essenciais** divididas em grandes temas:

### Economia e Preços
| ID da Pipeline | Pesquisa | Tabelas SIDRA | Destino Analítico |
|---|---|---|---|
| `pib_municipal` | **PIB dos Municípios** | 5938 | `analytics.pib_municipal` |
| `ipca` | **IPCA** (Inflação) | 7060, 1419, etc. | `analytics.ipca` |
| `ipca15` | **IPCA-15** | 7062, 1705, etc. | `analytics.ipca15` |
| `inpc` | **INPC** | 7063, 1100, etc. | `analytics.inpc` |

### Demografia
| ID da Pipeline | Pesquisa | Tabelas SIDRA | Destino Analítico |
|---|---|---|---|
| `estimativa_populacao` | **Estimativas de População** | 6579 | `analytics.estimativa_populacao` |
| `censo_populacao` | **Censo Demográfico** | 200 | `analytics.censo_populacao` |
| `contagem_populacao` | **Contagem de População** | 305, 793 | `analytics.contagem_populacao` |

### Agropecuária e Florestal
| ID da Pipeline | Pesquisa | Tabelas SIDRA | Destino Analítico |
|---|---|---|---|
| `pam_lavouras_temporarias` | **PAM** (Temporárias) | 839, 1000... | `analytics.pam_lavouras_temporarias` |
| `pam_lavouras_permanentes` | **PAM** (Permanentes) | 1613 | `analytics.pam_lavouras_permanentes` |
| `ppm_rebanhos` | **PPM** (Rebanhos) | 73, 3939 | `analytics.ppm_rebanhos` |
| `ppm_producao` | **PPM** (Produção Animal) | 74, 3940 | `analytics.ppm_producao` |
| `ppm_exploracao` | **PPM** (Aquicultura) | 94, 95 | `analytics.ppm_exploracao` |
| `pevs_producao` | **PEVS** (Extração/Silvic.) | 289, 291 | `analytics.pevs_producao` |
| `pevs_area_florestal` | **PEVS** (Área Florestal) | 5930 | `analytics.pevs_area_florestal` |

---

## ⚙️ Instalação

Para utilizar estas pipelines, você deve ter o `sidra-sql` instalado. Com ele pronto, instale este catálogo usando a CLI:

```bash
# Instala o catálogo oficial com o alias 'std'
sidra-sql plugin install https://github.com/Quantilica/sidra-pipelines.git --alias std
```

Para verificar se as pipelines foram registradas corretamente:
```bash
sidra-sql plugin list
```

---

## 🚀 Como Usar

Para executar uma pipeline (baixar os dados + transformar em tabela analítica), use o comando `run`:

```bash
# Exemplo: Executar a pipeline de PIB Municipal
sidra-sql run std pib_municipal

# Exemplo: Executar a pipeline de IPCA
sidra-sql run std ipca
```

O `sidra-sql` cuidará automaticamente de:
1. Consultar os metadados da tabela no IBGE.
2. Baixar os dados em paralelo (com retry e cache).
3. Carregar os dados brutos no schema `ibge_sidra`.
4. Executar a transformação SQL e criar a tabela no schema `analytics`.

---

## 📂 Estrutura de uma Pipeline

Cada pipeline dentro deste repositório segue o padrão exigido pelo motor:

```text
id-da-pipeline/
├── fetch.toml      # Define quais tabelas, variáveis e períodos baixar
├── transform.toml  # Define o nome da tabela destino e índices
└── transform.sql   # Query SQL denormalizada para consumo final
```

- **Fetch:** Utiliza o motor de download inteligente que evita requisições duplicadas.
- **Transform:** Gera tabelas planas onde valores como `"..."`, `"-"` ou `"X"` são devidamente convertidos para `NULL`.

---

## 🤝 Contribuindo

Sentiu falta de alguma pesquisa do IBGE? Contribuições são muito bem-vindas!

1. Faça um fork deste repositório.
2. Crie uma nova pasta para a sua pesquisa.
3. Adicione os arquivos `fetch.toml`, `transform.toml` e `transform.sql`.
4. Registre a nova pipeline no `manifest.toml` da raiz.
5. Envie um Pull Request!

Para um guia detalhado de como criar novas pipelines, consulte o **[Guia de Criação de Pipelines](https://github.com/Quantilica/sidra-sql/blob/main/CREATING_PIPELINES.md)** no repositório principal.

---

## 📄 Licença

Este projeto está licenciado sob a licença MIT — veja o arquivo [LICENSE](LICENSE) para detalhes.

---
**Desenvolvido por [dankkom](https://github.com/dankkom)**
