import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from bson import ObjectId
import requests
import sys
import os
from pymongo.errors import PyMongoError

# Add parent directory to sys.path to ensure we can import modules from web-app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import app module
from app import app as fastapi_app

class TestWebApp(unittest.TestCase):
    """Test for the web-app/app.py FastAPI application without template rendering"""
    
    def setUp(self):
        """Set up test client and mocks before each test"""
        self.client = TestClient(fastapi_app)
    
    @patch('fastapi.templating.Jinja2Templates.TemplateResponse')
    def test_get_dashboard(self, mock_template_response):
        """Test the / endpoint (dashboard)"""
        # Set mock return value
        mock_template_response.return_value = HTMLResponse(content="<html>Dashboard</html>")
        
        # Make request
        response = self.client.get("/")
        
        # Verify status code
        self.assertEqual(response.status_code, 200)
        
        # Verify template function was called
        mock_template_response.assert_called_once()
        args, kwargs = mock_template_response.call_args
        self.assertEqual(args[0], "index.html")
    
    @patch('fastapi.templating.Jinja2Templates.TemplateResponse')
    def test_get_trending_page(self, mock_template_response):
        """Test the /trending endpoint"""
        # Set mock return value
        mock_template_response.return_value = HTMLResponse(content="<html>Trending</html>")
        
        # Make request
        response = self.client.get("/trending")
        
        # Verify status code
        self.assertEqual(response.status_code, 200)
        
        # Verify template function was called
        mock_template_response.assert_called_once()
        args, kwargs = mock_template_response.call_args
        self.assertEqual(args[0], "trending.html")
    
    @patch('fastapi.templating.Jinja2Templates.TemplateResponse')
    def test_get_detail_page_with_ticker(self, mock_template_response):
        """Test the /detail endpoint with a ticker parameter"""
        # Set mock return value
        mock_template_response.return_value = HTMLResponse(content="<html>Detail</html>")
        
        # Make request
        response = self.client.get("/detail?ticker=AAPL")
        
        # Verify status code
        self.assertEqual(response.status_code, 200)
        
        # Verify template function was called
        mock_template_response.assert_called_once()
        args, kwargs = mock_template_response.call_args
        self.assertEqual(args[0], "detail.html")
    
    def test_get_detail_page_without_ticker(self):
        """Test the /detail endpoint without a ticker parameter (should redirect to root)"""
        response = self.client.get("/detail", follow_redirects=False)
        self.assertEqual(response.status_code, 307)  # Temporary redirect
        self.assertEqual(response.headers["location"], "/")
    
    @patch('app.requests.post')
    def test_trigger_analysis_success(self, mock_post):
        """Test the /analyze/{ticker} endpoint with successful LLM service response"""
        # Setup mock for LLM service response
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "status": "queued",
            "message": "Analysis for AAPL initiated."
        }
        mock_post.return_value = mock_response
        
        # Make the request
        response = self.client.post("/analyze/AAPL")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json["status"], "queued")
        self.assertEqual(response_json["ticker"], "AAPL")
        self.assertEqual(response_json["redirect_to"], "/detail?ticker=AAPL")
        
        # Assert that requests.post was called with the correct URL
        mock_post.assert_called_once_with("http://llm:5002/analyze/AAPL")
    
    @patch('app.requests.post')
    def test_trigger_analysis_llm_error(self, mock_post):
        """Test the /analyze/{ticker} endpoint with error from LLM service"""
        # Setup mock for LLM service response with non-202 status
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        # Make the request
        response = self.client.post("/analyze/AAPL")
        
        # Check response
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "LLM service error")
        
        # Assert that requests.post was called
        mock_post.assert_called_once_with("http://llm:5002/analyze/AAPL")
    
    @patch('app.requests.post')
    def test_trigger_analysis_request_exception(self, mock_post):
        """Test the /analyze/{ticker} endpoint when requests.post raises an exception"""
        # Setup mock for requests.post to raise an exception
        mock_post.side_effect = requests.RequestException("Connection error")
        
        # Make the request
        response = self.client.post("/analyze/AAPL")
        
        # Check response
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "LLM service request failed: Connection error")
        
        # Assert that requests.post was called
        mock_post.assert_called_once_with("http://llm:5002/analyze/AAPL")

    @patch('app.ArticleModel.get_articles_by_ticker')
    def test_get_articles_success(self, mock_get_articles):
        """Test the /articles/{ticker} endpoint with successful database response"""
        # Setup mock data
        mock_articles = [
            {
                "_id": ObjectId(),
                "ticker": "AAPL",
                "summary": "Test summary",
                "overall_sentiment": "Bullish",
                "created_at": datetime.now()
            }
        ]
        mock_get_articles.return_value = mock_articles
        
        # Make the request
        response = self.client.get("/articles/AAPL")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json["ticker"], "AAPL")
        self.assertEqual(len(response_json["articles"]), 1)
        self.assertEqual(response_json["articles"][0]["ticker"], "AAPL")
        self.assertEqual(response_json["articles"][0]["summary"], "Test summary")
        self.assertEqual(response_json["articles"][0]["overall_sentiment"], "Bullish")
        
        # Assert mock was called correctly - using simplified assertion
        mock_get_articles.assert_called_once()
    
    @patch('app.ArticleModel.get_articles_by_ticker')
    def test_get_articles_db_exception(self, mock_get_articles):
        """Test the /articles/{ticker} endpoint with database exception"""
        # Setup mock to raise exception
        mock_get_articles.side_effect = PyMongoError("Database connection error")
        
        # Make the request
        response = self.client.get("/articles/AAPL")
        
        # Check response
        self.assertEqual(response.status_code, 500)
        self.assertIn("Database error", response.json()["detail"])
        
        # Assert mock was called
        mock_get_articles.assert_called_once()
    
    @patch('app.ArticleModel.get_trending_articles')
    def test_get_trending_articles_success(self, mock_get_trending):
        """Test the /api/trending endpoint with successful response"""
        # Setup mock data
        mock_articles = [
            {
                "_id": ObjectId(),
                "ticker": "AAPL",
                "summary": "Test summary",
                "overall_sentiment": "Bullish",
                "created_at": datetime.now()
            }
        ]
        mock_get_trending.return_value = mock_articles
        
        # Make the request
        response = self.client.get("/api/trending?time_range=24h")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json["time_range"], "24h")
        self.assertEqual(len(response_json["articles"]), 1)
        
        # Simplified assertion, not checking specific parameters
        mock_get_trending.assert_called_once()
    
    @patch('app.ArticleModel.get_trending_articles')
    def test_get_trending_articles_invalid_time_range(self, mock_get_trending):
        """Test the /api/trending endpoint with invalid time range"""
        # Make the request with invalid time range
        response = self.client.get("/api/trending?time_range=invalid")
        
        # Check response
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid time_range", response.json()["detail"])
        
        # Assert mock was not called
        mock_get_trending.assert_not_called()
    
    @patch('app.ArticleModel.get_trending_articles')
    def test_get_trending_articles_db_exception(self, mock_get_trending):
        """Test the /api/trending endpoint with database exception"""
        # Setup mock to raise exception
        mock_get_trending.side_effect = PyMongoError("Database connection error")
        
        # Make the request
        response = self.client.get("/api/trending")
        
        # Check response
        self.assertEqual(response.status_code, 500)
        self.assertIn("Database error", response.json()["detail"])
        
        # Assert mock was called
        mock_get_trending.assert_called_once()
    
    @patch('app.requests.get')
    @patch('app.MongoDBConnection._client')
    def test_healthz_llm_down(self, mock_client, mock_get):
        """Test the /healthz endpoint when LLM service is down"""
        # Setup mock to raise exception
        mock_get.side_effect = requests.RequestException("Connection error")
        
        # Mock MongoDB ping direct return value
        mock_admin = MagicMock()
        mock_client.admin = mock_admin
        mock_admin.command.return_value = True
        
        # Make the request
        response = self.client.get("/healthz")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json["status"], "degraded")
        self.assertEqual(response_json["mongo"], "reachable")
        self.assertEqual(response_json["llm_service"]["status"], "unreachable")
    
    @patch('app.requests.get')
    @patch('app.MongoDBConnection._client')
    def test_healthz_mongo_down(self, mock_client, mock_get):
        """Test the /healthz endpoint when MongoDB is down"""
        # Setup mock response for LLM service
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "ok",
            "mongo": "reachable"
        }
        mock_get.return_value = mock_response
        
        # Mock MongoDB ping throws exception
        mock_admin = MagicMock()
        mock_client.admin = mock_admin
        mock_admin.command.side_effect = PyMongoError("Database connection error")
        
        # Make the request
        response = self.client.get("/healthz")
        
        # Check response
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertEqual(response_json["status"], "degraded")
        self.assertEqual(response_json["mongo"], "unreachable")
        self.assertEqual(response_json["llm_service"]["status"], "unknown")


from fastapi.responses import HTMLResponse

if __name__ == '__main__':
    unittest.main()