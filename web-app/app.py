# web-app/app.py
from fastapi import FastAPI, Request, HTTPException, Query, Depends, Form, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os, requests
from common.models import MongoDBConnection, ArticleModel, UserModel, UserLimitModel
from pymongo.errors import PyMongoError
from typing import Optional, List
import uuid
from datetime import datetime, timedelta
import httpx
from pathlib import Path
import json
from urllib.parse import unquote
from bson.objectid import ObjectId

app = FastAPI()

# Tell FastAPI where templates are
templates = Jinja2Templates(directory="templates")

ML_URL = os.getenv("ML_SERVICE_URL", "http://ml:5002")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/mydb")

# Initialize MongoDB connection
mongo_conn = MongoDBConnection()
articles_collection = mongo_conn.get_collection("articles")
users_collection = mongo_conn.get_collection("users")
analytics_collection = mongo_conn.get_collection("user_analytics")

# Session store (in-memory for simplicity)
# In a production app, you'd use Redis or another persistent store
sessions = {}

# 添加依赖项来检查用户认证状态
async def get_current_user(request: Request, session_id: Optional[str] = Cookie(None)):
    """
    Get the current authenticated user or None
    """
    # No session cookie
    if not session_id:
        print("DEBUG: No session_id cookie found")
        return None
    
    if session_id not in sessions:
        print(f"DEBUG: Session ID {session_id} not found in sessions store")
        print(f"DEBUG: Available sessions: {list(sessions.keys())}")
        return None
    
    # Session exists but expired
    session = sessions[session_id]
    if session["expires"] < datetime.utcnow():
        print(f"DEBUG: Session {session_id} expired")
        del sessions[session_id]
        return None
    
    # Valid session
    print(f"DEBUG: Valid session found for user {session['user'].get('username')}")
    return session["user"]

# 添加中间件检查登录状态并注入到模板
@app.middleware("http")
async def add_user_middleware(request: Request, call_next):
    """Add user to request and extend templates context"""
    user = await get_current_user(request)
    request.state.user = user
    print(f"DEBUG: User in middleware: {user['username'] if user else 'None'}")
    
    response = await call_next(request)
    return response

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """
    Render the index.html template on GET /
    """
    return templates.TemplateResponse("index.html", {"request": request, "user": request.state.user})

@app.get("/trending", response_class=HTMLResponse)
async def get_trending_page(request: Request):
    """
    Render the trending.html template on GET /trending
    """
    return templates.TemplateResponse("trending.html", {"request": request, "user": request.state.user})

@app.get("/detail", response_class=HTMLResponse)
async def get_detail_page(request: Request, ticker: str = None):
    """
    Render the detail.html template on GET /detail
    """
    if not ticker:
        # Redirect to home if no ticker provided
        return RedirectResponse(url="/")
    
    return templates.TemplateResponse("detail.html", {"request": request, "user": request.state.user})

