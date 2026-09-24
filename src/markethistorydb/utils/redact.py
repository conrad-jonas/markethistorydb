
"""Masking of the eodhd.com API token in text that may end up in logs or error messages"""

import re


# Matches the value of the eodhd.com API token, both in a query string (api_token=...) and in a
# dict repr ('api_token': '...'). requests puts the full URL, token included, into the message
# of e.g. a ConnectionError, so the token can surface in any error message or traceback.
_API_TOKEN_PATTERN = re.compile(r"""(api_token['"]?\s*[=:]\s*['"]?)[^&\s'",)}]+""")
# Stands in for the masked token
REDACTED = "***"


def redact_api_token(text: str) -> str:
    """
    Masks every API token in *text*.

    :param text: Text that may hold the API token
    :return: *text* with the value of every API token replaced by REDACTED
    """
    return _API_TOKEN_PATTERN.sub(r"\g<1>" + REDACTED, text)
