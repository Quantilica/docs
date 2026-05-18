---
title: Status das fontes públicas brasileiras
description: Estado de saúde conhecido das fontes oficiais que a Quantilica consome — IBGE, DATASUS, Tesouro, INMET, Comex, PDET.
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
| **IBGE SIDRA** (`apisidra.ibge.gov.br`) | ✅ estável | 2026-05-17 | Rate limit não documentado; preferir horário não-comercial |
| **IBGE Agregados v3** (`servicodados.ibge.gov.br`) | ✅ estável | 2026-05-17 | Janelas curtas de 502 em manutenção |
| **DATASUS FTP** (`ftp.datasus.gov.br`) | ⚠️ intermitente | 2026-05-17 | Cai frequentemente em horário comercial; reduzir `--threads` |
| **Tesouro Transparente CKAN** | ✅ estável | 2026-05-17 | Dataset com timestamp no nome |
| **INMET BDMEP** | ✅ estável | 2026-05-17 | ZIPs por ano; latin-1; valores `-9999` |
| **Siscomex** (Comex) | ⚠️ instável | 2026-05-17 | SSL ruim em janelas curtas; arquivos GB |
| **PDET FTP** (`ftp.mtps.gov.br`) | ⚠️ intermitente | 2026-05-17 | Cai com frequência; CAGED schema diferente em 2020+ |
| **Tesouro Nacional RTN** | ✅ estável | 2026-05-17 | Excel multi-aba publicado mensalmente |

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

*Última atualização manual desta página: 2026-05-17.*
