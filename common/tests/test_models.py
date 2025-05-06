import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from datetime import datetime, timedelta, timezone
from bson import ObjectId

# Remove the sys.path manipulation that can cause issues with pytest
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use absolute imports instead
from common.models import MongoDBConnection, ArticleModel


class TestMongoDBConnection(unittest.TestCase):
    """Test for the MongoDBConnection class in common/models.py"""
    
    def setUp(self):
        # Reset the singleton instance before each test
        MongoDBConnection._instance = None
        MongoDBConnection._client = None
        MongoDBConnection._db = None
    
    @patch('common.models.MongoClient')
    def test_singleton_pattern(self, mock_mongo_client):
        """Test if MongoDBConnection follows singleton pattern"""
        # Set up return values for the mock
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_mongo_client.return_value = mock_client
        
        # Create two instances of MongoDBConnection
        conn1 = MongoDBConnection()
        conn2 = MongoDBConnection()
        
        # Check if they are the same instance
        self.assertIs(conn1, conn2)
        
        # Check if MongoClient was called only once
        mock_mongo_client.assert_called_once()
    
    @patch('common.models.MongoClient')
    @patch('common.models.os.getenv')
    def test_connect_with_default_uri(self, mock_getenv, mock_mongo_client):
        """Test if _connect method uses default URI when environment variable is not set"""
        # Set up mock for os.getenv to return None for MONGO_URI but use the default
        # Need to simulate os.getenv's default value mechanism, rather than returning None
        def getenv_side_effect(key, default=None):
            if key == "MONGO_URI":
                return default
            return None
        mock_getenv.side_effect = getenv_side_effect
        
        # Set up return values for MongoClient mock
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_db.name = "mydb"
        mock_client.__getitem__.return_value = mock_db
        mock_mongo_client.return_value = mock_client
        
        # Create MongoDBConnection instance
        conn = MongoDBConnection()
        
        # Check if MongoClient was called with default URI
        mock_mongo_client.assert_called_once_with("mongodb://localhost:27017/mydb")
        
        # Check if the database name was accessed correctly
        self.assertEqual(conn._db.name, "mydb")
    
    @patch('common.models.MongoClient')
    @patch('common.models.os.getenv')
    def test_connect_with_custom_uri(self, mock_getenv, mock_mongo_client):
        """Test if _connect method uses custom URI from environment variable"""
        # Set up mock for os.getenv to return custom URI
        mock_getenv.return_value = "mongodb://mongodb:27017/stockDB"
        
        # Set up return values for MongoClient mock
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_db.name = "stockDB"
        mock_client.__getitem__.return_value = mock_db
        mock_mongo_client.return_value = mock_client
        
        # Create MongoDBConnection instance
        conn = MongoDBConnection()
        
        # Check if MongoClient was called with custom URI
        mock_mongo_client.assert_called_once_with("mongodb://mongodb:27017/stockDB")
        
        # Check if the database name was accessed correctly
        self.assertEqual(conn._db.name, "stockDB")
    
    @patch('common.models.MongoClient')
    def test_get_collection(self, mock_mongo_client):
        """Test if get_collection method returns the correct collection"""
        # Set up mock for MongoClient
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_client.__getitem__.return_value = mock_db
        mock_mongo_client.return_value = mock_client
        
        # Create MongoDBConnection instance and get collection
        conn = MongoDBConnection()
        collection = conn.get_collection("test_collection")
        
        # Check if the correct collection was returned
        mock_db.__getitem__.assert_called_with("test_collection")
        self.assertEqual(collection, mock_collection)


