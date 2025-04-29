import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from common.models import ArticleModel, MongoDBConnection
from bson import ObjectId

class TestArticleModel:
    def test_create_article(self):
        article = ArticleModel.create_article(
            ticker="AAPL",
            overall_sentiment="Bullish",
            summary="Test summary",
            analysis="Test analysis"
        )
        
        assert article["ticker"] == "AAPL"
        assert isinstance(article["created_at"], datetime)

    def test_get_articles_by_ticker(self):
        mock_collection = MagicMock()
        mock_collection.find.return_value.sort.return_value = [
            {"_id": ObjectId(), "ticker": "AAPL"}
        ]
        
        results = ArticleModel.get_articles_by_ticker(mock_collection, "AAPL")
        assert len(results) == 1
        assert results[0]["ticker"] == "AAPL"

    def test_format_article(self):
        test_article = {
            "_id": ObjectId(),
            "created_at": datetime.utcnow(),
            "ticker": "TSLA"
        }
        
        formatted = ArticleModel.format_article(test_article)
        assert "id" in formatted
        assert isinstance(formatted["created_at"], str)

    @pytest.mark.parametrize("time_range,expected_delta", [
        ("24h", timedelta(hours=24)),
        ("7d", timedelta(days=7)),
        ("30d", timedelta(days=30)),
        (None, None)
    ])
    def test_get_trending_articles(self, time_range, expected_delta):
        mock_collection = MagicMock()
        mock_collection.find.return_value.sort.return_value.limit.return_value = [
            {"_id": ObjectId(), "ticker": "AAPL"}
        ]
        
        results = ArticleModel.get_trending_articles(mock_collection, time_range)
        assert len(results) == 1
        if time_range:
            mock_collection.find.assert_called_with({
                "created_at": {"$gte": pytest.approx(datetime.utcnow() - expected_delta, rel=1)}
            })

class TestMongoDBConnection:
    def test_singleton_pattern(self):
        instance1 = MongoDBConnection()
        instance2 = MongoDBConnection()
        assert instance1 is instance2

    @patch.dict('os.environ', {'MONGO_URI': 'mongodb://test:27017/testdb'})
    def test_connection_with_env(self):
        conn = MongoDBConnection()
        assert conn._client is not None
        assert conn._db.name == "testdb"