@app.post("/analyze/{ticker}")
async def trigger_analysis(ticker: str, request: Request):
    """
    Trigger ML service to analyze the ticker.
    This doesn't return results directly, just triggers the process 
    and returns an appropriate response to guide the user to the detail page.
    """
    # 检查用户登录状态
    if request.state.user is None:
        return {
            "status": "unauthorized",
            "message": "You need to log in to analyze stocks",
            "redirect_to": f"/login?next=/detail?ticker={ticker}"
        }
    
    try:
        user_id = str(request.state.user["_id"])
        
        # Check if user has reached the daily limit
        can_analyze, remaining = UserLimitModel.check_and_update_limit(analytics_collection, user_id)
        if not can_analyze:
            return {
                "status": "limit_exceeded",
                "message": "You have reached your daily analysis limit. Please try again tomorrow.",
                "redirect_to": "/history"
            }
        
        # Send the analysis request to the ML service with user ID
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{ML_URL}/analyze/{ticker}",
                json={"user_id": user_id}
            )
            
            if resp.status_code != 202:
                raise HTTPException(status_code=502, detail="ML service error")
        
        # Return the status message and ticker for redirection
        return {
            "status": "queued",
            "message": f"Analysis for {ticker} has been initiated",
            "ticker": ticker,
            "redirect_to": f"/detail?ticker={ticker}"
        }
    except httpx.RequestError as e:
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
        formatted_articles = []
        for article in articles:
            article_dict = dict(article)
            # Convert ObjectId to string for JSON serialization
            if "_id" in article_dict:
                article_dict["_id"] = str(article_dict["_id"])
            # Format date
            if "created_at" in article_dict and isinstance(article_dict["created_at"], datetime):
                article_dict["created_at"] = article_dict["created_at"].isoformat()
            
            formatted_articles.append(article_dict)
        
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
        # Determine cutoff date based on time_range
        cutoff_date = None
        if time_range == "24h":
            cutoff_date = datetime.utcnow() - timedelta(hours=24)
        elif time_range == "7d":
            cutoff_date = datetime.utcnow() - timedelta(days=7)
        elif time_range == "30d":
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
        # Get trending articles from MongoDB
        articles = ArticleModel.get_trending_articles(articles_collection, cutoff_date)
        
        # Sort by date (newest first)
        articles = sorted(articles, key=lambda x: x.get('created_at', datetime.min), reverse=True)
        
        # Limit to 10
        articles = articles[:10]
        
        # Format articles for the response
        formatted_articles = []
        for article in articles:
            article_dict = dict(article)
            # Convert ObjectId to string for JSON serialization
            if "_id" in article_dict:
                article_dict["_id"] = str(article_dict["_id"])
            # Format date
            if "created_at" in article_dict and isinstance(article_dict["created_at"], datetime):
                article_dict["created_at"] = article_dict["created_at"].isoformat()
            
            formatted_articles.append(article_dict)
        
        return {"time_range": time_range, "articles": formatted_articles}
    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/healthz")
async def healthz():
    try:
        # Check ML service health
        async with httpx.AsyncClient() as client:
            ml_resp = await client.get(f"{ML_URL}/healthz", timeout=3)
            ml_resp.raise_for_status()
            ml_status = ml_resp.json()
        
        # Check database connectivity
        mongo_conn._client.admin.command("ping")
        
        return {
            "status": "ok", 
            "mongo": "reachable", 
            "ml_service": ml_status
        }
    except httpx.RequestError:
        return {"status": "degraded", "mongo": "reachable", "ml_service": "unreachable"}
    except PyMongoError:
        return {"status": "degraded", "mongo": "unreachable", "ml_service": "unknown"}

# 用户认证相关路由
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = None):
    """
    Render the login page
    """
    # 已登录用户重定向到首页
    if request.state.user:
        return RedirectResponse(url="/")
        
    return templates.TemplateResponse(
        "login.html", 
        {"request": request, "next": next, "error": None}
    )

@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: Optional[str] = Form(None)
):
    """
    Handle login form submission
    """
    # 已登录用户重定向到首页
    if request.state.user:
        print(f"DEBUG: User already logged in: {request.state.user['username']}")
        return RedirectResponse(url="/", status_code=303)
    
    try:
        print(f"DEBUG: Attempting to authenticate user: {username}")
        # 验证用户
        user = UserModel.authenticate_user(users_collection, username, password)
        
        if not user:
            print(f"DEBUG: Authentication failed for user: {username}")
            return templates.TemplateResponse(
                "login.html", 
                {
                    "request": request, 
                    "error": "Invalid username or password",
                    "next": next
                },
                status_code=401
            )
        
        print(f"DEBUG: Authentication successful for user: {username}")
        # 创建会话
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "user": user,
            "expires": datetime.utcnow() + timedelta(days=1)
        }
        print(f"DEBUG: Created session {session_id} for user {username}")
        print(f"DEBUG: Total sessions: {len(sessions)}")
        
        # 重定向到下一个URL或首页
        redirect_url = next if next else "/"
        response = RedirectResponse(url=redirect_url, status_code=303)
        
        # 设置Cookie
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            max_age=86400,  # 1 day
            samesite="lax",
            secure=False,  # 开发环境设置为False，生产环境应该为True
            path="/"
        )
        print(f"DEBUG: Set cookie session_id={session_id}")
        
        return response
        
    except Exception as e:
        return templates.TemplateResponse(
            "login.html", 
            {
                "request": request, 
                "error": f"An error occurred: {str(e)}",
                "next": next
            },
            status_code=500
        )

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """
    Render the registration page
    """
    # 已登录用户重定向到首页
    if request.state.user:
        return RedirectResponse(url="/")
        
    return templates.TemplateResponse(
        "register.html", 
        {"request": request, "error": None}
    )

