# Deployment Guide

Guia completo para configurar, desenvolver e publicar o site de documentação em `docs.quantilica.com`.

## Índice

- [Quick Start](#quick-start)
- [Configuração Local](#configuração-local)
- [Configuração do Repositório GitHub](#configuração-do-repositório-github)
- [Configuração de Domínio](#configuração-de-domínio)
- [Publicação](#publicação)
- [Checklist de Pré-Deploy](#checklist-de-pré-deploy)
- [Checklist: Pronto para Publicar?](#checklist-pronto-para-publicar)
- [Workflow GitHub Actions](#workflow-github-actions)
- [Troubleshooting](#troubleshooting)
- [Estrutura de Arquivos](#estrutura-de-arquivos)
- [Manutenção](#manutenção)

---

## Quick Start

Configure e suba o site localmente em minutos.

```bash
# 1. Clone o repositório
git clone https://github.com/Quantilica/docs.git
cd docs

# 2. Instale as dependências
pip install mkdocs mkdocs-material

# 3. Suba o servidor de desenvolvimento
mkdocs serve

# 4. Acesse http://localhost:8000
```

O site recarrega automaticamente ao editar arquivos.

### Publicar (após setup inicial)

```bash
git add .
git commit -m "Update docs"
git push origin main
```

O site é atualizado automaticamente em `https://docs.quantilica.com` (~1 minuto).

---

## Configuração Local

### Pré-requisitos

- Python 3.10 ou superior
- pip ou [uv](https://github.com/astral-sh/uv)
- Git

### Instalar Dependências

```bash
# pip
pip install mkdocs mkdocs-material

# ou com uv
uv pip install mkdocs mkdocs-material
```

### Comandos Comuns

```bash
# Servidor de desenvolvimento (com auto-reload)
mkdocs serve

# Build do site estático (saída em site/)
mkdocs build

# Build com modo estrito (falha em warnings)
mkdocs build --strict

# Build limpo
mkdocs build --clean
```

---

## Configuração do Repositório GitHub

### 1. Criar Repositório

```bash
git remote add origin https://github.com/Quantilica/docs.git
git branch -M main
git push -u origin main
```

### 2. Habilitar GitHub Pages

1. Vá em **Settings** → **Pages**
2. Em "Build and deployment":
   - Source: **GitHub Actions** *(NÃO "Deploy from a branch")*
3. Clique em **Save**

> **Não crie manualmente a branch `gh-pages`** — o workflow GitHub Actions cria automaticamente.

### 3. Verificar Permissões do Workflow

1. Vá em **Settings** → **Actions** → **General**
2. Em "Workflow permissions":
   - Selecione **Read and write permissions**
   - Marque **Allow GitHub Actions to create and approve pull requests**
3. Clique em **Save**

---

## Configuração de Domínio

### DNS (no provedor do domínio)

Para o subdomínio `docs.quantilica.com`, adicione um **CNAME record**:

| Campo      | Valor                    |
|------------|--------------------------|
| Name/Host  | `docs`                   |
| Type       | CNAME                    |
| Value      | `quantilica.github.io`   |
| TTL        | 3600 (ou padrão)         |

Aguarde 15–30 minutos para propagação do DNS.

> Para o domínio raiz (`quantilica.com`), use A records apontando para os IPs do GitHub Pages (`185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`) e os respectivos AAAA records para IPv6.

### Domínio Customizado no GitHub

1. Vá em **Settings** → **Pages**
2. Em "Custom domain": insira `docs.quantilica.com`
3. Clique em **Save**

O GitHub verifica o domínio e habilita HTTPS automaticamente (~1 minuto).

### Verificar DNS

```bash
dig docs.quantilica.com CNAME
nslookup docs.quantilica.com
# Deve resolver para GitHub Pages
```

---

## Publicação

### Deploy Automático

Ao fazer push para `main`, o workflow dispara automaticamente:

```bash
git add .
git commit -m "Update documentation"
git push origin main
```

Acompanhe em **Actions** → "Publish MkDocs Site". O site fica disponível em ~1 minuto.

### Deploy Manual

1. Vá na aba **Actions**
2. Clique em **Publish MkDocs Site**
3. Clique em **Run workflow** → selecione `main` → **Run workflow**

### Rollback (se necessário)

```bash
# Opção 1: Reverter último commit
git revert HEAD
git push origin main

# Opção 2: Reset para commit anterior (use com cautela)
git reset --hard <commit-hash>
git push origin main --force
```

---

## Checklist de Pré-Deploy

Use antes de cada push para garantir um deploy tranquilo.

### Verificações Locais

- [ ] **Atualizar dependências**
  ```bash
  pip install --upgrade mkdocs mkdocs-material
  ```

- [ ] **Build sem erros**
  ```bash
  mkdocs build --strict
  ```
  - Sem erros ou warnings
  - Diretório `site/` criado

- [ ] **Testar localmente**
  ```bash
  mkdocs serve
  ```
  - Acesse http://localhost:8000
  - Navegue pelas páginas principais
  - Verifique links e blocos de código

- [ ] **Verificar estrutura de navegação**
  - Todos os itens de menu aparecem
  - Sem referências quebradas a páginas inexistentes

- [ ] **Revisar conteúdo**
  - Ortografia e gramática
  - Exemplos de código corretos

### Verificações Antes do Push

- [ ] **Revisar git status**
  ```bash
  git status
  git diff
  ```
  - Apenas arquivos intencionais modificados

- [ ] **Mensagem de commit significativa**
  - Use imperativo: "Add IBGE labor statistics guide"

### Após o Push

- [ ] **Verificar workflow** na aba **Actions** (deve completar em < 2 minutos)
- [ ] **Verificar site ao vivo**: https://docs.quantilica.com
  - Hard refresh: `Ctrl+Shift+R` (Windows/Linux) ou `Cmd+Shift+R` (Mac)

---

## Checklist: Pronto para Publicar?

Verifique se tudo está configurado para o **primeiro deploy**:

- [ ] Repositório criado em **Quantilica/docs**
- [ ] GitHub Pages configurado com **"GitHub Actions"** como source
- [ ] CNAME registrado: `docs.quantilica.com` → `quantilica.github.io`
- [ ] Testado localmente com `mkdocs build --strict` (sem erros)
- [ ] `site/` está no `.gitignore` (NÃO commitar)
  ```bash
  grep -n "^/site/$" .gitignore
  # Deve retornar: 2:/site/
  ```
- [ ] Branch `gh-pages` **NÃO** criada manualmente

**Se tudo está ✅:**

```bash
git push origin main
# Acompanhe em: Actions tab do repositório
# Site em: https://docs.quantilica.com
```

### Proteção de Branch (Recomendado)

**Settings → Branches → Branch protection rules**:

```
Branch name pattern: main
✅ Require a pull request before merging
✅ Require status checks to pass before merging
  └─ GitHub Actions workflow required
```

---

## Workflow GitHub Actions

**Arquivo**: `.github/workflows/publish.yml`

### Triggers

- Push para `main` (mudanças em `docs/`, `mkdocs.yml`, ou arquivo do workflow)
- Pull requests para `main` (build apenas, sem deploy)
- Trigger manual via GitHub Actions UI

### Steps

1. Checkout do código
2. Python 3.11
3. Instala MkDocs + Material theme
4. Build com `--strict` (falha em warnings)
5. Upload do artefato para GitHub Pages
6. Deploy para GitHub Pages (somente em push para main)

---

## Troubleshooting

### Site não atualiza após push

1. Verifique o status do workflow na aba **Actions** (procure por X vermelho)
2. Verifique **Settings** → **Pages** (deve ter ✅ verde)
3. Hard refresh no browser: `Ctrl+Shift+R`
4. Aguarde 1–2 minutos após o workflow completar

### Domínio customizado não funciona

1. Verifique o DNS: `nslookup docs.quantilica.com`
2. Verifique se o arquivo `CNAME` existe na branch `gh-pages`
3. Confirme em **Settings** → **Pages** que o domínio está salvo com ✅

### Build falha com strict mode

```bash
# Rode localmente para ver o erro
mkdocs build --strict
```

Problemas comuns:
- Links internos quebrados: `[texto](caminho-invalido.md)`
- Imagens com caminho incorreto

### HTTPS não habilitado

1. **Settings** → **Pages**
2. Marque **Enforce HTTPS**
3. Aguarde ~1 minuto para emissão do certificado SSL

| Problema | Solução |
|----------|---------|
| Build falha | `mkdocs build --strict` local para ver erro |
| Site não aparece | Aguarde 2 min após build + hard refresh |
| HTTPS não funciona | GitHub leva ~1 min para emitir certificado |
| CNAME não resolve | `nslookup docs.quantilica.com` para verificar |

---

## Estrutura de Arquivos

```
docs/
├── .github/
│   └── workflows/
│       └── publish.yml          # GitHub Actions workflow
├── docs/                         # Arquivos fonte da documentação
│   ├── index.md
│   ├── ibge/
│   ├── tesouro/
│   ├── trabalho/
│   ├── comex/
│   ├── saude/
│   ├── clima/
│   ├── architecture/
│   └── concepts/
├── site/                         # Gerado (gitignored)
├── .gitignore
├── mkdocs.yml                    # Configuração do MkDocs
└── DEPLOYMENT.md                 # Este arquivo
```

---

## Manutenção

### Atualizar documentação

```bash
# Edite arquivos em docs/
git add docs/
git commit -m "Update documentation"
git push origin main
```

### Atualizar dependências (mensal)

```bash
pip install --upgrade mkdocs mkdocs-material
```

### Fixar versões (opcional)

Para evitar mudanças inesperadas, fixe versões no workflow `.github/workflows/publish.yml`:

```yaml
- name: Install dependencies
  run: |
    pip install --upgrade pip
    pip install mkdocs==1.5.3 mkdocs-material==9.4.14
```

Versões: [MkDocs releases](https://github.com/mkdocs/mkdocs/releases) · [Material releases](https://github.com/squidfunk/mkdocs-material/releases)

---

## Referências

- [MkDocs Docs](https://www.mkdocs.org/)
- [Material Theme](https://squidfunk.github.io/mkdocs-material/)
- [GitHub Pages Docs](https://docs.github.com/en/pages)

---

*Last Updated: April 2026*
