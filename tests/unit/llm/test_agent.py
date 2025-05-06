# tests/unit/llm/test_agent.py
import pytest
from unittest.mock import patch, MagicMock
from llm.agent import analyze_news

class TestAgent:
    def test_analyze_news_success(self):
        test_ticker = "TSLA"
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "structured_response": MagicMock(
                model_dump=lambda: {
                    "overall_sentiment": "Neutral",
                    "summary": "Test summary",
                    "analysis": "Test analysis"
                }
            )
        }
        
        with patch('llm.agent.agent', mock_agent):
            result = analyze_news(test_ticker)
            assert "structured_response" in result