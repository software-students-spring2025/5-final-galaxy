# web-app/app.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os, requests

app = FastAPI()


#tell FastAPI where templates are
templates = Jinja2Templates(directory="templates")

ML_URL = os.getenv("ML_SERVICE_URL", "http://ml:5002")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/mydb")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """
    Render the index.html template on GET /
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/analyze/{ticker}")
async def analyze(ticker: str):
    """Proxy to ML service"""
    resp = requests.get(f"{ML_URL}/analyze/{ticker}")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="ML service error")
    return resp.json()


@app.get("/healthz")
async def healthz():
    try:
        resp = requests.get(f"{os.getenv('ML_SERVICE_URL')}/healthz", timeout=3)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail="ML service unreachable")


