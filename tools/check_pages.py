"""Valida front-matter e o modelo das páginas de fonte.

Regras:
- toda página em docs/ (exceto assets/) tem `title` e `description`;
- `description` entre 50 e 160 caracteres;
- exatamente um H1 fora de blocos de código;
- páginas de coletor (fontes/*/*-fetcher.md) têm as seções "Instalação" e "Saiba mais";
- páginas × registro público, nos dois sentidos: todo coletor com `docs_pasta` tem
  a página fontes/<pasta>/<distribuição>.md, e toda página de coletor é de um
  coletor do registro, na pasta certa;
- os blocos gerados do registro (marcadores `registro:inicio`) estão em dia.

O registro vem do índice público (ou de `REGISTRO_LOCAL`); sem ele a checagem falha.

Uso: uv run python tools/check_pages.py
"""

import re
import sys
from pathlib import Path

from _registro import carrega_hook

DOCS = Path("docs")
REQUIRED_SECTIONS = ("instalação", "saiba mais")


def _split(text: str) -> tuple[dict[str, str], str]:
    m = re.match(r"---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return {}, text
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "-")):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip("\"'")
    return fm, text[m.end() :]


def _headings(body: str) -> list[tuple[int, str]]:
    out, fence = [], False
    for line in body.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fence = not fence
        elif not fence and (m := re.match(r"^(#{1,6})\s+(.*?)\s*#*$", line)):
            out.append((len(m.group(1)), m.group(2).strip("` ")))
    return out


def confere_registro(erros: list[str]) -> None:
    hook = carrega_hook()
    fetchers = hook.carregar_registro()
    grupos = hook.organiza(fetchers, hook.carregar_grupos_do_yml())
    esperadas = {hook._pagina(f) for f in fetchers if f.get("docs_pasta")}
    existentes = {
        p.relative_to(DOCS).as_posix() for p in DOCS.glob("fontes/*/*-fetcher.md")
    }
    for rel in sorted(esperadas - existentes):
        erros.append(f"{rel}: coletor do registro sem página")
    for rel in sorted(existentes - esperadas):
        erros.append(f"{rel}: página de coletor que o registro não tem (ou em outra pasta)")
    for rel in hook.blocos_desatualizados(grupos):
        erros.append(
            f"{rel}: bloco gerado desatualizado (uv run python hooks/registro.py --escrever)"
        )


def main() -> int:
    erros: list[str] = []
    confere_registro(erros)
    for page in sorted(DOCS.rglob("*.md")):
        rel = page.relative_to(DOCS).as_posix()
        fm, body = _split(page.read_text(encoding="utf-8"))
        for key in ("title", "description"):
            if not fm.get(key):
                erros.append(f"{rel}: falta `{key}` no front-matter")
        n = len(fm.get("description", ""))
        if fm.get("description") and not 50 <= n <= 160:
            erros.append(f"{rel}: description com {n} caracteres (esperado 50 a 160)")
        heads = _headings(body)
        h1 = [t for lvl, t in heads if lvl == 1]
        if len(h1) != 1:
            erros.append(f"{rel}: {len(h1)} H1 (esperado 1)")
        if re.fullmatch(r"fontes/[^/]+/[^/]+-fetcher\.md", rel):
            h2 = {t.lower() for lvl, t in heads if lvl == 2}
            for sec in REQUIRED_SECTIONS:
                if sec not in h2:
                    erros.append(f'{rel}: falta a seção H2 "{sec}"')
    for e in erros:
        print(e)
    pages_count = len(list(DOCS.rglob("*.md")))
    print(f"{pages_count} página(s) conferida(s), {len(erros)} problema(s)")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
