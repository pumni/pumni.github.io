from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from generate_redirects import (  # noqa: E402
    MAPPINGS,
    MIGRATION_DATE,
    OUTPUT_ROOT,
    SITE_ORIGIN,
    legacy_url,
    validate_mappings,
)


SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
UNEXPECTED_HOST_RE = re.compile(r"https?://[^\s\"'<>]+")


class DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_lang: str | None = None
        self.links: list[dict[str, str]] = []
        self.metas: list[dict[str, str]] = []
        self.scripts: list[str] = []
        self._script_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): value or "" for name, value in attrs}
        tag = tag.lower()
        if tag == "html":
            self.html_lang = values.get("lang")
        elif tag == "a":
            self.links.append(values)
        elif tag == "link":
            self.links.append(values)
        elif tag == "meta":
            self.metas.append(values)
        elif tag == "script":
            self._script_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._script_parts is not None:
            self.scripts.append("".join(self._script_parts))
            self._script_parts = None

    def handle_data(self, data: str) -> None:
        if self._script_parts is not None:
            self._script_parts.append(data)


def fail(message: str) -> None:
    raise AssertionError(message)


def parse_document(path: Path) -> tuple[str, DocumentParser]:
    if not path.is_file():
        fail(f"Missing generated file: {path.relative_to(REPOSITORY_ROOT)}")
    content = path.read_text(encoding="utf-8")
    if not content.endswith("\n"):
        fail(f"Generated file has no trailing newline: {path}")
    parser = DocumentParser()
    parser.feed(content)
    parser.close()
    return content, parser


def expected_file_for_url(url: str) -> Path:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "pumni.github.io":
        fail(f"Sitemap URL has an unexpected origin: {url}")
    path = parsed.path.lstrip("/")
    if path.endswith("/"):
        path += "index.html"
    return OUTPUT_ROOT / path


def validate_redirect(relative_path: str, locale: str, target: str) -> None:
    path = OUTPUT_ROOT / relative_path
    content, parser = parse_document(path)

    if parser.html_lang != locale:
        fail(f"{relative_path}: expected html lang={locale!r}, got {parser.html_lang!r}")
    if "noindex" in content.lower():
        fail(f"{relative_path}: redirect pages must remain crawlable")

    canonical = [
        link.get("href")
        for link in parser.links
        if link.get("rel", "").lower() == "canonical"
    ]
    if canonical != [target]:
        fail(f"{relative_path}: canonical must be exactly {target!r}")

    refresh = [
        meta.get("content")
        for meta in parser.metas
        if meta.get("http-equiv", "").lower() == "refresh"
    ]
    expected_refresh = f"0; url={target}"
    if refresh != [expected_refresh]:
        fail(f"{relative_path}: meta refresh must be exactly {expected_refresh!r}")

    scripts = "\n".join(parser.scripts)
    if "window.location.replace(destination.href);" not in scripts:
        fail(f"{relative_path}: missing window.location.replace(destination.href)")
    if "destination.search = window.location.search;" not in scripts:
        fail(f"{relative_path}: query-string preservation is missing")
    if "destination.hash = window.location.hash;" not in scripts:
        fail(f"{relative_path}: fragment preservation is missing")

    javascript_targets = re.findall(
        r"new URL\((\"(?:[^\"\\]|\\.)*\")\)", scripts
    )
    if len(javascript_targets) != 1:
        fail(f"{relative_path}: expected one JavaScript destination")
    if javascript_targets[0][1:-1].replace('\\"', '"') != target:
        fail(f"{relative_path}: JavaScript destination must be exactly {target!r}")

    visible_links = [
        link.get("href")
        for link in parser.links
        if "href" in link and link.get("rel", "").lower() != "canonical"
    ]
    if target not in visible_links:
        fail(f"{relative_path}: missing visible link to {target}")


