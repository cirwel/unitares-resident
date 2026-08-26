# Repository agent contract

- Preserve the external-client boundary in `ARCHITECTURE.md`.
- Do not import `src`, `governance_core`, database drivers, or deployment-local
  UNITARES modules.
- Run `uv run pytest` and `uv run ruff check .` before commit.
- Use a named agent-prefixed branch and a draft pull request.
- Follow the operator's global git closeout contract.
