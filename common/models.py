"""
Module for MongoDB models & connection.
"""

import os
from datetime import datetime, timedelta, timezone
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
    def create_article(ticker: str, overall_sentiment: str, summary: str, analysis: str) -> dict:
        """
        Create a new article document
        """
        article = {
            "ticker": ticker.upper(),
            "summary": summary,
            "analysis": analysis,
            "overall_sentiment": overall_sentiment,
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
            
        # Format datetime to ISO string with UTC indicator for JSON serialization
        if "created_at" in article and isinstance(article["created_at"], datetime):
            # Ensure the datetime is UTC-aware before formatting
            utc_dt = article["created_at"].replace(tzinfo=timezone.utc)
            article["created_at"] = utc_dt.isoformat()
            
        return article
        
    @staticmethod
    def get_trending_articles(collection: Collection, time_range: str = None, limit: int = 10) -> list:
        """
        Get recent articles based on time range
        
        Args:
            collection: MongoDB collection to query
            time_range: One of "24h", "7d", "30d" or None (for all)
            limit: Maximum number of articles to return (default 10)
        
        Returns:
            List of articles sorted by creation date (most recent first)
        """
        query = {}
        
        # Apply time filter if specified
        if time_range:
            current_time = datetime.utcnow()
            
            if time_range == "24h":
                since = current_time - timedelta(hours=24)
            elif time_range == "7d":
                since = current_time - timedelta(days=7)
            elif time_range == "30d":
                since = current_time - timedelta(days=30)
            else:
                since = None
                
            if since:
                query["created_at"] = {"$gte": since}
        
        # Execute query sorted by time (newest first) with limit
        return list(
            collection.find(query)
            .sort("created_at", DESCENDING)
            .limit(limit)
        )