def validate_special_pages() -> None:
    for filename in ("index.html", "404.html"):
        _, parser = parse_document(OUTPUT_ROOT / filename)
        robots = [
            meta.get("content", "").lower()
            for meta in parser.metas
            if meta.get("name", "").lower() == "robots"
        ]
        if robots != ["noindex, follow"]:
            fail(f"{filename}: expected robots metadata noindex, follow")

    four_oh_four, parser = parse_document(OUTPUT_ROOT / "404.html")
    if "window.location.replace" in four_oh_four or "http-equiv=\"refresh\"" in four_oh_four:
        fail("404.html must remain a normal non-redirecting custom 404 page")
    if not any(link.get("href") == "/Sky-Auto-Player/" for link in parser.links):
        fail("404.html must link to the current project site")


def validate_robots() -> None:
    path = OUTPUT_ROOT / "robots.txt"
    content, _ = parse_document(path)
    if "User-agent: *" not in content or "Allow: /" not in content:
        fail("robots.txt must allow crawling")
    if re.search(r"^\s*Disallow:\s*/Sky-Player/", content, re.IGNORECASE | re.MULTILINE):
        fail("robots.txt must not block /Sky-Player/")
    expected_sitemaps = {
        f"Sitemap: {SITE_ORIGIN}/Sky-Auto-Player/sitemap-index.xml",
        f"Sitemap: {SITE_ORIGIN}/Sky-Player/sitemap.xml",
    }
    if not expected_sitemaps.issubset(set(content.splitlines())):
        fail("robots.txt must reference both current and legacy sitemaps")


def validate_sitemap() -> None:
    path = OUTPUT_ROOT / "Sky-Player/sitemap.xml"
    content, _ = parse_document(path)
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        fail(f"Sky-Player/sitemap.xml is not valid XML: {error}")

    if root.tag != f"{{{SITEMAP_NAMESPACE}}}urlset":
        fail("Sky-Player/sitemap.xml has an unexpected root element")

    urls: list[str] = []
    for url_node in root.findall(f"{{{SITEMAP_NAMESPACE}}}url"):
        loc = url_node.find(f"{{{SITEMAP_NAMESPACE}}}loc")
        lastmod = url_node.find(f"{{{SITEMAP_NAMESPACE}}}lastmod")
        if loc is None or loc.text is None:
            fail("Sitemap contains a URL without a loc")
        if lastmod is None or lastmod.text != MIGRATION_DATE:
            fail(f"Sitemap lastmod must be the stable migration date {MIGRATION_DATE}")
        urls.append(loc.text)

    expected_urls = [
        f"{SITE_ORIGIN}{legacy_url(relative_path)}"
        for relative_path in sorted(MAPPINGS)
    ]
    if urls != expected_urls:
        fail("Sitemap URLs are out of sync with the authoritative redirect mappings")
    if len(urls) != len(set(urls)):
        fail("Sitemap contains duplicate URLs")

    for url in urls:
        expected_file = expected_file_for_url(url)
        if not expected_file.is_file():
            fail(f"Sitemap URL has no generated page: {url}")


def validate_public_surface() -> None:
    expected = {
        ".nojekyll",
        "404.html",
        "index.html",
        "robots.txt",
        "Sky-Player/sitemap.xml",
        *MAPPINGS,
    }
    actual = {
        path.relative_to(OUTPUT_ROOT).as_posix()
        for path in OUTPUT_ROOT.rglob("*")
        if path.is_file()
    }
    if actual != expected:
        fail(f"public/ contains unexpected or missing files: expected {expected}, got {actual}")


def validate_generated_hostnames() -> None:
    allowed_hosts = {"pumni.github.io", "www.sitemaps.org"}
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.name == ".nojekyll":
            continue
        content = path.read_text(encoding="utf-8")
        relative_path = path.relative_to(REPOSITORY_ROOT).as_posix()
        for match in UNEXPECTED_HOST_RE.findall(content):
            hostname = urlsplit(match.rstrip(".,)")).netloc
            if hostname not in allowed_hosts:
                fail(f"{relative_path}: unintended hostname in generated content: {match}")


def main() -> int:
    validate_mappings()
    validate_public_surface()
    validate_generated_hostnames()
    for relative_path in sorted(MAPPINGS):
        mapping = MAPPINGS[relative_path]
        validate_redirect(relative_path, mapping["locale"], mapping["target"])
    validate_special_pages()
    validate_robots()
    validate_sitemap()
    print(f"Validated {len(MAPPINGS)} redirect pages and deterministic sitemap metadata.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, ValueError) as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
