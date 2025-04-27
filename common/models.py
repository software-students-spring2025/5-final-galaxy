"""
Module for MongoDB models & connection.
"""

import os
from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from bson import ObjectId

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

# Schema and helper functions for the articles collection
class ArticleModel:
    """
    Class for handling article data stored in MongoDB
    """
    @staticmethod
    def create_article(ticker: str, title: str, summary: str, body: str) -> dict:
        """
        Create a new article document
        """
        article = {
            "ticker": ticker.upper(),
            "title": title,
            "summary": summary,
            "body": body,
            "created_at": datetime.utcnow()
        }
        return article
    
    @staticmethod
    def get_articles_by_ticker(collection: Collection, ticker: str) -> list:
        """
        Get all articles for a specific ticker
        """
        return list(collection.find({"ticker": ticker.upper()}).sort("created_at", DESCENDING))
    
    @staticmethod
    def format_article(article: dict) -> dict:
        """
        Format article for API response
        """
        # Convert ObjectId to string for JSON serialization
        if "_id" in article:
            article["id"] = str(article["_id"])
            del article["_id"]
            
        # Format datetime to ISO string for JSON serialization
        if "created_at" in article and isinstance(article["created_at"], datetime):
            article["created_at"] = article["created_at"].isoformat()
            
        return article