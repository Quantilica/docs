---
title: inep-fetcher — Microdados abertos do INEP
description: Baixa os microdados abertos do INEP por grupo (ENEM, Censo Escolar, SAEB, ENADE e outros 30), com atualização incremental e manifest SHA-256.
---

# `inep-fetcher`

O `inep-fetcher` baixa os microdados abertos do INEP, organizados em **34 grupos** do catálogo, de `enem` e `censo_escolar` a `saeb`, `enade`, `encceja` e os indicadores educacionais. O histórico completo passa de 20 GB.

| | |
|---|---|
| **Fonte** | INEP, microdados abertos (`download.inep.gov.br`) |
| **Formato** | ZIP no formato de origem |
| **Grupos** | 34, listados por `quantilica inep list` |
| **Escopo do pacote** | só baixa. Não extrai nem converte os arquivos |

!!! warning "Pegadinhas da fonte"

    - **Arquivos muito grandes.** Um ano de microdados pode ter vários GB. Baixe por grupo, não tudo de uma vez.
    - **Conexão reiniciada pelo servidor.** O servidor do INEP já reiniciou conexões de clientes simples (e falhou no handshake TLS com `urllib`) em verificações. O fetcher tem retry, mas revalide a fonte antes de tratá-la como indisponível. Ver [Status das fontes](../../status.md).
    - **Os nomes de grupo são IDs, não rótulos.** Use `enem`, `censo_escolar`, `censo_educacao_superior`, e assim por diante. O nome por extenso aparece em `list`.

## Instalação

```bash
# Via CLI unificada (recomendado)
quantilica install inep

# Ou como biblioteca no seu projeto
uv add inep-fetcher --index https://index.quantilica.com/simple/
```

**Requisitos:** Python 3.12+

## Primeiro dado

```bash
quantilica inep sync enem -o ./data/inep
```

Para ver o plano sem baixar nada, use `--dry-run`:

```bash
quantilica inep sync enem --dry-run -o ./data/inep
```

## Comandos

| Comando | O que faz |
|---|---|
| `quantilica inep list` | Lista os grupos e as partições disponíveis (ID, partição, extensão e URL) |
| `quantilica inep check` | Compara o disco com o remoto e mostra o plano, sem baixar. `--json` imprime o plano e `--out` o grava |
| `quantilica inep sync` | Baixa os grupos pedidos (padrão: todos). `--workers` (padrão 4), `--dry-run`, `--force` e `--from-plan` |

O fluxo incremental recomendado é gerar o plano e baixar só o que mudou:

```bash
quantilica inep check enem --out plano.json -o ./data/inep
quantilica inep sync --from-plan plano.json -o ./data/inep
```

`sync` pula os arquivos locais que já estão atualizados e grava um manifest SHA-256 ao lado de cada download.

## Grupos principais

| Grupo | Conteúdo |
|---|---|
| `enem` | ENEM, microdados por edição |
| `enem_por_escola` | ENEM por escola |
| `censo_escolar` | Censo Escolar (Educação Básica) |
| `censo_educacao_superior` | Censo da Educação Superior |
| `saeb` | Sistema de Avaliação da Educação Básica |
| `enade`, `enade_licenciaturas` | Exame Nacional de Desempenho dos Estudantes |
| `encceja` | Certificação de competências |
| `censo_magisterio` | Profissionais do magistério |
| `ana`, `idd`, `talis`, `pnd`, `pnera`, `enamed` | Avaliações e pesquisas específicas |

Além dos principais, 18 grupos de **indicadores educacionais** (taxas de rendimento, distorção idade-série, nível socioeconômico, remuneração docente e outros). O alias `indicadores_educacionais` baixa todos de uma vez.

### Aliases curtos

| Alias | Grupo |
|---|---|
| `censo` | `censo_escolar` |
| `censo-superior` | `censo_educacao_superior` |
| `magisterio` | `censo_magisterio` |
| `licenciaturas` | `enade_licenciaturas` |
| `docente` | `pnd` |
| `inse` | `nivel_socioeconomico` |
| `tdi` | `taxas_distorcao_idade_serie` |
| `remuneracao` | `remuneracao_docentes` |

## Saiba mais

- [Changelog do pacote](https://github.com/Quantilica/inep-fetcher/blob/main/CHANGELOG.md)
- [Repositório](https://github.com/Quantilica/inep-fetcher)
- [Convenções de armazenamento](../../conceitos/storage.md) e [proveniência e manifestos](../../conceitos/proveniencia.md)
