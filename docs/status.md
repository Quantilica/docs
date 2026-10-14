---
title: Status das fontes públicas brasileiras
description: Estado de saúde conhecido das fontes oficiais que a Quantilica consome — IBGE, DATASUS, Tesouro, INMET, Comex, PDET, BCB, INEP, RFB, ANAC, ANP, CVM e TSE.
---

# Status das fontes oficiais

## O que esta página é

Um snapshot informal do estado conhecido das fontes oficiais brasileiras que os fetchers da Quantilica consomem. Útil para:

- Confirmar se um erro de fetcher é problema da Quantilica ou downtime do governo.
- Decidir quando vale a pena rodar um pipeline grande.
- Entender padrões de instabilidade de cada fonte.

## Estado conhecido

| Fonte | Status atual | Última verificação | Observações |
|---|---|---|---|
| **IBGE SIDRA** (`apisidra.ibge.gov.br`) | ✅ estável | 2026-10-13 | Rate limit não documentado; preferir horário não-comercial |
| **IBGE Agregados v3** (`servicodados.ibge.gov.br`) | ✅ estável | 2026-10-13 | Janelas curtas de 502 em manutenção |
| **DATASUS FTP** (`ftp.datasus.gov.br`) | ⚠️ intermitente | 2026-10-13 | Cai frequentemente em horário comercial; reduzir `--threads` (FTP alcançável na verificação) |
| **Tesouro Transparente CKAN** | ✅ estável | 2026-10-13 | Dataset com timestamp no nome (API `package_list` responde 200) |
| **INMET BDMEP** | ⚠️ intermitente | 2026-10-13 | ZIPs por ano; latin-1; valores `-9999`. O cron da madrugada baixou os 27 ZIPs (1,9 GB) em cerca de 11 min, mas à noite o portal reiniciou conexões de `curl` e `urllib` e um ZIP de 91 MB levou 7 min 40 s pelo cliente do fetcher |
| **Siscomex** (Comex) | ⚠️ instável | 2026-10-13 | Falha de verificação do certificado SSL na verificação (`balanca.economia.gov.br`); arquivos GB |
| **PDET FTP** (`ftp.mtps.gov.br`) | ⚠️ intermitente | 2026-10-13 | Cai com frequência (FTP alcançável na verificação); a velocidade oscila de dezenas a centenas de KB/s por conexão (um CAGED de 51 MB levou 1 min 46 s); CAGED schema diferente em 2020+ |
| **Tesouro Nacional RTN** | ✅ estável | 2026-10-13 | Excel multi-aba publicado mensalmente |
| **BCB SGS** (`api.bcb.gov.br` + `www3.bcb.gov.br/sgspub`) | ✅ estável | 2026-10-13 | API JSON de valores estável (200); metadados só via scraping HTML (a árvore de grupos é sequencial; a coleta em lote dos metadados aceita `--workers`); séries diárias truncadas (varredura ano a ano) |
| **INEP** (`download.inep.gov.br`) | ⚠️ não confirmado | 2026-10-13 | Conexão reiniciada pelo servidor na verificação (e falha de handshake TLS com `urllib`). Arquivos muito grandes, preferir download particionado. Revalidar antes de tratar como indisponível |
| **RFB CNPJ** (`arquivos.receitafederal.gov.br`) | ✅ estável, lento | 2026-10-13 | `HEAD` responde 200 e há suporte a `Range`, mas cada requisição leva cerca de 20 s. Referência de 2026-09: 37 ZIPs, 7,8 GB compactados e 28,7 GB descompactados (soma lida do diretório central dos ZIPs). Atualizada mensalmente |
| **ANAC** (`sistemas.anac.gov.br`) | ✅ estável | 2026-10-13 | Arquivos estáticos; schema razoavelmente consistente (arquivo do catálogo responde 200) |
| **ANP** (`gov.br/anp`) | ✅ estável | 2026-10-13 | Arquivos estáticos; atualizados periodicamente (arquivo do catálogo responde) |
| **CVM Dados Abertos** (`dados.cvm.gov.br`) | ✅ estável | 2026-10-13 | Diretório de dados responde 200; cada grupo é um conjunto de CSV/ZIP |
| **TSE ODSele** (`cdn.tse.jus.br`) | ⚠️ não confirmado | 2026-10-13 | Listagem do diretório respondeu 403 na verificação; pode ser bloqueio a clientes sem navegador. Revalidar antes de tratar como indisponível |

**Legenda:**
- ✅ **Estável** — funciona sem intervenção; eventuais 502 curtos são normais.
- ⚠️ **Intermitente** — cai algumas vezes por semana, mas se recupera; retry resolve.
- 🔴 **Fora do ar** — indisponibilidade estendida (mais de 24h).

## Padrões de instabilidade conhecidos

### Horário comercial brasileiro (9h–18h BRT)

A maioria das fontes governamentais tem mais incidentes nesse intervalo. Se possível, agende pipelines pesados para madrugada ou fim de semana.

### Janelas de manutenção

- **IBGE:** sem janela fixa pública; aparecem `502` por 5–30 minutos sem aviso.
- **DATASUS:** atualizações de microdados costumam acontecer entre 22h e 5h, com FTP inacessível.
- **Tesouro:** publicação de novos relatórios às vezes coincide com pico de tráfego.

### Republicações silenciosas

Várias fontes republicam arquivos antigos sem mudar o nome. O manifesto SHA-256 da Quantilica detecta isso automaticamente — veja [Proveniência](concepts/proveniencia.md#detecção-de-mudança-silenciosa).

## Reportar um problema

Encontrou uma fonte fora do ar que esta página marca como estável (ou o contrário)?

- Abra issue em [github.com/Quantilica/.github](https://github.com/Quantilica/.github/issues) com o template `Bug Report`.
- Inclua a URL exata, mensagem de erro e horário aproximado em UTC ou BRT.

---

*Última revisão editorial desta página: 2026-10-13 (verificação ao vivo parcial via HTTP/FTP; linhas não re-verificadas mantêm a data anterior). Cadência pretendida: revisão mensal. Divergências, reporte como descrito acima.*
