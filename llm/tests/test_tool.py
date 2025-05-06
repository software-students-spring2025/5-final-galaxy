import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime
import sys
import os

# Remove the sys.path manipulation that can cause issues with pytest
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock environment variables before imports
with patch.dict(os.environ, {"LLM_API_PROVIDER": "GEMINI", "GEMINI_API_KEY": "fake_key"}):
    from llm.tool import (
        get_feed, 
        convert_timestamp_ms_to_iso, 
        get_ticker_news, 
        get_broad_ticker_news,
        get_news_from_source,
        get_news_for_multiple_tickers,
        get_curated_news,
        get_entity_news,
        search_tickers,
        get_ticker_news_tool,
        get_broad_ticker_news_tool,
        get_news_from_source_tool,
        get_news_for_multiple_tickers_tool,
        get_curated_news_tool,
        get_entity_news_tool,
        search_tickers_tool
    )

class TestToolFunctions(unittest.TestCase):
    """Test for the non-tool functions in tool.py"""
    
    def test_convert_timestamp_ms_to_iso(self):
        """Test conversion of timestamp in milliseconds to ISO format"""
        # Create a sample response with a timestamp in milliseconds
        test_response = {
            "stories": [
                {"time": 1633046400000},  # 2021-10-01 00:00:00 UTC
                {"time": 1633132800000}   # 2021-10-02 00:00:00 UTC
            ]
        }
        
        # Convert timestamps in the response
        result = convert_timestamp_ms_to_iso(test_response)
        
        # Check if conversion was done correctly
        self.assertEqual(result["stories"][0]["time"], "2021-10-01T00:00:00")
        self.assertEqual(result["stories"][1]["time"], "2021-10-02T00:00:00")
    
    @patch('llm.tool.requests.get')
    def test_get_feed_success(self, mock_get):
        """Test get_feed function with a successful API response"""
        # Mock response object
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "stories": [
                {"time": 1633046400000, "headline": "Test headline"}
            ]
        }
        mock_get.return_value = mock_response
        
        # Call the function with a test query
        result = get_feed("test_query", limit=10)
        
        # Assert that get was called with the correct URL
        mock_get.assert_called_once_with("https://api.tickertick.com/feed?q=test_query&n=10")
        
        # Check if the result has the timestamp converted
        self.assertEqual(result["stories"][0]["time"], "2021-10-01T00:00:00")
        self.assertEqual(result["stories"][0]["headline"], "Test headline")
    
    @patch('llm.tool.requests.get')
    def test_get_feed_with_last_id(self, mock_get):
        """Test get_feed function with a last_id parameter"""
        # Mock response object
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"stories": []}
        mock_get.return_value = mock_response
        
        # Call the function with a test query and last_id
        result = get_feed("test_query", limit=10, last_id="last_123")
        
        # Assert that get was called with the correct URL including last_id
        mock_get.assert_called_once_with("https://api.tickertick.com/feed?q=test_query&n=10&last=last_123")
    
    @patch('llm.tool.requests.get')
    def test_get_feed_error(self, mock_get):
        """Test get_feed function with an error response"""
        # Mock response object
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        # Call the function with a test query
        result = get_feed("test_query")
        
        # Check if the result contains the error message
        self.assertEqual(result, {"error": "API request failed with status code 500"})
    
    @patch('llm.tool.get_feed')
    def test_get_ticker_news(self, mock_get_feed):
        """Test get_ticker_news function"""
        # Set up the mock return value
        mock_get_feed.return_value = {"stories": [{"headline": "Test ticker news"}]}
        
        # Call the function
        result = get_ticker_news("AAPL", limit=20)
        
        # Assert get_feed was called with correct parameters
        mock_get_feed.assert_called_once_with("z:AAPL", 20)
        
        # Check the result
        self.assertEqual(result, {"stories": [{"headline": "Test ticker news"}]})
    
    @patch('llm.tool.get_feed')
    def test_get_broad_ticker_news(self, mock_get_feed):
        """Test get_broad_ticker_news function"""
        # Set up the mock return value
        mock_get_feed.return_value = {"stories": [{"headline": "Test broad ticker news"}]}
        
        # Call the function
        result = get_broad_ticker_news("AAPL", limit=15)
        
        # Assert get_feed was called with correct parameters
        mock_get_feed.assert_called_once_with("tt:AAPL", 15)
        
        # Check the result
        self.assertEqual(result, {"stories": [{"headline": "Test broad ticker news"}]})
    
    @patch('llm.tool.get_feed')
    def test_get_news_from_source(self, mock_get_feed):
        """Test get_news_from_source function"""
        # Set up the mock return value
        mock_get_feed.return_value = {"stories": [{"headline": "Test source news"}]}
        
        # Call the function
        result = get_news_from_source("bloomberg", limit=5)
        
        # Assert get_feed was called with correct parameters
        mock_get_feed.assert_called_once_with("s:bloomberg", 5)
        
        # Check the result
        self.assertEqual(result, {"stories": [{"headline": "Test source news"}]})
    
    @patch('llm.tool.get_feed')
    def test_get_news_for_multiple_tickers(self, mock_get_feed):
        """Test get_news_for_multiple_tickers function"""
        # Set up the mock return value
        mock_get_feed.return_value = {"stories": [{"headline": "Test multiple tickers news"}]}
        
        # Call the function
        result = get_news_for_multiple_tickers(["AAPL", "MSFT"], limit=25)
        
        # Assert get_feed was called with correct parameters
        mock_get_feed.assert_called_once_with("(or tt:AAPL tt:MSFT)", 25)
        
        # Check the result
        self.assertEqual(result, {"stories": [{"headline": "Test multiple tickers news"}]})
    
    @patch('llm.tool.get_feed')
    def test_get_curated_news(self, mock_get_feed):
        """Test get_curated_news function"""
        # Set up the mock return value
        mock_get_feed.return_value = {"stories": [{"headline": "Test curated news"}]}
        
        # Call the function
        result = get_curated_news(limit=30)
        
        # Assert get_feed was called with correct parameters
        mock_get_feed.assert_called_once_with("T:curated", 30)
        
        # Check the result
        self.assertEqual(result, {"stories": [{"headline": "Test curated news"}]})
    
    @patch('llm.tool.get_feed')
    def test_get_entity_news(self, mock_get_feed):
        """Test get_entity_news function"""
        # Set up the mock return value
        mock_get_feed.return_value = {"stories": [{"headline": "Test entity news"}]}
        
        # Call the function
        result = get_entity_news("Elon Musk", limit=10)
        
        # Assert get_feed was called with correct parameters
        mock_get_feed.assert_called_once_with("E:elon_musk", 10)
        
        # Check the result
        self.assertEqual(result, {"stories": [{"headline": "Test entity news"}]})
    
    @patch('llm.tool.requests.get')
    def test_search_tickers(self, mock_get):
        """Test search_tickers function with a successful API response"""
        # Mock response object
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tickers": [
                {"symbol": "AAPL", "name": "Apple Inc."}
            ]
        }
        mock_get.return_value = mock_response
        
        # Call the function
        result = search_tickers("Apple", limit=5)
        
        # Assert that get was called with the correct URL
        mock_get.assert_called_once_with("https://api.tickertick.com/tickers?p=Apple&n=5")
        
        # Check the result
        self.assertEqual(result, {"tickers": [{"symbol": "AAPL", "name": "Apple Inc."}]})
    
    @patch('llm.tool.requests.get')
    def test_search_tickers_error(self, mock_get):
        """Test search_tickers function with an error response"""
        # Mock response object
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        # Call the function
        result = search_tickers("Invalid query")
        
        # Check if the result contains the error message
        self.assertEqual(result, {"error": "API request failed with status code 500"})


