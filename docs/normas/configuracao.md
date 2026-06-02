---
title: Configuração Global das Ferramentas
description: Onde os pacotes SQL do ecossistema Quantilica armazenam configuração de banco de dados e armazenamento, e como gerenciá-la.
---

# Configuração Global das Ferramentas

Os pacotes SQL do ecossistema Quantilica (`bcb-sgs-sql`, `sidra-sql`) precisam de
configuração persistente para conectar ao banco de dados PostgreSQL e localizar
os dados baixados pelos fetchers. Esta página explica onde essa configuração
fica, como configurá-la e qual é a ordem de precedência.

---

## Localização dos arquivos

Toda a configuração global fica agrupada sob `~/.config/quantilica/`:

```
~/.config/quantilica/
  bcb-sgs-sql/
    config.ini
  sidra-sql/
    config.ini
```

No Windows, `~/.config/quantilica/` resolve para `%APPDATA%\quantilica\`.

Além do arquivo global, cada ferramenta também aceita um `config.ini` local —
um arquivo na pasta de trabalho corrente. A configuração local sobrepõe a global
para qualquer chave em comum.

### Precedência

```
config.ini (local, pasta corrente)  ← maior prioridade
    ↑
~/.config/quantilica/<ferramenta>/config.ini  (global)
    ↑
(sem config → erro com instruções de setup)
```

---

## Formato do arquivo

Os arquivos usam o formato INI padrão do Python:

```ini
[database]
host     = localhost
port     = 5432
user     = postgres
password = senha_secreta
dbname   = dados
schema   = bcb_sgs

[storage]
data_dir       = /data/bcb-sgs
cache_ttl_hours = 24.0
```

A seção `[database]` e a chave `storage.data_dir` são obrigatórias. As demais
chaves têm valores padrão.

---

## Gerenciando via CLI

Todas as ferramentas expõem um subcomando `config` com três operações:

### `config set`

```bash
# Escreve no config local (pasta corrente)
bcb-sgs-sql config set database.host localhost
bcb-sgs-sql config set database.port 5432
bcb-sgs-sql config set database.user postgres
bcb-sgs-sql config set database.password senha_secreta
bcb-sgs-sql config set database.dbname dados
bcb-sgs-sql config set database.schema bcb_sgs
bcb-sgs-sql config set storage.data_dir /data/bcb-sgs

# Escreve no config global (~/.config/quantilica/bcb-sgs-sql/config.ini)
bcb-sgs-sql config set --global database.host localhost
```

A flag `--global` é útil para configuração de máquina que serve a múltiplos
projetos.

### `config get`

```bash
bcb-sgs-sql config get database.host
```

### `config list`

```bash
# Visão mesclada (local sobrepõe global)
bcb-sgs-sql config list

# Apenas o arquivo global
bcb-sgs-sql config list --global

# Apenas o arquivo local
bcb-sgs-sql config list --local
```

Os mesmos subcomandos existem para `sidra-sql`.

---

## Setup inicial recomendado

Para uma instalação nova, configure o global e esqueça:

```bash
bcb-sgs-sql config set --global database.host     localhost
bcb-sgs-sql config set --global database.port     5432
bcb-sgs-sql config set --global database.user     postgres
bcb-sgs-sql config set --global database.password <senha>
bcb-sgs-sql config set --global database.dbname   dados
bcb-sgs-sql config set --global database.schema   bcb_sgs
bcb-sgs-sql config set --global storage.data_dir  /data/bcb-sgs
```

Se você usa banco de dados diferentes por projeto, crie um `config.ini` local
na raiz de cada projeto com apenas as chaves que diferem:

```ini
# ./config.ini — sobrepõe apenas o schema e o data_dir para este projeto
[database]
schema = bcb_sgs_dev

[storage]
data_dir = ./data
```

---

## Migração de versões anteriores

Versões anteriores ao suporte ao namespace `quantilica` guardavam a config em
caminhos isolados por ferramenta:

- `~/.config/bcb-sgs-sql/config.ini`
- `~/.config/sidra-sql/config.ini`

Na primeira execução após a atualização, a ferramenta detecta o arquivo antigo
e o copia automaticamente para o novo caminho, emitindo um aviso:

```
UserWarning: Config migrated from ~/.config/bcb-sgs-sql/config.ini
             to ~/.config/quantilica/bcb-sgs-sql/config.ini
```

O arquivo antigo **não é removido** automaticamente. Após confirmar que a
migração ocorreu corretamente, você pode excluí-lo:

```bash
rm -rf ~/.config/bcb-sgs-sql
rm -rf ~/.config/sidra-sql
```

---

## Saiba mais

- [bcb-sgs-sql](../bcb/bcb-sgs-sql.md) — carregar séries do SGS/BCB no PostgreSQL.
- [sidra-sql](../ibge/sidra-sql.md) — carregar agregados do IBGE SIDRA no PostgreSQL.
- [Convenções de Armazenamento](../concepts/storage.md) — onde os fetchers salvam os dados brutos.
