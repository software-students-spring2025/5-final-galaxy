import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
from fastapi.testclient import TestClient
from bson import ObjectId

# Remove the sys.path manipulation that can cause issues with pytest
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock environment variables before imports
with patch.dict(os.environ, {"LLM_API_PROVIDER": "GEMINI", "GEMINI_API_KEY": "fake_key"}):
    # Import the FastAPI app using absolute imports
    from llm import llm_app
    from llm.llm_app import app


class TestLLMApp(unittest.TestCase):
    """Test for the llm_app.py FastAPI application"""
    
    def setUp(self):
        """Set up test client and mocks before each test"""
        self.client = TestClient(app)
    
    @patch('llm.llm_app.analyze_news')
    @patch('llm.llm_app.articles_collection.insert_one')
    def test_analyze_endpoint_success(self, mock_insert_one, mock_analyze_news):
        """Test the /analyze/{ticker} endpoint with successful response"""
        # Setup mock for analyze_news
        mock_model_dump = {
            'ticker': 'AAPL',
            'overall_sentiment': 'Bullish',
            'summary': 'Positive news about Apple.',
            'analysis': '| Time | Headline | Sentiment | Reason | Source |\n|------|---------|-----------|-------|--------|\n| 2023-05-01 14:30 | Apple reports record earnings | Strongly Bullish | Exceeds expectations | Bloomberg |'
        }
        mock_structured_response = MagicMock()
        mock_structured_response.model_dump.return_value = mock_model_dump
        
        mock_analyze_news.return_value = {
            'structured_response': mock_structured_response
        }
        
        # Setup mock for insert_one
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = ObjectId()
        mock_insert_one.return_value = mock_insert_result
        
        # Make the request
        response = self.client.post("/analyze/AAPL")
        
        # Check response
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], "queued")
        self.assertEqual(response.json()["ticker"], "AAPL")
        
        # Assert analyze_news was called with correct ticker
        mock_analyze_news.assert_called_once_with("AAPL")
        
        # Assert insert_one was called
        mock_insert_one.assert_called_once()
        args, kwargs = mock_insert_one.call_args
        article_data = args[0]
        self.assertEqual(article_data['ticker'], 'AAPL')
        self.assertEqual(article_data['overall_sentiment'], 'Bullish')
        self.assertEqual(article_data['summary'], 'Positive news about Apple.')
        self.assertEqual(article_data['analysis'], '| Time | Headline | Sentiment | Reason | Source |\n|------|---------|-----------|-------|--------|\n| 2023-05-01 14:30 | Apple reports record earnings | Strongly Bullish | Exceeds expectations | Bloomberg |')
    
    @patch('llm.llm_app.analyze_news')
    def test_analyze_endpoint_analyze_news_exception(self, mock_analyze_news):
        """Test the /analyze/{ticker} endpoint when analyze_news raises an exception"""
        # Setup mock for analyze_news to raise an exception
        mock_analyze_news.side_effect = Exception("Test exception")
        
        # Make the request
        response = self.client.post("/analyze/AAPL")
        
        # Check response
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Error processing request: Test exception")
        
        # Assert analyze_news was called with correct ticker
        mock_analyze_news.assert_called_once_with("AAPL")
    
    @patch('llm.llm_app.articles_collection.insert_one')
    @patch('llm.llm_app.analyze_news')
    def test_analyze_endpoint_db_exception(self, mock_analyze_news, mock_insert_one):
        """Test the /analyze/{ticker} endpoint when MongoDB insert raises an exception"""
        # Setup mock for analyze_news
        mock_model_dump = {
            'ticker': 'AAPL',
            'overall_sentiment': 'Bullish',
            'summary': 'Positive news about Apple.',
            'analysis': '| Time | Headline | Sentiment | Reason | Source |\n|------|---------|-----------|-------|--------|\n| 2023-05-01 14:30 | Apple reports record earnings | Strongly Bullish | Exceeds expectations | Bloomberg |'
        }
        mock_structured_response = MagicMock()
        mock_structured_response.model_dump.return_value = mock_model_dump
        
        mock_analyze_news.return_value = {
            'structured_response': mock_structured_response
        }
        
        # Setup mock for insert_one to raise a PyMongoError
        from pymongo.errors import PyMongoError
        mock_insert_one.side_effect = PyMongoError("Test DB error")
        
        # Make the request
        response = self.client.post("/analyze/AAPL")
        
        # Check response
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Database error: Test DB error")
        
        # Assert analyze_news was called with correct ticker
        mock_analyze_news.assert_called_once_with("AAPL")
        
        # Assert insert_one was called
        mock_insert_one.assert_called_once()
    
    @patch('llm.llm_app.articles_collection.insert_one')
    @patch('llm.llm_app.analyze_news')
    def test_analyze_endpoint_insert_failure(self, mock_analyze_news, mock_insert_one):
        """Test the /analyze/{ticker} endpoint when MongoDB insert returns no inserted_id"""
        # Setup mock for analyze_news
        mock_model_dump = {
            'ticker': 'AAPL',
            'overall_sentiment': 'Bullish',
            'summary': 'Positive news about Apple.',
            'analysis': '| Time | Headline | Sentiment | Reason | Source |\n|------|---------|-----------|-------|--------|\n| 2023-05-01 14:30 | Apple reports record earnings | Strongly Bullish | Exceeds expectations | Bloomberg |'
        }
        mock_structured_response = MagicMock()
        mock_structured_response.model_dump.return_value = mock_model_dump
        
        mock_analyze_news.return_value = {
            'structured_response': mock_structured_response
        }
        
        # Setup mock for insert_one to return no inserted_id
        mock_insert_result = MagicMock()
        mock_insert_result.inserted_id = None
        mock_insert_one.return_value = mock_insert_result
        
        # Make the request
        response = self.client.post("/analyze/AAPL")
        
        # Check response
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["detail"], "Error processing request: 500: Failed to insert article into database.")
        
        # Assert analyze_news was called with correct ticker
        mock_analyze_news.assert_called_once_with("AAPL")
        
        # Assert insert_one was called
        mock_insert_one.assert_called_once()
    
    @patch('llm.llm_app.conn')
    def test_healthcheck_success(self, mock_conn):
        """Test the /healthz endpoint when MongoDB is reachable"""
        # Setup mock for MongoDB ping
        mock_client = MagicMock()
        mock_admin = MagicMock()
        mock_admin.command.return_value = True
        mock_client.admin = mock_admin
        mock_conn._client = mock_client
        
        # Make the request
        response = self.client.get("/healthz")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["mongo"], "reachable")
        
        # Assert MongoDB ping was called
        mock_admin.command.assert_called_once_with("ping")
    
    @patch('llm.llm_app.conn')
    def test_healthcheck_failure(self, mock_conn):
        """Test the /healthz endpoint when MongoDB is not reachable"""
        # Setup mock for MongoDB ping to raise an exception
        from pymongo.errors import PyMongoError
        mock_client = MagicMock()
        mock_admin = MagicMock()
        mock_admin.command.side_effect = PyMongoError("Test MongoDB error")
        mock_client.admin = mock_admin
        mock_conn._client = mock_client
        
        # Make the request
        response = self.client.get("/healthz")
        
        # Check response
        self.assertEqual(response.status_code, 500)
        self.assertTrue("MongoDB ping failed" in response.json()["detail"])
        
        # Assert MongoDB ping was called
        mock_admin.command.assert_called_once_with("ping")


if __name__ == '__main__':
    unittest.main()