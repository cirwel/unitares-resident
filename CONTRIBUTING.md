# Contributing

Keep Resident an external consumer of UNITARES. New integrations should depend
on `unitares_sdk` or a documented public network endpoint, never server
internals or governance storage.

Before committing:

```bash
uv run pytest
uv run ruff check .
```

Use a `codex/*` or `claude/*` branch, push it, and open a draft pull request.
