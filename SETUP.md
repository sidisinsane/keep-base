# Readme

`uv init --package --python 3.12 --description "Personal wiki tooling." keep`

`uv add ruamel.yaml`

`uv add --dev ruff bandit pytest pytest-cov dprint-py`

```bash
uv run dprint add g-plane/pretty_yaml
uv run dprint add markdown
uv run dprint add json
uv run dprint add toml
```

```text
uv run lint          # check for issues
uv run lint-fix      # fix what can be auto-fixed
uv run format        # format code
uv run test          # run tests with coverage
uv run check         # run everything — good pre-commit gate
```
