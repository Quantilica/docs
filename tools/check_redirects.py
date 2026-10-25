"""Confere o mapa de redirects do properdocs.yml contra o site construído.

Uso: uv run properdocs build -d site && uv run python tools/check_redirects.py site
Falha se uma URL antiga não gerou página de redirecionamento ou se o destino não existe.
"""

import re
import sys
from pathlib import Path

import yaml


def _url_dir(md_path: str) -> str:
    p = md_path.removesuffix(".md")
    return p.removesuffix("/index") if p.endswith("/index") else p


def main(site: str) -> int:
    class _Loader(yaml.SafeLoader):
        pass

    # properdocs.yml usa tags python/!ENV; só o bloco de plugins interessa.
    _Loader.add_multi_constructor("", lambda loader, suffix, node: None)
    cfg = yaml.load(Path("properdocs.yml").read_text(encoding="utf-8"), Loader=_Loader)
    maps: dict[str, str] = {}
    for plugin in cfg.get("plugins", []):
        if isinstance(plugin, dict) and "redirects" in plugin:
            maps = plugin["redirects"]["redirect_maps"]
    root = Path(site)
    erros = []
    for old, new in maps.items():
        old_page = root / _url_dir(old) / "index.html"
        new_page = root / _url_dir(new) / "index.html"
        if not old_page.exists():
            erros.append(f"sem redirect gerado: {old}")
        elif not re.search(r"location\.href=", old_page.read_text(encoding="utf-8")):
            erros.append(f"página antiga não redireciona: {old}")
        if not new_page.exists():
            erros.append(f"destino inexistente: {old} -> {new}")
    for e in erros:
        print(e)
    print(f"{len(maps)} redirect(s) conferido(s), {len(erros)} erro(s)")
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "site"))
