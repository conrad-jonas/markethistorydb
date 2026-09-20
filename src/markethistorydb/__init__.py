"""Creates and manages database for historical exchange market data"""

import logging

from markethistorydb.client           import Client
from markethistorydb.config           import Config
from markethistorydb.utils import TimeFrame, SymbolStatus

# Library etiquette: the application decides where log messages go
logging.getLogger(__name__).addHandler(logging.NullHandler())
