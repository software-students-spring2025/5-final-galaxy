# llm/llm_app.py
import logging
from fastapi import FastAPI, HTTPException
from common.models import MongoDBConnection, ArticleModel
from pymongo.errors import PyMongoError
from typing import Dict
from fastapi.responses import JSONResponse
from agent import analyze_news
from datetime import datetime

app = FastAPI()
conn = MongoDBConnection()
# Use the articles collection instead of sentiments
articles_collection = conn.get_collection("articles")



@app.post("/analyze/{ticker}")
async def analyze(ticker: str) -> Dict:
    """
    Process an analysis request for a stock ticker.
    Saves the result to the database and returns a 202 status.
    """
    try:
        raw_result = analyze_news(ticker)
        result = raw_result['structured_response'].model_dump()
        logging.info(f"result from analyze_news: {result}")


        article_data = ArticleModel.create_article(ticker, result['overall_sentiment'], result['summary'], result['analysis'])
        
        # Insert the article into the database
        insert_result = articles_collection.insert_one(article_data)
        if not insert_result.inserted_id:
             raise HTTPException(status_code=500, detail="Failed to insert article into database.")

        # Return a 202 Accepted response indicating the task is queued/processing
        return JSONResponse(
            status_code=202,
            content={
                "status": "queued", 
                "message": f"Analysis for {ticker} initiated.",
                "ticker": ticker,
                # Removed summary and analysis from the response
            }
        )
        
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        # Log the specific exception before raising the HTTP error
        logging.error(f"Unexpected error processing {ticker}: {e}", exc_info=True)
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

