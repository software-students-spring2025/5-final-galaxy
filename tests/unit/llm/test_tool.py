import pytest
from unittest.mock import patch, MagicMock
from llm.tool import (
    get_ticker_news,
    get_broad_ticker_news,
    get_news_from_source,
    get_news_for_multiple_tickers,
    get_curated_news,
    get_entity_news,
    search_tickers,
    ticker_news_tool
)
from datetime import datetime

class TestToolFunctions:
    @patch('llm.tool.requests.get')
    def test_get_ticker_news(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "stories": [{"time": 1625097600000, "title": "Test News"}]
        }
        mock_get.return_value = mock_response
        
        result = get_ticker_news("AAPL")
        assert "stories" in result
        assert isinstance(result["stories"][0]["time"], str)

    @patch('llm.tool.requests.get')
    def test_api_failure(self, mock_get):
        mock_get.return_value.status_code = 500
        result = get_ticker_news("INVALID")
        assert "error" in result

    @patch('llm.tool.get_ticker_news')
    def test_ticker_news_tool(self, mock_get):
        mock_get.return_value = {"stories": []}
        tool = next(t for t in ticker_news_tool if t.name == "get_ticker_news_tool")
        result = tool.run("AAPL")
        assert isinstance(result, dict)

    @pytest.mark.parametrize("tool_func,arg", [
        ("get_broad_ticker_news_tool", "AAPL"),
        ("get_news_from_source_tool", "bloomberg"),
        ("get_curated_news_tool", None),
        ("search_tickers_tool", "Apple")
    ])
    def test_tool_operations(self, tool_func, arg):
        tool = next(t for t in ticker_news_tool if t.name == tool_func)
        with patch(f'llm.tool.{tool_func.split("_tool")[0]}') as mock:
            mock.return_value = {"test": "data"}
            result = tool.run(arg) if arg else tool.run()
            assert isinstance(result, dict)