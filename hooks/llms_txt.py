"""Gera /llms.txt (índice do site para modelos de linguagem) a partir da navegação.

Formato: https://llmstxt.org/ — título, resumo e listas de links com descrição.
Hook do ProperDocs/MkDocs: não exige plugin extra. A ordem e as seções seguem
a navegação; título e descrição vêm do front-matter de cada página.
"""

from pathlib import Path

_order: list[tuple[str, str]] = []  # (seção, url)
_meta: dict[str, tuple[str, str]] = {}  # url -> (título, descrição)


def _walk(items, section, out):
    for item in items:
        if item.is_page:
            out.append((section, item.url))
        elif item.is_section:
            _walk(item.children, section or item.title, out)


def on_nav(nav, config, files):
    _order.clear()
    _meta.clear()
    _walk(nav.items, "", _order)
    return nav


def on_page_markdown(markdown, page, config, files):
    meta = page.meta or {}
    _meta[page.url] = (meta.get("title") or page.title or page.url, meta.get("description", ""))
    return markdown


def on_post_build(config):
    base = config["site_url"].rstrip("/")
    lines = [
        f"# {config['site_name']}",
        "",
        f"> {config['site_description']}",
        "",
        "Cada fonte tem um coletor próprio, instalado com `quantilica install <fonte>`. "
        "A documentação está em português do Brasil.",
    ]
    current = None
    for section, url in _order:
        title, description = _meta.get(url, (url, ""))
        if section != current:
            lines += ["", f"## {section or 'Início'}", ""]
            current = section
        suffix = f": {description}" if description else ""
        lines.append(f"- [{title}]({base}/{url}){suffix}")
    (Path(config["site_dir"]) / "llms.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
