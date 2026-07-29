# `pumni.github.io` legacy Pages bridge

This user-site repository restores the former project Pages paths without
recreating `pumni/Sky-Player`. It serves the legacy `/Sky-Player/*` paths and
redirects each known path directly to its equivalent under
`/Sky-Auto-Player/*`.

## Build

```powershell
python generate_redirects.py
```

GitHub Pages should be configured for the `main` branch, repository root.

The bridge uses static client-side redirects because GitHub Pages does not
provide a repository-path HTTP 301/308 configuration. Keep these files for at
least one year, preferably indefinitely, and update public backlinks to point
directly to `/Sky-Auto-Player/`.
