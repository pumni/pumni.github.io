from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from generate_redirects import MAPPINGS, SITE_ORIGIN, legacy_url  # noqa: E402


def fetch(url: str, timeout: float) -> tuple[int, str]:
    request = Request(url, headers={"User-Agent": "pumni-pages-smoke-test/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except HTTPError as error:
        return error.code, error.read().decode("utf-8", errors="replace")


def check_live_site(timeout: float) -> None:
    for relative_path in sorted(MAPPINGS):
        mapping = MAPPINGS[relative_path]
        legacy = f"{SITE_ORIGIN}{legacy_url(relative_path)}"
        status, body = fetch(legacy, timeout)
        if status != 200:
            raise AssertionError(f"{legacy}: expected 200, got {status}")

        target = mapping["target"]
        expected_signals = (
            f'<link rel="canonical" href="{target}">',
            f'<meta http-equiv="refresh" content="0; url={target}">',
            f"const destination = new URL(\"{target}\");",
            "window.location.replace(destination.href);",
            f'<a href="{target}">',
        )
        for signal in expected_signals:
            if signal not in body:
                raise AssertionError(f"{legacy}: missing expected signal {signal!r}")

        destination_status, _ = fetch(target, timeout)
        if destination_status != 200:
            raise AssertionError(
                f"{target}: expected 200 from redirect destination, got {destination_status}"
            )

    for path in ("/Sky-Player/sitemap.xml", "/robots.txt"):
        url = f"{SITE_ORIGIN}{path}"
        status, body = fetch(url, timeout)
        if status != 200:
            raise AssertionError(f"{url}: expected 200, got {status}")
        if not body.strip():
            raise AssertionError(f"{url}: response body is empty")

    unknown = f"{SITE_ORIGIN}/Sky-Player/__pages_bridge_unknown_path__"
    status, body = fetch(unknown, timeout)
    if status != 404:
        raise AssertionError(f"{unknown}: expected normal 404, got {status}")
    if "Page not found" not in body:
        raise AssertionError(f"{unknown}: custom 404 body was not served")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded live smoke test for the Pages bridge")
    parser.add_argument("--attempts", type=int, default=6)
    parser.add_argument("--delay", type=float, default=10.0)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    if args.attempts < 1 or args.delay < 0 or args.timeout <= 0:
        parser.error("attempts must be positive; delay must be non-negative; timeout must be positive")

    last_error: Exception | None = None
    for attempt in range(1, args.attempts + 1):
        try:
            check_live_site(args.timeout)
            print(f"Live smoke test passed on attempt {attempt}.")
            return 0
        except (AssertionError, OSError, URLError) as error:
            last_error = error
            print(f"Attempt {attempt}/{args.attempts} failed: {error}", file=sys.stderr)
            if attempt < args.attempts:
                time.sleep(args.delay)

    print(f"Live smoke test failed after {args.attempts} attempts: {last_error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
