# ml/ml_app.py
from fastapi import FastAPI, HTTPException
from common.models import MongoDBConnection, ArticleModel
from pymongo.errors import PyMongoError
import os
import time
from typing import Dict, Optional
from fastapi.responses import JSONResponse

app = FastAPI()
conn = MongoDBConnection()
# Use the articles collection instead of sentiments
articles_collection = conn.get_collection("articles")

@app.post("/analyze/{ticker}")
async def analyze(ticker: str, user_id: Optional[str] = None) -> Dict:
    """
    Process an analysis request for a stock ticker.
    Includes a 10 second delay to simulate processing time.
    
    Args:
        ticker: Stock ticker symbol
        user_id: Optional user ID who requested the analysis
    """
    try:
        # Sleep for 10 seconds to simulate processing time
        time.sleep(10)
        
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
        
        # Insert each hardcoded article into the database
        inserted_ids = []
        for article_data in hardcoded_articles:
            article = ArticleModel.create_article(
                ticker=ticker,
                title=article_data["title"],
                summary=article_data["summary"],
                body=article_data["body"],
                user_id=user_id  # 添加用户ID
            )
            result = articles_collection.insert_one(article)
            inserted_ids.append(str(result.inserted_id))
        
        # Return a simple confirmation with article IDs
        return JSONResponse(
            status_code=202,
            content={
                "status": "completed", 
                "message": f"Analysis for {ticker} is complete",
                "ticker": ticker,
                "article_count": len(inserted_ids),
                "article_ids": inserted_ids,
                "user_id": user_id  # 在响应中包含用户ID
            }
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