class TestArticleModel(unittest.TestCase):
    """Test for the ArticleModel class in common/models.py"""
    
    def test_create_article(self):
        """Test if create_article method creates article document correctly"""
        # Call create_article method
        article = ArticleModel.create_article(
            ticker="aapl",
            overall_sentiment="Bullish",
            summary="Positive news about Apple.",
            analysis="Detailed analysis..."
        )
        
        # Check article fields
        self.assertEqual(article["ticker"], "AAPL")  # Should be uppercase
        self.assertEqual(article["overall_sentiment"], "Bullish")
        self.assertEqual(article["summary"], "Positive news about Apple.")
        self.assertEqual(article["analysis"], "Detailed analysis...")
        self.assertIn("created_at", article)
        self.assertIsInstance(article["created_at"], datetime)
    
    def test_get_articles_by_ticker(self):
        """Test if get_articles_by_ticker method calls find and sort correctly"""
        # Create mock collection
        mock_collection = MagicMock()
        mock_find = MagicMock()
        mock_find.sort.return_value = [{"ticker": "AAPL"}]
        mock_collection.find.return_value = mock_find
        
        # Call get_articles_by_ticker method
        articles = ArticleModel.get_articles_by_ticker(mock_collection, "aapl")
        
        # Check if find was called with correct query
        mock_collection.find.assert_called_once_with({"ticker": "AAPL"})
        
        # Check if sort was called correctly
        mock_find.sort.assert_called_once_with("created_at", -1)  # -1 is DESCENDING
        
        # Check if the result is a list containing the article
        self.assertEqual(articles, [{"ticker": "AAPL"}])
    
    def test_format_article_with_object_id(self):
        """Test if format_article method formats ObjectId correctly"""
        # Create test article with ObjectId
        test_id = ObjectId()
        article = {
            "_id": test_id,
            "ticker": "AAPL",
            "summary": "Test summary"
        }
        
        # Call format_article method
        formatted = ArticleModel.format_article(article)
        
        # Check if _id was converted to string id
        self.assertNotIn("_id", formatted)
        self.assertIn("id", formatted)
        self.assertEqual(formatted["id"], str(test_id))
        
        # Other fields should remain unchanged
        self.assertEqual(formatted["ticker"], "AAPL")
        self.assertEqual(formatted["summary"], "Test summary")
    
    def test_format_article_with_datetime(self):
        """Test if format_article method formats datetime correctly"""
        # Create test article with datetime
        test_dt = datetime(2023, 1, 1, 12, 0, 0)
        article = {
            "ticker": "AAPL",
            "created_at": test_dt
        }
        
        # Call format_article method
        formatted = ArticleModel.format_article(article)
        
        # Check if datetime was converted to ISO string with UTC
        expected_iso = test_dt.replace(tzinfo=timezone.utc).isoformat()
        self.assertEqual(formatted["created_at"], expected_iso)
    
    def test_format_article_with_both_object_id_and_datetime(self):
        """Test if format_article method formats both ObjectId and datetime correctly"""
        # Create test article with both ObjectId and datetime
        test_id = ObjectId()
        test_dt = datetime(2023, 1, 1, 12, 0, 0)
        article = {
            "_id": test_id,
            "ticker": "AAPL",
            "created_at": test_dt
        }
        
        # Call format_article method
        formatted = ArticleModel.format_article(article)
        
        # Check if _id was converted to string id
        self.assertNotIn("_id", formatted)
        self.assertIn("id", formatted)
        self.assertEqual(formatted["id"], str(test_id))
        
        # Check if datetime was converted to ISO string with UTC
        expected_iso = test_dt.replace(tzinfo=timezone.utc).isoformat()
        self.assertEqual(formatted["created_at"], expected_iso)
    
    def test_get_trending_articles_no_time_range(self):
        """Test if get_trending_articles method works with no time range specified"""
        # Create mock collection
        mock_collection = MagicMock()
        mock_find = MagicMock()
        mock_find.sort.return_value = mock_find
        mock_find.limit.return_value = [{"ticker": "AAPL"}, {"ticker": "MSFT"}]
        mock_collection.find.return_value = mock_find
        
        # Call get_trending_articles method with no time range
        articles = ArticleModel.get_trending_articles(mock_collection)
        
        # Check if find was called with empty query
        mock_collection.find.assert_called_once_with({})
        
        # Check if sort and limit were called correctly
        mock_find.sort.assert_called_once_with("created_at", -1)  # -1 is DESCENDING
        mock_find.limit.assert_called_once_with(10)  # Default limit is 10
        
        # Check if the result contains the articles
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]["ticker"], "AAPL")
        self.assertEqual(articles[1]["ticker"], "MSFT")
    
    @patch('common.models.datetime')
    def test_get_trending_articles_with_time_range_24h(self, mock_datetime):
        """Test if get_trending_articles method works with 24h time range"""
        # Set up mock datetime.utcnow
        current_time = datetime(2023, 1, 2, 12, 0, 0)
        mock_datetime.utcnow.return_value = current_time
        
        # Create mock collection
        mock_collection = MagicMock()
        mock_find = MagicMock()
        mock_find.sort.return_value = mock_find
        mock_find.limit.return_value = [{"ticker": "AAPL"}]
        mock_collection.find.return_value = mock_find
        
        # Call get_trending_articles method with 24h time range
        articles = ArticleModel.get_trending_articles(mock_collection, time_range="24h", limit=5)
        
        # Expected time for the query (24 hours ago)
        expected_time = current_time - timedelta(hours=24)
        
        # Check if find was called with the correct time filter
        mock_collection.find.assert_called_once()
        args, kwargs = mock_collection.find.call_args
        query = args[0]
        self.assertIn("created_at", query)
        self.assertIn("$gte", query["created_at"])
        self.assertEqual(query["created_at"]["$gte"], expected_time)
        
        # Check if sort and limit were called correctly
        mock_find.sort.assert_called_once_with("created_at", -1)
        mock_find.limit.assert_called_once_with(5)
    
    @patch('common.models.datetime')
    def test_get_trending_articles_with_time_range_7d(self, mock_datetime):
        """Test if get_trending_articles method works with 7d time range"""
        # Set up mock datetime.utcnow
        current_time = datetime(2023, 1, 10, 12, 0, 0)
        mock_datetime.utcnow.return_value = current_time
        
        # Create mock collection
        mock_collection = MagicMock()
        mock_find = MagicMock()
        mock_find.sort.return_value = mock_find
        mock_find.limit.return_value = [{"ticker": "AAPL"}]
        mock_collection.find.return_value = mock_find
        
        # Call get_trending_articles method with 7d time range
        articles = ArticleModel.get_trending_articles(mock_collection, time_range="7d")
        
        # Expected time for the query (7 days ago)
        expected_time = current_time - timedelta(days=7)
        
        # Check if find was called with the correct time filter
        mock_collection.find.assert_called_once()
        args, kwargs = mock_collection.find.call_args
        query = args[0]
        self.assertIn("created_at", query)
        self.assertIn("$gte", query["created_at"])
        self.assertEqual(query["created_at"]["$gte"], expected_time)
    
    @patch('common.models.datetime')
    def test_get_trending_articles_with_time_range_30d(self, mock_datetime):
        """Test if get_trending_articles method works with 30d time range"""
        # Set up mock datetime.utcnow
        current_time = datetime(2023, 2, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = current_time
        
        # Create mock collection
        mock_collection = MagicMock()
        mock_find = MagicMock()
        mock_find.sort.return_value = mock_find
        mock_find.limit.return_value = [{"ticker": "AAPL"}]
        mock_collection.find.return_value = mock_find
        
        # Call get_trending_articles method with 30d time range
        articles = ArticleModel.get_trending_articles(mock_collection, time_range="30d")
        
        # Expected time for the query (30 days ago)
        expected_time = current_time - timedelta(days=30)
        
        # Check if find was called with the correct time filter
        mock_collection.find.assert_called_once()
        args, kwargs = mock_collection.find.call_args
        query = args[0]
        self.assertIn("created_at", query)
        self.assertIn("$gte", query["created_at"])
        self.assertEqual(query["created_at"]["$gte"], expected_time)
    
    def test_get_trending_articles_with_invalid_time_range(self):
        """Test if get_trending_articles method works with invalid time range"""
        # Create mock collection
        mock_collection = MagicMock()
        mock_find = MagicMock()
        mock_find.sort.return_value = mock_find
        mock_find.limit.return_value = [{"ticker": "AAPL"}]
        mock_collection.find.return_value = mock_find
        
        # Call get_trending_articles method with invalid time range
        articles = ArticleModel.get_trending_articles(mock_collection, time_range="invalid")
        
        # Check if find was called with empty query (invalid time range should be ignored)
        mock_collection.find.assert_called_once_with({})


if __name__ == '__main__':
    unittest.main()