# MarketHistoryDB

Creates and manages a QuestDB database for historical exchange market data, fed from eodhd.com.

## Install

```
uv sync            # development (includes pytest, ruff)
pip install .      # as a package
```

Copy `.env.example` to `.env` and fill in `EODHD_API_TOKEN` and `QUESTDB_PASSWORD`.

## CLI usage

```
markethistorydb setup                      # create tables (asks for confirmation)
markethistorydb fetch [--time-frame daily|minute] [--symbol-status active|delisted] [--exchange NAME]
```

Also available as `python -m markethistorydb ...`.

## Library usage

```python
from markethistorydb import Client, Config, TimeFrame

client = Client(Config(eodhd_api_token="...", questdb_password="..."))  # or Client() to read the environment
client.setup()                                   # drops and recreates the tables
client.fetch(TimeFrame.DAILY, exchange="USA Stocks")
df = client.read.ohlcv({"NASDAQ": ["AAPL"]}, TimeFrame.DAILY)
```

Nothing is read from the environment at import time; `Client()` without a config uses
`Config.from_env()` (`EODHD_API_TOKEN`, `QUESTDB_PASSWORD`, optional `QUESTDB_HOST`, ...).
The library never configures logging; add your own handlers. Pass `should_stop=callable` to
`client.fetch` to abort between symbols.

## ToDo-List

- Update project ready for library usage
- Update tests (stale imports)
- Improve test naming
- Implement read/select/query module under markethistorydb
- Implement REST API endpoints for fetch and read functionality
