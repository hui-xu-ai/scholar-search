# Contributing

## Quick start

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -e ".[dev]"
pre-commit install
pytest -m "not e2e"
```

## Red lines

These are not style preferences. A pull request that crosses them is rejected.

1. No download functionality, in any form.
2. No captcha solving, no retry after a risk signal.
3. No weakening of the hard limits in `core/config.py` without a new ADR.
4. No new browser verb without an ADR and updates to host + extension.
5. No credentials, cookies, or real session data in the repository or fixtures.

## Adding a channel

See `docs/channel-contract.md`. A channel is a directory plus a manifest; it
must pass `tests/contract/` before the registry will load it.

## Commits

Conventional Commits. One logical change per commit. Tests and docs travel
with the code they describe.

## Pull requests

- Describe the user-visible change and the risk impact.
- State which verification level you ran: unit / contract / live.
- Live tests are never required in CI and must not run there.
