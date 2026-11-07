---
title: Documentação dos dados
description: Norma da documentação dos dados de cada fetcher Quantilica — uma página por dataset, cabeçalho YAML verificado no CI, seções fixas, dicionário de todas as variáveis e publicação neste site.
---

# Documentação dos dados

Todo fetcher documenta, no próprio repositório, os dados que baixa e converte para o lake. Esta norma define onde essa documentação fica, o formato de cada página e como ela é verificada e publicada.

Ela complementa a de [Padrões de Escrita](escrita.md), que trata do README (a ferramenta), e a de [CHANGELOG.md](changelog.md), que registra as mudanças. A documentação dos dados descreve o **estado atual** de cada dataset: o que ele contém, de onde vem, como chega ao lake e quais cuidados exige.

---

## 1. Escopo

**Obrigatória** em todo repositório `*-fetcher`, para todo dataset que o fetcher declara (os ids devolvidos pelo conversor do lake), inclusive os que ainda não têm conversão.

Um fetcher novo já nasce com a pasta `docs/`. Um PR que muda o que o fetcher baixa ou como converte atualiza as páginas afetadas **no mesmo commit**.

## 2. Estrutura

```
docs/
  README.md                  # página da fonte
  datasets/
    <dataset_id>.md          # uma página por dataset
    <dataset_id>.schema.json # esquema de referência do lake (gerado)
```

- `<dataset_id>` é o mesmo id que o conversor grava no lake (`<fonte>/<dataset_id>`).
- A página da fonte (`docs/README.md`) apresenta o órgão e o sistema, lista os datasets (uma linha cada), descreve como e quando a fonte publica, relaciona a fonte com outras (por exemplo COSIF, ESTBAN e SCR, no Banco Central) e registra as quebras que valem para todos os datasets.
- O texto é público. Detalhes de operação interna (máquinas, caminhos locais, agendamentos) não entram.

## 3. Cabeçalho da página de dataset

Cada página começa com um cabeçalho YAML de campos fixos. É o que a verificação lê e o que este site e o catálogo do portal agregam. Campo que não se aplica fica explícito (`null`), com o motivo no texto.

| Campo | Obrigatório | Conteúdo |
|---|---|---|
| `id`, `fonte` | sim | id do dataset e da fonte, iguais aos do lake |
| `titulo`, `resumo` | sim | nome e uma frase |
| `orgao` | sim | quem publica |
| `pagina_oficial` | sim | URL de referência na fonte |
| `licenca` | sim | licença ou termo de uso, com URL |
| `periodicidade` | sim | frequência de publicação |
| `cobertura` | sim | `inicio` e `fim` (ou `em-curso`) |
| `unidade` | sim | o que é uma linha |
| `granularidade` | sim | espacial e temporal |
| `formato_bruto` | sim | como a fonte publica (formato, codificação, separador, layout) |
| `lake` | sim | `estado` (`convertido`, `parcial`, `so-bruto`), `particoes`, `chave`, `colunas` |
| `unidades_de_medida` | quando há valores | moeda, escala (R$, R$ mil), unidade física, por coluna |
| `dados_pessoais` | sim | `nenhum` ou a lista de colunas com a categoria (nome, CPF, endereço…), como inventário |
| `eras` | sim | quebras de layout, metodologia ou classificação, com data; lista vazia se não houver |
| `revisado_em`, `versao_fetcher` | sim | data e versão do fetcher em que a página foi conferida contra dados reais |

## 4. Seções da página de dataset

As seções vêm nesta ordem, com estes títulos:

1. **Resumo** — o que é o dataset e para que serve.
2. **Ficha técnica** — tabela gerada a partir do cabeçalho; não se edita à mão.
3. **Origem e coleta** — de onde o fetcher baixa, como os arquivos se chamam na fonte e no bruto, como as versões se sucedem e o que o fetcher descarta (documentação, provas, arquivos temporários).
4. **Conteúdo** — unidade de análise, cobertura real (o que a fonte anuncia e o que de fato veio) e as eras, com data.
5. **Variáveis** — dicionário de **todas** as variáveis, escrito à mão:

    | Coluna no lake | Na fonte | Tipo | Descrição | Unidade / códigos | Período |
    |---|---|---|---|---|---|

    Variável que só existe em algumas eras indica o período. Códigos longos podem apontar para uma tabela de códigos. O dicionário oficial da fonte entra como link, mas não substitui esta tabela.
6. **No lake** — dataset, partições, chave e as transformações do conversor: tipos, renomeações, textos que viram nulo, correções de layout e o que fica de fora.
7. **Cuidados de uso** — o que leva quem usa o dado a errar: escala (R$ mil), mês corrente parcial, dupla contagem, códigos que mudam de composição, diferenças com outras fontes. Cada item traz a evidência (data, versão do fetcher, comparação feita).
8. **Exemplos** — pelo menos uma consulta reproduzível sobre o lake (polars ou DuckDB) que responde a uma pergunta real e respeita o cuidado principal.
9. **Referências** — documentação oficial, notas técnicas e páginas da fonte.

## 5. Modelo

```markdown
---
dataset:
  id: <dataset_id>
  fonte: <fonte>
  titulo: <nome>
  resumo: <uma frase>
  orgao: <órgão>
  pagina_oficial: <URL>
  licenca: <licença ou termo de uso, com URL>
  periodicidade: <mensal, anual...>
  cobertura: {inicio: <AAAA-MM>, fim: em-curso}
  unidade: <o que é uma linha>
  granularidade: {espacial: <nível>, temporal: <nível>}
  formato_bruto: <formato, codificação, separador>
  lake: {estado: convertido, particoes: [ano, mes], chave: [<colunas>], colunas: <n>}
  unidades_de_medida: {<coluna>: "R$ mil"}
  dados_pessoais: nenhum
  eras:
    - {desde: <AAAA-MM>, mudanca: "<o que mudou>"}
  revisado_em: <AAAA-MM-DD>
  versao_fetcher: <versão>
---

# <nome>

## Resumo
## Ficha técnica
<!-- gerado:ficha -->
## Origem e coleta
## Conteúdo
## Variáveis
| Coluna no lake | Na fonte | Tipo | Descrição | Unidade / códigos | Período |
|---|---|---|---|---|---|
## No lake
## Cuidados de uso
## Exemplos
## Referências
```

## 6. Verificação

Um teste em cada fetcher chama a verificação comum do `quantilica-core`, que falha quando:

- um dataset declarado não tem página, ou uma página não corresponde a dataset;
- o cabeçalho não segue o esquema da seção 3;
- falta uma seção da seção 4, ou ela está fora de ordem;
- o dataset está convertido e as partições do cabeçalho divergem das do conversor;
- o dataset está convertido e o dicionário de variáveis não cobre exatamente as colunas do esquema de referência (`<dataset_id>.schema.json`, gerado de uma conversão real).

A verificação começa como aviso e passa a **bloquear o CI** de cada fetcher assim que ele estiver migrado. Ela não julga a qualidade do texto; isso fica para a revisão.

## 7. Partes geradas

O comando `quantilica docs <fonte> --update` reescreve a ficha técnica a partir do cabeçalho e atualiza o esquema de referência a partir de uma conversão real. Todo o resto, inclusive o dicionário de variáveis, é escrito à mão.

## 8. Publicação

Este site importa a pasta `docs/` de cada fetcher no build e publica as páginas sob a página da ferramenta (`fontes/<tema>/<fetcher>/dados/<dataset_id>`). O cabeçalho também alimenta o catálogo do portal. O repositório do fetcher é a fonte da verdade: correções se fazem lá, não aqui.
