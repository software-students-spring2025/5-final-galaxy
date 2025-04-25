"""
Module for MongoDB models & connection.
"""

import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database

class MongoDBConnection:
    _instance = None
    _client: MongoClient = None
    _db: Database = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connect()
        return cls._instance

    def _connect(self):
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/mydb")
        # store the client so you can ping it later
        self._client = MongoClient(uri)
        # extract the database name from the URI
        db_name = uri.rsplit('/', 1)[-1]
        self._db = self._client[db_name]

    def get_collection(self, name: str) -> Collection:
        return self._db[name]