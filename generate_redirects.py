from __future__ import annotations

import html
import json
import shutil
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlsplit


REPOSITORY_ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = REPOSITORY_ROOT / "public"
SITE_ORIGIN = "https://pumni.github.io"
CURRENT_SITE_PREFIX = "/Sky-Auto-Player/"
MIGRATION_DATE = "2026-07-29"


class RedirectMapping(TypedDict):
    locale: str
    target: str


# This is the authoritative list of legacy files. The generator and local
# validator both derive their redirect and sitemap expectations from it.
MAPPINGS: dict[str, RedirectMapping] = {
    "Sky-Player/index.html": {
        "locale": "en",
        "target": f"{SITE_ORIGIN}{CURRENT_SITE_PREFIX}",
    },
    "Sky-Player/faq/index.html": {
        "locale": "en",
        "target": f"{SITE_ORIGIN}{CURRENT_SITE_PREFIX}faq/",
    },
    "Sky-Player/faq.html": {
        "locale": "en",
        "target": f"{SITE_ORIGIN}{CURRENT_SITE_PREFIX}faq/",
    },
    "Sky-Player/vi/index.html": {
        "locale": "vi",
        "target": f"{SITE_ORIGIN}{CURRENT_SITE_PREFIX}vi/",
    },
    "Sky-Player/vi/faq/index.html": {
        "locale": "vi",
        "target": f"{SITE_ORIGIN}{CURRENT_SITE_PREFIX}vi/faq/",
    },
    "Sky-Player/vi/faq.html": {
        "locale": "vi",
        "target": f"{SITE_ORIGIN}{CURRENT_SITE_PREFIX}vi/faq/",
    },
}


def validate_mappings() -> None:
    """Reject malformed mapping data before touching generated output."""
    seen_paths: set[str] = set()

    for relative_path, mapping in MAPPINGS.items():
        path = Path(relative_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Mapping path must stay relative: {relative_path}")
        if relative_path in seen_paths:
            raise ValueError(f"Duplicate mapping output path: {relative_path}")
        seen_paths.add(relative_path)

        locale = mapping.get("locale")
        if locale not in {"en", "vi"}:
            raise ValueError(
                f"Unsupported locale for {relative_path}: {locale!r}"
            )

        target = mapping.get("target")
        parsed = urlsplit(target)
        if parsed.scheme != "https" or parsed.netloc != "pumni.github.io":
            raise ValueError(f"Target must use https://pumni.github.io: {target}")
        if not parsed.path.startswith(CURRENT_SITE_PREFIX):
            raise ValueError(
                f"Target must point directly to {CURRENT_SITE_PREFIX}: {target}"
            )
        if parsed.query or parsed.fragment:
            raise ValueError(f"Mapping targets must not contain query or fragment: {target}")


def legacy_url(relative_path: str) -> str:
    """Convert a generated legacy file path to its public URL path."""
    if relative_path.endswith("/index.html"):
        return "/" + relative_path[: -len("index.html")]
    return "/" + relative_path


def redirect_document(language: str, target: str) -> str:
    safe_target = html.escape(target, quote=True)
    js_target = json.dumps(target, ensure_ascii=False)

    if language == "vi":
        title = "Sky Player đã chuyển sang Sky Auto Player"
        heading = "Trang này đã được chuyển"
        message = "Sky Player hiện có tên mới là Sky Auto Player."
        link_text = "Mở Sky Auto Player"
    elif language == "en":
        title = "Sky Player moved to Sky Auto Player"
        heading = "This page has moved"
        message = "Sky Player is now called Sky Auto Player."
        link_text = "Open Sky Auto Player"
    else:
        raise ValueError(f"Unsupported locale: {language!r}")

    return f"""<!doctype html>
<html lang="{language}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html.escape(title)}</title>
    <link rel="canonical" href="{safe_target}">
    <meta http-equiv="refresh" content="0; url={safe_target}">
    <script>
      (() => {{
        const destination = new URL({js_target});
        destination.search = window.location.search;
        destination.hash = window.location.hash;
        window.location.replace(destination.href);
      }})();
    </script>
    <style>
      body {{
        max-width: 44rem;
        margin: 4rem auto;
        padding: 0 1.25rem;
        font-family: system-ui, sans-serif;
        line-height: 1.6;
      }}
    </style>
  </head>
  <body>
    <main>
      <h1>{html.escape(heading)}</h1>
      <p>{html.escape(message)}</p>
      <p><a href="{safe_target}">{html.escape(link_text)}</a></p>
    </main>
  </body>
</html>
"""


def build_old_sitemap() -> str:
    entries = "\n".join(
        f"""  <url>
    <loc>{html.escape(f"{SITE_ORIGIN}{legacy_url(relative_path)}")}</loc>
    <lastmod>{MIGRATION_DATE}</lastmod>
  </url>"""
        for relative_path in sorted(MAPPINGS)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{entries}
</urlset>
"""


def root_placeholder() -> str:
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="robots" content="noindex, follow">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>pumni projects</title>
  </head>
  <body>
    <main><p><a href="/Sky-Auto-Player/">Open Sky Auto Player</a></p></main>
  </body>
</html>
"""


def not_found_page() -> str:
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="robots" content="noindex, follow">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Page not found</title>
  </head>
  <body>
    <main>
      <h1>Page not found</h1>
      <p>The Sky Player project is now named
        <a href="/Sky-Auto-Player/">Sky Auto Player</a>.</p>
    </main>
  </body>
</html>
"""


def robots_file() -> str:
    return f"""User-agent: *
Allow: /

Sitemap: {SITE_ORIGIN}/Sky-Auto-Player/sitemap-index.xml
Sitemap: {SITE_ORIGIN}/Sky-Player/sitemap.xml
"""


def clean_output() -> None:
    """Remove only the contents of the dedicated generated output directory."""
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for child in OUTPUT_ROOT.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def write_text(relative_path: str, content: str) -> None:
    output = OUTPUT_ROOT / relative_path
    if not output.resolve().is_relative_to(OUTPUT_ROOT.resolve()):
        raise ValueError(f"Generated path escapes output directory: {relative_path}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if not content.endswith("\n"):
        content += "\n"
    output.write_text(content, encoding="utf-8", newline="\n")
    print(f"Created public/{relative_path}")


def main() -> None:
    validate_mappings()
    clean_output()

    for relative_path in sorted(MAPPINGS):
        mapping = MAPPINGS[relative_path]
        write_text(
            relative_path,
            redirect_document(mapping["locale"], mapping["target"]),
        )

    write_text(".nojekyll", "\n")
    write_text("index.html", root_placeholder())
    write_text("404.html", not_found_page())
    write_text("robots.txt", robots_file())
    write_text("Sky-Player/sitemap.xml", build_old_sitemap())


if __name__ == "__main__":
    main()
