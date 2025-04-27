# ml/ml_app.py
from fastapi import FastAPI, HTTPException
from common.models import MongoDBConnection, ArticleModel
from pymongo.errors import PyMongoError
import os
from typing import Dict
from fastapi.responses import JSONResponse

app = FastAPI()
conn = MongoDBConnection()
# Use the articles collection instead of sentiments
articles_collection = conn.get_collection("articles")

@app.post("/analyze/{ticker}")
async def analyze(ticker: str) -> Dict:
    """
    Process an analysis request for a stock ticker.
    Instead of returning data, this now inserts data into the database.
    """
    # Hardcoded data for demonstration purposes
    hardcoded_articles = [
        {
            "title": f"{ticker} Shows Strong Growth Potential",
            "summary": f"Analysts are optimistic about {ticker}'s future performance based on recent financial results.",
            "body": f"In a recent report, market analysts highlighted that {ticker} has demonstrated exceptional growth potential in the last quarter. The company reported earnings that exceeded expectations by 15%, driven primarily by their new product line and expansion into emerging markets. Experts predict continued growth through the next fiscal year."
        },
        {
            "title": f"New Strategic Partnership Boosts {ticker} Stock",
            "summary": f"{ticker} announced a major partnership that could significantly increase market share.",
            "body": f"{ticker} has entered into a strategic partnership with a leading technology provider, which is expected to enhance their product offerings and expand their customer base. This collaboration aims to integrate cutting-edge technologies into {ticker}'s existing solutions, potentially disrupting the current market landscape. Investors responded positively to this announcement, with the stock price rising by 7% following the news."
        }
    ]
    
    try:
        # Insert each hardcoded article into the database
        for article_data in hardcoded_articles:
            article = ArticleModel.create_article(
                ticker=ticker,
                title=article_data["title"],
                summary=article_data["summary"],
                body=article_data["body"]
            )
            articles_collection.insert_one(article)
        
        # Return a simple confirmation without the data
        return JSONResponse(
            status_code=202,
            content={"status": "processing", "message": f"Analysis for {ticker} has been queued"}
        )
        
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@app.get("/healthz")
async def healthcheck():
    """
    Ping MongoDB to verify connectivity.
    """
    try:
        # This will raise if Mongo isn't reachable
        conn._client.admin.command("ping")
        return {"status": "ok", "mongo": "reachable"}
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"MongoDB ping failed: {e}")

