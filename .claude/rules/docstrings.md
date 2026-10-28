---
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
  - "scripts/**/*.py"
---

# Docstrings

- Use reStructuredText field lists.
- Document every function parameter with `:param <name>:`.
- Add `:return:` whenever the function returns anything other than `None`.
- Add one `:raises <ExceptionType>:` per exception type, after `:return:`.
- Write docstrings and comments in the third person singular, e.g.
  "Fetches the price history" or "Retries on timeout", not the imperative
  ("Fetch", "Retry") or the first person plural ("We retry on timeout").

Example:

```python
def fetch(symbol: str, retries: int = 3) -> list[Price]:
    """
    Fetches the price history for *symbol*.

    :param symbol: Ticker to fetch, exchange suffix included
    :param retries: Number of attempts before giving up
    :return: Price rows, oldest first
    :raises SymbolNotFoundError: If the API reports no such symbol
    :raises RateLimitError: If retries are exhausted while rate limited
    """
```

## Which exceptions to document

- Document what the caller can act on: exceptions raised deliberately, or
  propagating from callees, that a caller would reasonably catch. Skip
  incidental ones such as `TypeError` from bad arguments, unless they are part
  of the contract.
- Phrase each condition starting with "If" or "When".
- Do not document exceptions that are caught and handled internally. If the
  behaviour matters to callers, describe it in the summary instead, e.g.
  "Retries on timeout, up to *retries* times."
- Name the project's own exception classes from `markethistorydb.errors` rather than
  letting `requests` or DB driver exceptions appear in the contract.
- When the set of exceptions is large or unstable, document the base class:
  `:raises MarketHistoryDbError: If any fetch step fails`.
- Errors returned as values (`None`, an error result) belong in `:return:`,
  not `:raises:`.
