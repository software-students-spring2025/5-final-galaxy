import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os
import json

# Mock environment variables before imports
with patch.dict(os.environ, {"LLM_API_PROVIDER": "GEMINI", "GEMINI_API_KEY": "fake_key"}):
    # Use absolute imports instead
    from llm.agent import analyze_news, NewsAnalysis, system_prompt


class TestAgent(unittest.TestCase):
    """Test for the agent.py functions"""
    
    @patch('llm.agent.agent')
    @patch('llm.agent.prompt')
    def test_analyze_news_success(self, mock_prompt, mock_agent):
        """Test analyze_news function with successful response"""
        # Setup mocks
        mock_messages = MagicMock()
        mock_prompt.invoke = MagicMock(return_value=mock_messages)
        
        # Setup mock for agent invoke
        mock_result = {
            'structured_response': NewsAnalysis(
                ticker="AAPL",
                overall_sentiment="Bullish",
                summary="Positive news about Apple's earnings.",
                analysis="| Time | Headline | Sentiment | Reason | Source |\n|------|---------|-----------|-------|--------|\n| 2023-05-01 14:30 | Apple reports record earnings | Strongly Bullish | Exceeds market expectations | Bloomberg |"
            )
        }
        mock_agent.invoke = MagicMock(return_value=mock_result)
        
        # Call the function
        result = analyze_news("AAPL")
        
        # Assert that prompt.invoke was called with correct parameters
        expected_param = {"system_prompt": system_prompt, "ticker": "AAPL"}
        mock_prompt.invoke.assert_called_once_with(expected_param)
        
        # Assert that agent.invoke was called with correct parameters
        mock_agent.invoke.assert_called_once_with(mock_messages)
        
        # Check the result
        self.assertEqual(result["structured_response"].ticker, "AAPL")
        self.assertEqual(result["structured_response"].overall_sentiment, "Bullish")
        self.assertEqual(result["structured_response"].summary, "Positive news about Apple's earnings.")
        self.assertTrue("Apple reports record earnings" in result["structured_response"].analysis)
    
    @patch('llm.agent.agent')
    @patch('llm.agent.prompt')
    @patch('llm.agent.logging.error')
    def test_analyze_news_failure(self, mock_logging_error, mock_prompt, mock_agent):
        """Test analyze_news function with exception"""
        # Setup mock for prompt invoke
        mock_messages = MagicMock()
        mock_prompt.invoke = MagicMock(return_value=mock_messages)
        
        # Setup mock for agent invoke to raise an exception
        test_exception = Exception("Test exception")
        mock_agent.invoke = MagicMock(side_effect=test_exception)
        
        # Call the function and check if it raises the exception
        with self.assertRaises(Exception) as context:
            analyze_news("AAPL")
        
        # Check if the correct exception was raised
        self.assertEqual(str(context.exception), "Test exception")
        
        # Check if logging.error was called
        mock_logging_error.assert_called_once()
        args, kwargs = mock_logging_error.call_args
        self.assertEqual(args[0], "Error analyzing ticker AAPL: Test exception")
        self.assertTrue(kwargs.get("exc_info", False))


if __name__ == '__main__':
    unittest.main()