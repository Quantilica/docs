# Arquitetura de CLI e Estratégia de Dependências

Este documento descreve o padrão arquitetural adotado para as interfaces de linha de comando (CLI) e o gerenciamento de dependências nos pacotes da organização Quantilica.

## 1. Princípios de Design

O ecossistema Quantilica é composto por múltiplos "fetchers" independentes que podem ser utilizados de três formas:
1.  Como bibliotecas Python (SDK).
2.  Como ferramentas de linha de comando autônomas.
3.  Como plugins integrados na CLI unificada (`quantilica-cli`).

Para suportar esses casos de uso sem sobrecarregar o usuário final com dependências desnecessárias, adotamos a estratégia de **CLI Híbrida**.

## 2. Estratégia de CLI Híbrida

Cada pacote de fetcher (ex: `comex-fetcher`, `sidra-fetcher`) deve seguir esta estrutura:

### 2.1. CLI Nativa (Leve)
- **Arquivo:** `src/<package_name>/cli.py`
- **Tecnologia:** `argparse` (biblioteca padrão do Python).
- **Dependências:** Apenas `quantilica-core` e bibliotecas padrão.
- **Objetivo:** Garantir que o pacote possa ser instalado e utilizado em ambientes restritos, mantendo o `pyproject.toml` limpo e focado na funcionalidade principal.

### 2.2. Plugin para CLI Unificada (Rico)
- **Arquivo:** `src/<package_name>/plugin.py`
- **Tecnologia:** `typer` e `rich`.
- **Dependências:** Não declaradas no `pyproject.toml` do fetcher (são fornecidas pelo host `quantilica-cli`).
- **Objetivo:** Oferecer uma experiência de usuário (UX) superior com tabelas coloridas, painéis e subcomandos aninhados quando utilizado através do hub central.

## 3. Estado Atual dos Projetos

| Projeto | CLI Nativa (`argparse`) | Plugin Typer (`plugin.py`) | Status de Padronização |
| :--- | :---: | :---: | :--- |
| `comex-fetcher` | Sim | Sim | **Padronizado** |
| `sidra-fetcher` | Sim | Sim | **Padronizado** (Refatorado em Mai/2026) |
| `datasus-fetcher` | Sim | Sim | **Padronizado** |
| `pdet-fetcher` | Sim | Sim | **Padronizado** |
| `rtn-fetcher` | Sim | Sim | **Padronizado** |
| `tesouro-direto-fetcher` | Sim | Sim | **Padronizado** |
| `inmet-fetcher` | Sim | Sim | **Padronizado** |
| `bcb-sgs-fetcher` | Sim | Sim | **Padronizado** |

## 4. Diretrizes para Novos Fetchers

Ao criar um novo fetcher, o desenvolvedor deve:
1.  Manter a lógica de download desacoplada da interface.
2.  Implementar comandos básicos de exploração em `cli.py` usando `argparse`.
3.  Expor a interface completa em `plugin.py` usando `typer` para integração com o `quantilica-cli`.
4.  Não adicionar `typer` ou `rich` nas `dependencies` principais do `pyproject.toml`.
