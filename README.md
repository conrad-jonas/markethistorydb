# MarketHistoryDB

Creates and manages a QuestDB database for historical exchange market data, fed from eodhd.com.

## Install

```
uv sync            # development (includes pytest, ruff)
pip install .      # as a package
```

Copy `.env.example` to `.env` and fill in `EODHD_API_TOKEN` and `QUESTDB_PASSWORD`.

## Usage

```
markethistorydb setup                      # create tables (asks for confirmation)
markethistorydb fetch [--time-frame daily|minute] [--symbol-status active|delisted] [--exchange NAME]
```

Also available as `python -m markethistorydb ...`.

## ToDo

- Update tests (stale imports)
- Improve test naming
