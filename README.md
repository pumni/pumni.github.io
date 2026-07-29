# `pumni.github.io` legacy Pages bridge

## Purpose

This repository preserves the legacy GitHub Pages URLs from the rename of Sky
Player to Sky Auto Player. It serves the known `/Sky-Player/*` pages as static
HTML redirects to their page-equivalent `/Sky-Auto-Player/*` destinations.

The repository-level GitHub rename redirect is also important: never recreate
`pumni/Sky-Player`. The old repository name must remain available for GitHub's
redirect to `pumni/Sky-Auto-Player`.

## Architecture

```text
pumni/pumni.github.io
→ serves root-level files and /Sky-Player/* redirects

pumni/Sky-Auto-Player
→ serves /Sky-Auto-Player/*
```

`generate_redirects.py` writes the complete Pages artifact to `public/`.
Generated files are committed, and CI regenerates them and fails if
`public/` changes. GitHub Actions uploads only `public/`; source files,
documentation, and workflow files are never deployed.

The six authoritative mappings live in `MAPPINGS` in
`generate_redirects.py`. Redirect pages, the legacy sitemap, and local
validation expectations derive from that structure.

## Migration invariants

- Never create or reuse `pumni/Sky-Player`.
- Do not change the six page-equivalent redirect destinations.
- Never add `noindex` to a `/Sky-Player/` redirect page.
- Never block `/Sky-Player/` in `robots.txt`; crawlers must observe the
  redirect and canonical signals.
- Never redirect unrelated or unknown paths to the homepage. Unknown paths
  must remain normal GitHub Pages 404 responses using `404.html`.
- Preserve query strings and fragments in JavaScript navigation.
- Keep canonical, meta-refresh, JavaScript, and visible-link destinations in
  agreement, using HTTPS and no intermediate URL.
- Keep redirects for at least one year, preferably indefinitely.
- Do not remove the legacy sitemap until the migration is stable in Search
  Console.
- Update `MIGRATION_DATE` only when a redirect mapping or migration document
  genuinely changes. It is intentionally not the generator execution date.

The root placeholder and custom 404 page may use `noindex, follow`; legacy
redirect pages must remain crawlable.

## Development

```bash
python generate_redirects.py
python scripts/validate_redirects.py
```

Generation is idempotent and cleans only generated contents inside `public/`.
The validator checks all six mappings, HTML redirect signals, languages,
query/fragment preservation, crawl directives, sitemap XML and synchronization,
hostnames, HTTPS targets, and the minimal public surface.

For a bounded live check after deployment:

```bash
python scripts/smoke_test.py
```

The smoke test checks all legacy URLs, both sitemap/robots resources, every
destination, and one unknown path. It retries at most six times with a
10-second delay to allow for CDN propagation.

## Deployment

`.github/workflows/pages.yml` runs generation, local validation, and the
stale-generated-output check on relevant pull requests and pushes to `main`.
Pull requests stop after artifact validation; pushes and manual dispatches
deploy the `public/` directory with the official GitHub Pages actions, then
run a separate bounded live verification job.

In repository settings, GitHub Pages must use:

```text
Settings → Pages → Build and deployment → Source: GitHub Actions
```

Do not use `Deploy from a branch` with `main / root`; that bypasses the
`public/` artifact and leaves the legacy URLs unavailable. After changing the
source, confirm the `Deploy legacy Pages bridge` workflow has successful
`Generate and validate Pages artifact`, `Deploy Pages artifact`, and `Verify
live Pages bridge` jobs.

This repository intentionally does not add Playwright: it would add a browser
runtime and dependency maintenance for six static redirect pages. The local
validator provides a browser-independent check of the generated JavaScript,
and the live smoke test covers the English and Vietnamese FAQ routes. For the
browser acceptance check, open a browser console or navigate directly to:

```text
https://pumni.github.io/Sky-Player/?utm_source=acceptance#download
```

The final address must be:

```text
https://pumni.github.io/Sky-Auto-Player/?utm_source=acceptance#download
```

Also verify one English FAQ route and one Vietnamese FAQ route, and inspect
the generated source with:

```text
view-source:https://pumni.github.io/Sky-Player/
```

It must show the canonical link, meta refresh, `window.location.replace`, and
the visible destination link.
