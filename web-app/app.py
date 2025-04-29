# web-app/app.py
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os, requests
from common.models import MongoDBConnection, ArticleModel
from pymongo.errors import PyMongoError
from typing import Optional

app = FastAPI()

# Tell FastAPI where templates are
templates = Jinja2Templates(directory="templates")

LLM_URL = os.getenv("LLM_SERVICE_URL", "http://llm:5002")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/mydb")

# Initialize MongoDB connection
conn = MongoDBConnection()
articles_collection = conn.get_collection("articles")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """
    Render the index.html template on GET /
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/trending", response_class=HTMLResponse)
async def get_trending_page(request: Request):
    """
    Render the trending.html template on GET /trending
    """
    return templates.TemplateResponse("trending.html", {"request": request})

@app.get("/detail", response_class=HTMLResponse)
async def get_detail_page(request: Request, ticker: str = None):
    """
    Render the detail.html template on GET /detail
    """
    if not ticker:
        # Redirect to home if no ticker provided
        return RedirectResponse(url="/")
    
    return templates.TemplateResponse("detail.html", {"request": request})

@app.post("/analyze/{ticker}")
async def trigger_analysis(ticker: str):
    """
    Trigger ML service to analyze the ticker.
    This doesn't return results directly, just triggers the process 
    and returns an appropriate response to guide the user to the detail page.
    """
    try:
        # Send the analysis request to the ML service
        resp = requests.post(f"{LLM_URL}/analyze/{ticker}")
        if resp.status_code != 202:
            raise HTTPException(status_code=502, detail="LLM service error")
        
        # Return the status message and ticker for redirection
        return {
            "status": "queued",
            "message": f"Analysis for {ticker} has been initiated",
            "ticker": ticker,
            "redirect_to": f"/detail?ticker={ticker}"
        }
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"LLM service request failed: {str(e)}")

@app.get("/articles/{ticker}")
async def get_articles(ticker: str):
    """
    Get articles for a specific ticker from the database.
    This is what the frontend will poll to check for results.
    """
    try:
        # Get articles from MongoDB
        articles = ArticleModel.get_articles_by_ticker(articles_collection, ticker)
        
        # Format articles for the response
        formatted_articles = [ArticleModel.format_article(article) for article in articles]
        
        return {"ticker": ticker, "articles": formatted_articles}
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/trending")
async def get_trending_articles(time_range: Optional[str] = Query(None, description="Time range: 24h, 7d, 30d")):
    """
    Get trending articles from the database based on time range.
    Default returns the newest 10 articles.
    """
    try:
        # Validate time_range parameter
        valid_ranges = [None, "24h", "7d", "30d"]
        if time_range not in valid_ranges:
            raise HTTPException(status_code=400, detail=f"Invalid time_range. Must be one of: {', '.join(str(r) for r in valid_ranges if r)}")
        
        # Get trending articles from MongoDB
        articles = ArticleModel.get_trending_articles(
            collection=articles_collection,
            time_range=time_range,
            limit=10
        )
        
        # Format articles for the response
        formatted_articles = [ArticleModel.format_article(article) for article in articles]
        
        return {"time_range": time_range, "articles": formatted_articles}
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/healthz")
async def healthz():
    try:
        # Check LLM service health
        llm_resp = requests.get(f"{LLM_URL}/healthz", timeout=3)
        llm_resp.raise_for_status()
        llm_status = llm_resp.json()
        
        # Check database connectivity
        conn._client.admin.command("ping")
        
        return {
            "status": "ok", 
            "mongo": "reachable", 
            "llm_service": llm_status
        }
    except requests.RequestException:
        # Return consistent structure for llm_service
        return {"status": "degraded", "mongo": "reachable", "llm_service": {"status": "unreachable"}}
    except PyMongoError:
        # Return consistent structure for llm_service
        return {"status": "degraded", "mongo": "unreachable", "llm_service": {"status": "unknown"}}