@app.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...)
):
    """
    Handle registration form submission
    """
    # 已登录用户重定向到首页
    if request.state.user:
        return RedirectResponse(url="/", status_code=303)
    
    # 验证密码
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html", 
            {
                "request": request, 
                "error": "Passwords do not match"
            },
            status_code=400
        )
    
    try:
        # 创建用户
        user = UserModel.create_user(users_collection, username, email, password)
        
        # 创建会话
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "user": user,
            "expires": datetime.utcnow() + timedelta(days=1)
        }
        
        # 重定向到首页
        response = RedirectResponse(url="/", status_code=303)
        
        # 设置Cookie
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            max_age=86400,  # 1 day
            samesite="lax"
        )
        
        return response
        
    except ValueError as e:
        return templates.TemplateResponse(
            "register.html", 
            {
                "request": request, 
                "error": str(e)
            },
            status_code=400
        )
    except Exception as e:
        return templates.TemplateResponse(
            "register.html", 
            {
                "request": request, 
                "error": f"An error occurred: {str(e)}"
            },
            status_code=500
        )

@app.get("/logout")
async def logout(request: Request, session_id: Optional[str] = Cookie(None)):
    """
    Log out the current user
    """
    if session_id and session_id in sessions:
        del sessions[session_id]
    
    response = RedirectResponse(url="/")
    response.delete_cookie(key="session_id")
    
    return response

@app.get("/history", response_class=HTMLResponse)
async def get_history(request: Request):
    """
    Display the current user's analysis history
    """
    # Check if the user is logged in
    if not request.state.user:
        return RedirectResponse(url="/login?next=/history")
    
    try:
        user_id = str(request.state.user["_id"])
        
        # Get remaining analyses for today
        remaining_analyses = UserLimitModel.get_remaining_analyses(
            analytics_collection, 
            user_id
        )
        
        # Get articles analyzed by this user
        articles = ArticleModel.get_articles_by_user(articles_collection, user_id)
        
        # Sort articles by date (newest first)
        articles = sorted(articles, key=lambda x: x.get('created_at', datetime.min), reverse=True)
        
        # Format dates and group by ticker
        ticker_groups = {}
        for article in articles:
            # Format date
            if 'created_at' in article:
                dt = article['created_at']
                if isinstance(dt, str):
                    try:
                        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                    except ValueError:
                        continue
                article['formatted_date'] = dt.strftime("%B %d, %Y at %H:%M")
            
            # Group by ticker
            ticker = article.get('ticker')
            if ticker:
                if ticker not in ticker_groups:
                    ticker_groups[ticker] = []
                ticker_groups[ticker].append(article)
        
        return templates.TemplateResponse("history.html", {
            "request": request,
            "user": request.state.user,
            "ticker_groups": ticker_groups,
            "remaining_analyses": remaining_analyses
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request, 
            "user": request.state.user,
            "error_message": f"Error retrieving history: {str(e)}"
        })

@app.get("/api/user/remaining-analyses", response_class=JSONResponse)
async def get_remaining_analyses(request: Request):
    """API endpoint to get remaining analyses for the current user"""
    # Check if the user is logged in
    if not request.state.user:
        return JSONResponse(
            status_code=401,
            content={"error": "User not authenticated"}
        )
        
    try:
        user_id = str(request.state.user["_id"])
        remaining = UserLimitModel.get_remaining_analyses(analytics_collection, user_id)
        return {"remaining_analyses": remaining}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error retrieving remaining analyses: {str(e)}"}
        )


