"""Creates and manages database for historical exchange market data"""

import logging

from markethistorydb.db import statements, tables, Read, Insert

# Library etiquette: the application decides where log messages go
logging.getLogger(__name__).addHandler(logging.NullHandler())
