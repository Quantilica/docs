"""Navegação, tabelas e redirects dos coletores, gerados do registro público.

O registro publicado pelo índice (https://index.quantilica.com/registry.json,
formato 2) é a fonte da identidade de cada coletor: id, distribuição, pasta do
site (`docs_pasta`) e renomes passados (`historico`). Este hook monta a partir
dele, no `on_config`:

- a seção de coletores da navegação (`registro:fetchers` em `nav`), agrupada por
  `docs_pasta`; os títulos de grupo, a ordem dos grupos e as exceções de ordem
  ficam em `extra.fontes_grupos` do properdocs.yml;
- os redirects de páginas renomeadas (`historico`), juntados aos manuais do
  plugin `redirects`;
- os dados dos coletores com `docs/`, lidos pelo hook `dados_fetchers`
  (guardados em `extra.registro_fetchers`).

E, em cada página, os blocos entre marcadores (comentários HTML):

    <!-- registro:inicio tabela-fontes -->   (só em fontes/index.md)
    <!-- registro:inicio coletores -->       (em fontes/<pasta>/index.md)

O arquivo no repositório guarda o bloco gerado (legível no GitHub); o build
sempre o regera em memória, de modo que o site acompanha o registro sem commit.
`tools/check_pages.py` falha se o bloco commitado estiver desatualizado.
Para reescrever os blocos nos arquivos:

    uv run python hooks/registro.py --escrever

Variáveis de ambiente:
    REGISTRO_LOCAL   caminho de um registry.json local (build sem rede).
    REGISTRO_URL     outra URL do registro (padrão: o índice público).

Falha o build se o registro não carregar, se o `sha256` não bater ou se um
coletor aponta para uma `docs_pasta` sem grupo em `extra.fontes_grupos`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

log = logging.getLogger("properdocs.hooks.registro")

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
URL_PADRAO = "https://index.quantilica.com/registry.json"
VERSAO_ESPERADA = 2
SENTINELA_NAV = "registro:fetchers"
GRUPOS_CHAVE = "fontes_grupos"

_BLOCO = re.compile(
    r"<!-- registro:inicio (?P<nome>[\w-]+) -->\n"
    r"(?P<corpo>.*?)"
    r"<!-- registro:fim (?P=nome) -->\n",
    re.S,
)


class RegistroError(RuntimeError):
    """O registro não carregou ou não bate com o docs."""


# ---------------------------------------------------------------- carga


def _sha256(doc: dict) -> str:
    """Mesmo cálculo do índice: `{version, fetchers}` em JSON canônico."""
    canon = json.dumps(
        {"version": doc["version"], "fetchers": doc["fetchers"]},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _baixa(url: str, tentativas: int = 4) -> bytes:
    ultimo: Exception | None = None
    for n in range(tentativas):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "quantilica-docs-build"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - https fixo
                return resp.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            ultimo = exc
            time.sleep(2**n)
    raise RegistroError(f"registro público indisponível em {url}: {ultimo}")


def carregar_registro() -> list[dict]:
    """Lista de coletores do registro (local ou público), validada."""
    local = os.environ.get("REGISTRO_LOCAL")
    if local:
        bruto = Path(local).read_bytes()
        origem = local
    else:
        origem = os.environ.get("REGISTRO_URL", URL_PADRAO)
        bruto = _baixa(origem)
    try:
        doc = json.loads(bruto)
    except ValueError as exc:
        raise RegistroError(f"registro de {origem} não é JSON: {exc}") from exc
    if doc.get("version") != VERSAO_ESPERADA:
        raise RegistroError(
            f"registro de {origem}: formato {doc.get('version')!r}, esperado {VERSAO_ESPERADA}"
        )
    if doc.get("sha256") != _sha256(doc):
        raise RegistroError(f"registro de {origem}: sha256 não bate com o conteúdo")
    fetchers = doc.get("fetchers")
    if not isinstance(fetchers, list) or not fetchers:
        raise RegistroError(f"registro de {origem}: sem coletores")
    for f in fetchers:
        for campo in ("id", "distribution", "nome", "docs_pasta"):
            if campo not in f:
                raise RegistroError(f"registro de {origem}: coletor sem `{campo}`: {f}")
    log.info("registro carregado de %s: %d coletores", origem, len(fetchers))
    return fetchers


# ---------------------------------------------------------------- grupos


def _grupos(config_extra: dict) -> list[dict]:
    grupos = config_extra.get(GRUPOS_CHAVE)
    if not grupos:
        raise RegistroError(f"extra.{GRUPOS_CHAVE} ausente no properdocs.yml")
    return grupos


def _pagina(f: dict) -> str:
    """Caminho da página do coletor, relativo a `docs/`."""
    return f"fontes/{f['docs_pasta']}/{f['distribution']}.md"


def organiza(fetchers: list[dict], grupos: list[dict]) -> list[dict]:
    """Une os grupos do properdocs.yml aos coletores do registro.

    Devolve, na ordem dos grupos, `{**grupo, "fetchers": [...], "itens": [...]}`:
    `itens` é a ordem final da seção (coletores e itens literais da `ordem`);
    os coletores que a `ordem` não cita vão ao fim, por id.
    """
    por_pasta: dict[str, dict[str, dict]] = {}
    for f in fetchers:
        if f.get("docs_pasta"):
            por_pasta.setdefault(f["docs_pasta"], {})[f["id"]] = f
    pastas_conhecidas = {g["pasta"] for g in grupos}
    sem_grupo = sorted(set(por_pasta) - pastas_conhecidas)
    if sem_grupo:
        raise RegistroError(
            f"docs_pasta sem grupo em extra.{GRUPOS_CHAVE}: {', '.join(sem_grupo)}"
        )
    saida = []
    for g in grupos:
        membros = dict(por_pasta.get(g["pasta"], {}))
        if not membros:
            raise RegistroError(f"grupo `{g['pasta']}` sem nenhum coletor no registro")
        itens: list = []
        for entrada in g.get("ordem", []):
            if isinstance(entrada, str):
                if entrada not in membros:
                    # um id renomeado segue valendo na `ordem` pelo apelido
                    entrada = next(
                        (k for k, m in membros.items() if entrada in m.get("aliases", [])),
                        entrada,
                    )
                if entrada not in membros:
                    raise RegistroError(
                        f"`ordem` de `{g['pasta']}` cita `{entrada}`, que não está na pasta"
                    )
                itens.append(membros.pop(entrada))
            else:
                itens.append(entrada)
        itens.extend(membros[k] for k in sorted(membros))
        saida.append(
            {**g, "itens": itens, "fetchers": [i for i in itens if "distribution" in i]}
        )
    return saida


# ---------------------------------------------------------------- navegação


def _nav_do_grupo(g: dict) -> dict:
    itens: list = [f"fontes/{g['pasta']}/index.md"]
    for item in g["itens"]:
        if "distribution" in item:
            itens.append({item["distribution"]: _pagina(item)})
        else:
            itens.append(item)
    return {g["titulo"]: itens}


def monta_nav(nav: list, grupos: list[dict]) -> None:
    """Troca a sentinela `registro:fetchers` pelos grupos de coletores."""

    def _troca(itens: list) -> bool:
        for i, item in enumerate(itens):
            if item == SENTINELA_NAV:
                itens[i : i + 1] = [_nav_do_grupo(g) for g in grupos]
                return True
            if isinstance(item, dict):
                for valor in item.values():
                    if isinstance(valor, list) and _troca(valor):
                        return True
        return False

    if not _troca(nav):
        raise RegistroError(
            f"`{SENTINELA_NAV}` não está na navegação do properdocs.yml"
        )


# ---------------------------------------------------------------- redirects


def redirects_do_historico(fetchers: list[dict]) -> dict[str, str]:
    """Páginas dos nomes antigos -> página atual, pelo `historico` do registro."""
    mapa: dict[str, str] = {}
    for f in fetchers:
        if not f.get("docs_pasta"):
            continue
        for antigo in f.get("historico") or []:
            origem = f"fontes/{f['docs_pasta']}/{antigo['distribution']}.md"
            mapa[origem] = _pagina(f)
    return mapa


def mescla_redirects(
    manuais: dict[str, str], gerados: dict[str, str]
) -> dict[str, str]:
    """Junta os mapas; o mesmo caminho com destinos diferentes é erro."""
    for origem, destino in gerados.items():
        if manuais.get(origem, destino) != destino:
            raise RegistroError(
                f"redirect `{origem}` manual ({manuais[origem]}) difere do histórico ({destino})"
            )
    return {**manuais, **gerados}


# ---------------------------------------------------------------- blocos


def _tabela(grupos: list[dict]) -> str:
    linhas = ["| Domínio | Coletores | Fonte oficial |", "|---|---|---|"]
    for g in grupos:
        links = ", ".join(
            f"[{f['distribution']}]({g['pasta']}/{f['distribution']}.md)"
            for f in g["fetchers"]
        )
        linhas.append(
            f"| [{g['curto']}]({g['pasta']}/index.md) | {links} | {g['fonte']} |"
        )
    return "\n".join(linhas) + "\n"


def _lista_coletores(g: dict) -> str:
    linhas = []
    for f in g["fetchers"]:
        linhas.append(
            f"- **[{f['distribution']}]({f['distribution']}.md)** — {f['nome']}"
        )
    return "\n".join(linhas) + "\n"


def _gerador(rel: str, grupos: list[dict]):
    """Função `nome do bloco -> texto` da página `rel` (relativa a `docs/`)."""
    partes = Path(rel).parts
    if rel == "fontes/index.md":
        return {"tabela-fontes": lambda: _tabela(grupos)}
    if len(partes) == 3 and partes[0] == "fontes" and partes[2] == "index.md":
        g = next((g for g in grupos if g["pasta"] == partes[1]), None)
        if g:
            return {"coletores": lambda: _lista_coletores(g)}
    return {}


def aplica_blocos(texto: str, rel: str, grupos: list[dict], *, marcadores: bool) -> str:
    """Regera os blocos de marcadores da página.

    Com `marcadores=True` (reescrita do arquivo) mantém os comentários; com
    `False` (build) devolve só o conteúdo, de modo que o HTML não os carrega.
    """
    geradores = _gerador(rel, grupos)

    def _sub(m: re.Match) -> str:
        nome = m["nome"]
        if nome not in geradores:
            raise RegistroError(f"{rel}: bloco `{nome}` desconhecido para esta página")
        gerado = "\n" + geradores[nome]() + "\n"
        if not marcadores:
            return gerado
        return (
            f"<!-- registro:inicio {nome} -->\n{gerado}<!-- registro:fim {nome} -->\n"
        )

    return _BLOCO.sub(_sub, texto)


def paginas_com_blocos() -> list[Path]:
    return [
        p
        for p in sorted(DOCS.rglob("*.md"))
        if "<!-- registro:inicio " in p.read_text("utf-8")
    ]


def blocos_desatualizados(grupos: list[dict]) -> list[str]:
    """Páginas cujo bloco commitado difere do gerado (para o `check_pages`)."""
    ruins = []
    for p in paginas_com_blocos():
        rel = p.relative_to(DOCS).as_posix()
        atual = p.read_text("utf-8")
        if aplica_blocos(atual, rel, grupos, marcadores=True) != atual:
            ruins.append(rel)
    return ruins


def escreve_blocos(grupos: list[dict]) -> list[str]:
    mudadas = []
    for p in paginas_com_blocos():
        rel = p.relative_to(DOCS).as_posix()
        atual = p.read_text("utf-8")
        novo = aplica_blocos(atual, rel, grupos, marcadores=True)
        if novo != atual:
            p.write_text(novo, "utf-8")
            mudadas.append(rel)
    return mudadas


# ---------------------------------------------------------------- properdocs


def _yml() -> dict:
    """Lê o properdocs.yml (que usa tags !ENV e !!python) sem resolvê-las."""

    class _Loader(yaml.SafeLoader):
        pass

    _Loader.add_multi_constructor("", lambda loader, suffix, node: None)
    return yaml.load(
        (ROOT / "properdocs.yml").read_text(encoding="utf-8"), Loader=_Loader
    )


def carregar_grupos_do_yml() -> list[dict]:
    return _grupos(_yml().get("extra", {}))


def manuais_do_yml() -> dict[str, str]:
    """`redirect_maps` escritos à mão no properdocs.yml."""
    for plugin in _yml().get("plugins", []):
        if isinstance(plugin, dict) and "redirects" in plugin:
            return dict(plugin["redirects"]["redirect_maps"])
    return {}


def redirects_completos(fetchers: list[dict]) -> dict[str, str]:
    return mescla_redirects(manuais_do_yml(), redirects_do_historico(fetchers))


_estado: dict = {"grupos": None}


def on_config(config):
    fetchers = carregar_registro()
    grupos = organiza(fetchers, _grupos(config["extra"]))
    monta_nav(config["nav"], grupos)
    _estado["grupos"] = grupos

    plugin = config["plugins"].get("redirects")
    if plugin is None:
        raise RegistroError("plugin `redirects` não está habilitado")
    mapa = plugin.config["redirect_maps"]
    plugin.config["redirect_maps"] = mescla_redirects(
        dict(mapa), redirects_do_historico(fetchers)
    )

    # Para o hook dados_fetchers: coletores com página no site.
    config["extra"]["registro_fetchers"] = [f for f in fetchers if f.get("docs_pasta")]
    return config


def on_page_markdown(markdown, page, config, files):
    if "<!-- registro:inicio " not in markdown:
        return markdown
    return aplica_blocos(
        markdown, page.file.src_uri, _estado["grupos"], marcadores=False
    )


if __name__ == "__main__":
    if "--escrever" not in sys.argv:
        sys.exit(__doc__)
    _grupos_yml = organiza(carregar_registro(), carregar_grupos_do_yml())
    _mudadas = escreve_blocos(_grupos_yml)
    print("\n".join(f"reescrito: {m}" for m in _mudadas) or "blocos já em dia")
