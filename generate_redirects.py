from __future__ import annotations

import html
import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent

MAPPINGS: dict[str, tuple[str, str]] = {
    "Sky-Player/index.html": (
        "en",
        "https://pumni.github.io/Sky-Auto-Player/",
    ),
    "Sky-Player/faq/index.html": (
        "en",
        "https://pumni.github.io/Sky-Auto-Player/faq/",
    ),
    "Sky-Player/faq.html": (
        "en",
        "https://pumni.github.io/Sky-Auto-Player/faq/",
    ),
    "Sky-Player/vi/index.html": (
        "vi",
        "https://pumni.github.io/Sky-Auto-Player/vi/",
    ),
    "Sky-Player/vi/faq/index.html": (
        "vi",
        "https://pumni.github.io/Sky-Auto-Player/vi/faq/",
    ),
    "Sky-Player/vi/faq.html": (
        "vi",
        "https://pumni.github.io/Sky-Auto-Player/vi/faq/",
    ),
}


def redirect_document(language: str, target: str) -> str:
    safe_target = html.escape(target, quote=True)
    js_target = json.dumps(target)

    if language == "vi":
        title = "Sky Player đã chuyển sang Sky Auto Player"
        heading = "Trang này đã được chuyển"
        message = "Sky Player hiện có tên mới là Sky Auto Player."
        link_text = "Mở Sky Auto Player"
    else:
        title = "Sky Player moved to Sky Auto Player"
        heading = "This page has moved"
        message = "Sky Player is now called Sky Auto Player."
        link_text = "Open Sky Auto Player"

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


def write_text(relative_path: str, content: str) -> None:
    output = ROOT / relative_path
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8", newline="\n")
    print(f"Created {relative_path}")


def build_old_sitemap() -> str:
    old_urls = [
        "https://pumni.github.io/Sky-Player/",
        "https://pumni.github.io/Sky-Player/faq/",
        "https://pumni.github.io/Sky-Player/faq.html",
        "https://pumni.github.io/Sky-Player/vi/",
        "https://pumni.github.io/Sky-Player/vi/faq/",
        "https://pumni.github.io/Sky-Player/vi/faq.html",
    ]

    today = date.today().isoformat()
    entries = "\n".join(
        f"""  <url>
    <loc>{html.escape(url)}</loc>
    <lastmod>{today}</lastmod>
  </url>"""
        for url in old_urls
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{entries}
</urlset>
"""


def main() -> None:
    for relative_path, (language, target) in MAPPINGS.items():
        write_text(relative_path, redirect_document(language, target))

    write_text(".nojekyll", "")
    write_text(
        "index.html",
        """<!doctype html>
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
""",
    )
    write_text(
        "robots.txt",
        """User-agent: *
Allow: /

Sitemap: https://pumni.github.io/Sky-Auto-Player/sitemap-index.xml
Sitemap: https://pumni.github.io/Sky-Player/sitemap.xml
""",
    )
    write_text("Sky-Player/sitemap.xml", build_old_sitemap())
    write_text(
        "404.html",
        """<!doctype html>
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
""",
    )


if __name__ == "__main__":
    main()