class TestToolWrappers(unittest.TestCase):
    """Test for the tool wrapper functions in tool.py"""
    
    @patch('llm.tool.get_ticker_news')
    def test_get_ticker_news_tool(self, mock_get_ticker_news):
        """Test get_ticker_news_tool function"""
        # Set up the mock return value
        mock_get_ticker_news.return_value = {"stories": [{"headline": "Test ticker news"}]}
        
        # Call the function with run() directly instead of the tool wrapper
        # 这里直接调用run方法而不是tool本身，避免callback问题
        result = get_ticker_news_tool.run({"ticker": "AAPL", "limit": 10})
        
        # Assert get_ticker_news was called with correct parameters
        mock_get_ticker_news.assert_called_once_with("AAPL", 10)
        
        # 修改检查：工具返回的是Python对象而不是JSON字符串
        self.assertEqual(type(result), dict)
        self.assertIn("stories", result)
        self.assertEqual(result["stories"][0]["headline"], "Test ticker news")
    
    @patch('llm.tool.get_broad_ticker_news')
    def test_get_broad_ticker_news_tool(self, mock_get_broad_ticker_news):
        """Test get_broad_ticker_news_tool function"""
        # Set up the mock return value
        mock_get_broad_ticker_news.return_value = {"stories": [{"headline": "Test broad ticker news"}]}
        
        # Call the function
        result = get_broad_ticker_news_tool.run({"ticker": "AAPL", "limit": 10})
        
        # Assert get_broad_ticker_news was called with correct parameters
        mock_get_broad_ticker_news.assert_called_once_with("AAPL", 10)
        
        # 修改检查：工具返回的是Python对象而不是JSON字符串
        self.assertEqual(type(result), dict)
        self.assertIn("stories", result)
        self.assertEqual(result["stories"][0]["headline"], "Test broad ticker news")
    
    @patch('llm.tool.get_news_from_source')
    def test_get_news_from_source_tool(self, mock_get_news_from_source):
        """Test get_news_from_source_tool function"""
        # Set up the mock return value
        mock_get_news_from_source.return_value = {"stories": [{"headline": "Test source news"}]}
        
        # Call the function
        result = get_news_from_source_tool.run({"source": "bloomberg", "limit": 10})
        
        # Assert get_news_from_source was called with correct parameters
        mock_get_news_from_source.assert_called_once_with("bloomberg", 10)
        
        # 修改检查：工具返回的是Python对象而不是JSON字符串
        self.assertEqual(type(result), dict)
        self.assertIn("stories", result)
        self.assertEqual(result["stories"][0]["headline"], "Test source news")
    
    @patch('llm.tool.get_news_for_multiple_tickers')
    def test_get_news_for_multiple_tickers_tool(self, mock_get_news_for_multiple_tickers):
        """Test get_news_for_multiple_tickers_tool function"""
        # Set up the mock return value
        mock_get_news_for_multiple_tickers.return_value = {"stories": [{"headline": "Test multiple tickers news"}]}
        
        # Call the function
        result = get_news_for_multiple_tickers_tool.run({"tickers": ["AAPL", "MSFT"], "limit": 10})
        
        # Assert get_news_for_multiple_tickers was called with correct parameters
        mock_get_news_for_multiple_tickers.assert_called_once_with(["AAPL", "MSFT"], 10)
        
        # 修改检查：工具返回的是Python对象而不是JSON字符串
        self.assertEqual(type(result), dict)
        self.assertIn("stories", result)
        self.assertEqual(result["stories"][0]["headline"], "Test multiple tickers news")
    
    @patch('llm.tool.get_curated_news')
    def test_get_curated_news_tool(self, mock_get_curated_news):
        """Test get_curated_news_tool function"""
        # Set up the mock return value
        mock_get_curated_news.return_value = {"stories": [{"headline": "Test curated news"}]}
        
        # Call the function
        result = get_curated_news_tool.run({"limit": 10})
        
        # Assert get_curated_news was called with correct parameters
        mock_get_curated_news.assert_called_once_with(10)
        
        # 修改检查：工具返回的是Python对象而不是JSON字符串
        self.assertEqual(type(result), dict)
        self.assertIn("stories", result)
        self.assertEqual(result["stories"][0]["headline"], "Test curated news")
    
    @patch('llm.tool.get_entity_news')
    def test_get_entity_news_tool(self, mock_get_entity_news):
        """Test get_entity_news_tool function"""
        # Set up the mock return value
        mock_get_entity_news.return_value = {"stories": [{"headline": "Test entity news"}]}
        
        # Call the function
        result = get_entity_news_tool.run({"entity": "Elon Musk", "limit": 10})
        
        # Assert get_entity_news was called with correct parameters
        mock_get_entity_news.assert_called_once_with("Elon Musk", 10)
        
        # 修改检查：工具返回的是Python对象而不是JSON字符串
        self.assertEqual(type(result), dict)
        self.assertIn("stories", result)
        self.assertEqual(result["stories"][0]["headline"], "Test entity news")
    
    @patch('llm.tool.search_tickers')
    def test_search_tickers_tool(self, mock_search_tickers):
        """Test search_tickers_tool function"""
        # Set up the mock return value
        mock_search_tickers.return_value = {"tickers": [{"symbol": "AAPL", "name": "Apple Inc."}]}
        
        # Call the function
        result = search_tickers_tool.run({"query": "Apple", "limit": 5})
        
        # Assert search_tickers was called with correct parameters
        mock_search_tickers.assert_called_once_with("Apple", 5)
        
        # 修改检查：工具返回的是Python对象而不是JSON字符串
        self.assertEqual(type(result), dict)
        self.assertIn("tickers", result)
        self.assertEqual(result["tickers"][0]["symbol"], "AAPL")
        self.assertEqual(result["tickers"][0]["name"], "Apple Inc.")


if __name__ == '__main__':
    unittest.main()