---
title: quantilica-cloud
description: Plugin CLI para sincronizar manifestos de download com o catálogo Quantilica Cloud.
---

# `quantilica-cloud`

Plugin do `quantilica-cli` que sincroniza manifestos de download (`*.manifest.json`) locais com um catálogo na nuvem. A coleta de dados **nunca depende** deste pacote — sincronizar é sempre opt-in. Uma vez instalado, os comandos ficam disponíveis sob `quantilica cloud`.

> **Por que separado?** A filosofia da Quantilica é offline-first: fetchers, manifestos e armazenamento local funcionam sem rede externa. Enviar manifestos à nuvem é uma camada adicional de conveniência, nunca uma dependência.

## Instalação

```bash
uv add "quantilica-cloud @ git+https://github.com/Quantilica/quantilica-cloud.git"
```

Requer `quantilica-cli` instalado para que os comandos `quantilica cloud` funcionem.

## CLI

### Autenticar

```bash
quantilica cloud login --api-key <chave>
```

Grava as credenciais em `~/.quantilica/credentials.toml` com permissão restrita ao dono (`chmod 0o600`). Para apontar a um servidor próprio (self-hosted):

```bash
quantilica cloud login --api-key <chave> --endpoint http://localhost:8000
```

### Sincronizar manifestos

```bash
# Enviar todos os manifestos na pasta /data
quantilica cloud sync --root /data

# Só os dos últimos 7 dias
quantilica cloud sync --root /data --since 7d

# Simular sem enviar
quantilica cloud sync --root /data --since 7d --dry-run
```

O sync varre recursivamente o diretório em busca de arquivos `*.manifest.json`, agrupa-os em lotes de 100 e envia via `POST /v1/manifests:batch`. O servidor é idempotente — reenviar o mesmo manifesto não duplica registros.

### Ver status

```bash
quantilica cloud status --root /data
```

Compara a contagem de manifestos locais com o catálogo na nuvem e exibe o endpoint configurado.

## Referência de opções

| Comando | Opção | Padrão | Descrição |
|---|---|---|---|
| `login` | `--api-key` | _(obrigatório)_ | Chave de API da Quantilica Cloud |
| `login` | `--endpoint` | `https://api.quantilica.com` | URL da API |
| `sync` | `-r / --root` | `.` (diretório atual) | Diretório raiz a varrer |
| `sync` | `--since` | _(todos)_ | Filtro por data: `7d`, `30d`, etc. |
| `sync` | `--dry-run` | `False` | Simula sem enviar |
| `status` | `-r / --root` | `.` | Diretório raiz a varrer |

## Credenciais

As credenciais ficam em `~/.quantilica/credentials.toml`:

```toml
[cloud]
api_key = "sk-..."
endpoint = "https://api.quantilica.com"
```

Não coloque esse arquivo no controle de versão.

## Como está registrado

`quantilica-cloud` usa o grupo de entry points `quantilica.commands` (não `quantilica.fetchers`). Ambos os grupos montam na raiz do CLI — a distinção é semântica (ferramentas de fonte vs. comandos de plataforma), não estrutural:

```toml
[project.entry-points."quantilica.commands"]
cloud = "quantilica.cloud.plugin:app"
```

## Módulos

| Módulo | Responsabilidade |
|---|---|
| `credentials` | Carga e gravação de credenciais em `~/.quantilica/credentials.toml` |
| `client` | `ManifestSyncClient` — comunica com a API REST (push e listagem) |
| `plugin` | App Typer com os comandos `login`, `sync` e `status` |

## Princípios de Design

1. **Offline-first** — fetchers e armazenamento local funcionam sem este pacote.
2. **Plugin, não dependência** — descoberto via entry point; o CLI não acopla diretamente.
3. **Idempotente** — reenvio do mesmo manifesto SHA-256 não duplica registros.
4. **Credenciais locais** — a chave de API fica em `~/.quantilica/`, com permissão `0o600`.

## Saiba Mais

- [Manifestos & Proveniência](../concepts/proveniencia.md) — o que contém um manifesto
- [quantilica-cli](quantilica-cli.md) — arquitetura do host de plugins
- [quantilica-manifests-db](https://github.com/Quantilica/quantilica-manifests-db) — servidor SaaS que recebe os manifestos

## Repositório

[github.com/Quantilica/quantilica-cloud](https://github.com/Quantilica/quantilica-cloud) — MIT.
