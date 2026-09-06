from markethistorydb.db.tables import Table

class TableExchange(Table):
    """Constants for the 'exchange' table."""
    NAME = "exchange"

    class Columns:
        NAME            = "name"           # Full name of the exchange
        EXCHANGE_CODE   = "exchange_code"  # Exchange code used in EODHD APIs
        OPERATING_MIC   = "operating_mic"  # MIC codes for operating venues
        COUNTRY         = "country"        # Country where the exchange operates
        CURRENCY        = "currency"       # Default trading currency
        COUNTRY_ISO_2   = "country_iso_2"  # ISO2 country code
        COUNTRY_ISO_3   = "country_iso_3"  # ISO3 country code
        CREATED_AT      = "created_at"

    # Designated timestamp column
    TIMESTAMP_COLUMN = Columns.CREATED_AT

    # Columns that form the unique/dedup key
    UNIQUE_KEY_COLUMNS = (
        Columns.EXCHANGE_CODE,
    )

    # All columns in definition order
    ALL_COLUMNS = (
        Columns.NAME,
        Columns.EXCHANGE_CODE,
        Columns.OPERATING_MIC,
        Columns.COUNTRY,
        Columns.CURRENCY,
        Columns.COUNTRY_ISO_2,
        Columns.COUNTRY_ISO_3,
        Columns.CREATED_AT,
    )


# Type Hint for table in this class
ExchangeTableType = TableExchange
# Table names
TABLES_NAMES_EXCHANGE = [TableExchange.NAME]