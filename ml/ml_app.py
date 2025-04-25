# ml/ml_app.py
from fastapi import FastAPI, HTTPException
from common.models import MongoDBConnection
from pymongo.errors import PyMongoError
import os

app = FastAPI()
conn = MongoDBConnection()
db = MongoDBConnection().get_collection("sentiments")

@app.get("/analyze/{ticker}")
async def analyze(ticker: str):
    # simple cache check
    cached = db.find_one({"ticker": ticker})
    if cached:
        return {"source": "cache", **cached["result"]}

    # mock sentiment logic
    result = {
        "ticker": ticker,
        "sentiment_score": 0.42,
        "news": [{"title": "Dummy headline", "summary": "This is a mock summary."}]
    }
    db.insert_one({"ticker": ticker, "result": result})
    return {"source": "fresh", **result}


@app.get("/healthz")
async def healthcheck():
    """
    Ping MongoDB to verify connectivity.
    """
    try:
        # This will raise if Mongo isn’t reachable
        conn._client.admin.command("ping")
        return {"status": "ok", "mongo": "reachable"}
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"MongoDB ping failed: {e}")

