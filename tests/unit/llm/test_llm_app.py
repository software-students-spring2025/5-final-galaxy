# tests/unit/llm/test_llm_app.py
import pytest
from fastapi import HTTPException
from llm.llm_app import app
from unittest.mock import patch, MagicMock

class TestLLMApp:
    @pytest.mark.asyncio
    async def test_analyze_success(self, client, mock_mongo):
        test_ticker = "AAPL"
        mock_result = {
            "structured_response": MagicMock(
                model_dump=lambda: {
                    "overall_sentiment": "Bullish",
                    "summary": "Test summary",
                    "analysis": "Test analysis"
                }
            )
        }
        mock_insert = MagicMock(inserted_id="123")
        mock_mongo.insert_one.return_value = mock_insert

        with patch('llm.llm_app.analyze_news', return_value=mock_result):
            response = client.post(f"/analyze/{test_ticker}")
            assert response.status_code == 202
            assert response.json()["status"] == "queued"

    @pytest.mark.asyncio
    async def test_healthcheck_failure(self, client):
        with patch.object(conn._client.admin, 'command', side_effect=Exception("DB down")):
            response = client.get("/healthz")
            assert response.status_code == 500