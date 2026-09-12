
"""Global eodhd.com related constants"""

from markethistorydb.utils.env import require_env


# API token for eodhd.com (must be provided via environment, never hardcoded)
API_TOKEN = require_env("EODHD_API_TOKEN")
