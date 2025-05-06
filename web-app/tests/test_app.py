import unittest
from unittest.mock import patch, MagicMock
import json
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from bson import ObjectId
import requests
import sys
import os

# 添加父目录到sys.path，确保可以导入web-app中的模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 现在可以导入app模块
from app import app as fastapi_app


class TestWebApp(unittest.TestCase):
    """Test for the web-app/app.py FastAPI application without template rendering"""
    
    def setUp(self):
        """Set up test client and mocks before each test"""
        self.client = TestClient(fastapi_app)
    
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


if __name__ == '__main__':
    unittest.main()