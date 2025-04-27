# web-app/app.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os, requests
from common.models import MongoDBConnection, ArticleModel
from pymongo.errors import PyMongoError

app = FastAPI()

# Tell FastAPI where templates are
templates = Jinja2Templates(directory="templates")

ML_URL = os.getenv("ML_SERVICE_URL", "http://ml:5002")
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

@app.post("/analyze/{ticker}")
async def trigger_analysis(ticker: str):
    """
    Trigger ML service to analyze the ticker.
    This doesn't return the results, just triggers the process.
    """
    try:
        # Send the analysis request to the ML service
        resp = requests.post(f"{ML_URL}/analyze/{ticker}")
        if resp.status_code != 202:
            raise HTTPException(status_code=502, detail="ML service error")
        
        # Return the status message from ML service
        return resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"ML service request failed: {str(e)}")

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

@app.get("/healthz")
async def healthz():
    try:
        # Check ML service health
        ml_resp = requests.get(f"{ML_URL}/healthz", timeout=3)
        ml_resp.raise_for_status()
        ml_status = ml_resp.json()
        
        # Check database connectivity
        conn._client.admin.command("ping")
        
        return {
            "status": "ok", 
            "mongo": "reachable", 
            "ml_service": ml_status
        }
    except requests.RequestException:
        return {"status": "degraded", "mongo": "reachable", "ml_service": "unreachable"}
    except PyMongoError:
        return {"status": "degraded", "mongo": "unreachable", "ml_service": "unknown"}


