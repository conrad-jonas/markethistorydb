
"""Bundles the db access interfaces for one configuration"""

from markethistorydb.config    import Config
from markethistorydb.db.io     import Query, Read, Delete, Insert, Update


class Database:
    def __init__(self, config: Config):
        self.query  = Query(config)
        self.read   = Read(self.query)
        self.update = Update(self.query)
        self.delete = Delete(self.query)
        self.insert = Insert(config)
