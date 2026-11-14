"""Importa a documentação dos dados dos fetchers para o site.

Norma: docs/normas/documentacao-dados.md. Cada fetcher guarda em `docs/` a
documentação dos dados que baixa (README.md, datasets/<id>.md e
datasets/<id>.schema.json). O site lê esses arquivos do repositório do fetcher,
na tag da última versão lançada, e os publica ao lado da página do coletor:

    <destino>/index.md              <- docs/README.md
    <destino>/datasets/<id>.md      <- docs/datasets/<id>.md
    <destino>/datasets/<id>.schema.json

Os fetchers a importar saem do registro público (hooks/registro.py): todo
coletor com página no site é tentado, e os que não têm `docs/README.md` na
última tag (ainda sem a documentação dos dados) ficam de fora sem aviso. A página do
coletor vira uma seção da navegação, com "Dados" e um item por dataset.

Variáveis de ambiente:
    DADOS_FETCHERS_LOCAL   pasta com cópias locais dos repositórios (prévia de
                           alterações ainda sem release); não usa rede.
    DADOS_FETCHERS_STRICT  "1": falha o build se um fetcher não puder ser lido
                           (padrão no CI). Sem ela, avisa e publica sem os dados.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path

import yaml
from properdocs.structure.files import File

log = logging.getLogger("properdocs.hooks.dados_fetchers")

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "dados-fetchers"
ORG_URL = "https://github.com/Quantilica"
_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")

# (coletor, [(src_uri no site, conteúdo texto | Path binário)], navegação)
_importados: list[tuple[dict, list[tuple[str, str | Path]], list]] = []


def _strict() -> bool:
    return os.environ.get("DADOS_FETCHERS_STRICT") == "1"


def ultima_tag(repo: str) -> str:
    """Maior tag `vX.Y.Z` do repositório (versões finais, sem pré-lançamento)."""
    out = subprocess.run(
        ["git", "ls-remote", "--tags", "--refs", f"{ORG_URL}/{repo}.git", "v*"],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout
    tags = []
    for line in out.splitlines():
        name = line.split("refs/tags/")[-1]
        if m := _TAG.match(name):
            tags.append((tuple(int(x) for x in m.groups()), name))
    if not tags:
        raise RuntimeError(f"{repo}: nenhuma tag vX.Y.Z")
    return max(tags)[1]


def _docs_do_fetcher(repo: str) -> tuple[Path, str] | None:
    """Pasta `docs/` do fetcher e a versão (tag) lida; None se não tem `docs/`."""
    local = os.environ.get("DADOS_FETCHERS_LOCAL")
    if local:
        docs = Path(local) / repo / "docs"
        return (docs, "local") if docs.is_dir() else None
    tag = ultima_tag(repo)
    destino = CACHE / f"{repo}@{tag}"
    if not destino.is_dir():
        destino.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--quiet", "--depth", "1", "--branch", tag,
             f"{ORG_URL}/{repo}.git", str(destino)],
            check=True,
            timeout=300,
        )
    return (destino / "docs", tag) if (destino / "docs").is_dir() else None


def _separa(texto: str) -> tuple[dict, str]:
    m = re.match(r"---\n(.*?)\n---\n?", texto, re.S)
    if not m:
        return {}, texto
    return yaml.safe_load(m.group(1)) or {}, texto[m.end():]


def _recorta(texto: str, limite: int = 160) -> str:
    texto = " ".join(texto.split())
    if len(texto) <= limite:
        return texto
    return texto[: limite - 1].rsplit(" ", 1)[0].rstrip(",;:.") + "…"


def _com_front_matter(texto: str, titulo: str, descricao: str) -> str:
    """Acrescenta title/description ao cabeçalho da página (a norma usa `dataset:`)."""
    meta, corpo = _separa(texto)
    meta = {"title": titulo, "description": _recorta(descricao), **meta}
    cab = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=10_000)
    return f"---\n{cab}---\n\n{corpo.lstrip()}"


def _primeiro_paragrafo(corpo: str) -> str:
    for bloco in corpo.split("\n\n"):
        bloco = bloco.strip()
        if bloco and not bloco.startswith(("#", "|", "-", "!", "<")):
            return bloco
    return ""


def _importa(entrada: dict) -> tuple[list[tuple[str, str | Path]], list] | None:
    repo = entrada["repo"]
    achado = _docs_do_fetcher(repo)
    if achado is None:
        log.info("%s: sem docs/ na última versão, nada a importar", repo)
        return None
    docs, tag = achado
    if not (docs / "README.md").is_file():
        # A norma exige docs/README.md; sem ele a documentação ainda não foi adotada.
        log.info("%s (%s): docs/ sem README.md, nada a importar", repo, tag)
        return None
    destino = entrada["destino"].strip("/")
    arquivos: list[tuple[str, str | Path]] = []
    nav_datasets: list = []

    meta, corpo = _separa((docs / "README.md").read_text(encoding="utf-8"))
    titulo_ini = f"Dados do {repo}"
    h1 = re.search(r"^# (.+)$", corpo, re.M)
    arquivos.append((
        f"{destino}/index.md",
        _com_front_matter(
            (docs / "README.md").read_text(encoding="utf-8"),
            (h1.group(1).replace("`", "") if h1 else titulo_ini),
            _primeiro_paragrafo(corpo) or titulo_ini,
        ),
    ))

    for pagina in sorted((docs / "datasets").glob("*.md")):
        meta, _ = _separa(pagina.read_text(encoding="utf-8"))
        ds = meta.get("dataset") or {}
        titulo = ds.get("titulo") or pagina.stem
        arquivos.append((
            f"{destino}/datasets/{pagina.name}",
            _com_front_matter(
                pagina.read_text(encoding="utf-8"), titulo, ds.get("resumo", titulo)
            ),
        ))
        nav_datasets.append({titulo: f"{destino}/datasets/{pagina.name}"})
    for esquema in sorted((docs / "datasets").glob("*.schema.json")):
        arquivos.append((f"{destino}/datasets/{esquema.name}", esquema))

    log.info("dados do %s importados da versão %s (%d arquivos)", repo, tag, len(arquivos))
    nav = [{"Visão geral": f"{destino}/index.md"}, *nav_datasets]
    return arquivos, nav


def _insere_na_nav(itens: list, pagina: str, nav_dados: list) -> bool:
    """Troca a folha `pagina` por uma seção: a página do coletor + "Dados"."""
    for item in itens:
        if isinstance(item, dict):
            for titulo, valor in item.items():
                if valor == pagina:
                    item[titulo] = [pagina, {"Dados": nav_dados}]
                    return True
                if isinstance(valor, list) and _insere_na_nav(valor, pagina, nav_dados):
                    return True
    return False


def _entradas(config) -> list[dict]:
    """Um coletor por entrada do registro que tem página no site."""
    fetchers = config["extra"].get("registro_fetchers")
    if not fetchers:
        raise RuntimeError(
            "registro dos coletores não carregado: hooks/registro.py deve vir "
            "antes de dados_fetchers.py em `hooks`"
        )
    entradas = []
    for f in fetchers:
        pasta, dist = f["docs_pasta"], f["distribution"]
        entradas.append({
            "repo": f["repo"].rstrip("/").rsplit("/", 1)[-1],
            "pagina": f"fontes/{pasta}/{dist}.md",
            "destino": f"fontes/{pasta}/{dist}/dados",
        })
    return entradas


def on_config(config):
    _importados.clear()
    for entrada in _entradas(config):
        try:
            importado = _importa(entrada)
        except Exception as exc:  # noqa: BLE001 - rede, git ou formato
            if _strict():
                raise
            log.warning("dados do %s não importados: %s", entrada["repo"], exc)
            continue
        if importado is None:
            continue
        arquivos, nav = importado
        if not _insere_na_nav(config["nav"], entrada["pagina"], nav):
            raise RuntimeError(
                f"{entrada['repo']}: página {entrada['pagina']} não está na navegação"
            )
        _importados.append((entrada, arquivos, nav))
    return config


def on_files(files, config):
    for _entrada, arquivos, _nav in _importados:
        for src_uri, conteudo in arquivos:
            if isinstance(conteudo, Path):
                arq = File.generated(config, src_uri, abs_src_path=str(conteudo))
            else:
                arq = File.generated(config, src_uri, content=conteudo)
            files.append(arq)
    return files
