"""
Module for MongoDB models & connection.
"""

import os
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from bson import ObjectId
import hashlib
import secrets
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoDBConnection:
    _instance = None
    _client: MongoClient = None
    _db: Database = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connect()
        return cls._instance

    def _connect(self):
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/mydb")
        # store the client so you can ping it later
        self._client = MongoClient(uri)
        # extract the database name from the URI
        db_name = uri.rsplit('/', 1)[-1]
        self._db = self._client[db_name]

    def get_collection(self, name: str) -> Collection:
        return self._db[name]

# Schema and helper functions for the articles collection
class ArticleModel:
    """
    Class for handling article data stored in MongoDB
    """
    @staticmethod
    def create_article(ticker: str, title: str, summary: str, body: str, user_id: str = None) -> dict:
        """
        Create a new article document
        
        Args:
            ticker: Stock ticker symbol
            title: Article title
            summary: Article summary
            body: Article body text
            user_id: ID of the user who requested the analysis (optional)
            
        Returns:
            Article document
        """
        article = {
            "ticker": ticker.upper(),
            "title": title,
            "summary": summary,
            "body": body,
            "created_at": datetime.utcnow()
        }
        
        # Add user_id if provided
        if user_id:
            article["user_id"] = user_id
        
        return article
    
    @staticmethod
    def get_articles_by_ticker(collection: Collection, ticker: str) -> list:
        """
        Get all articles for a specific ticker
        """
        return list(collection.find({"ticker": ticker.upper()}).sort("created_at", DESCENDING))
    
    @staticmethod
    def get_articles_by_user(collection: Collection, user_id: str, limit: int = 50) -> list:
        """
        Get articles requested by a specific user
        
        Args:
            collection: MongoDB collection to query
            user_id: User ID
            limit: Maximum number of articles to return (default 50)
            
        Returns:
            List of articles sorted by creation date (most recent first)
        """
        return list(
            collection.find({"user_id": user_id})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
    
    @staticmethod
    def format_article(article: dict) -> dict:
        """
        Format article for API response
        """
        # Convert ObjectId to string for JSON serialization
        if "_id" in article:
            article["id"] = str(article["_id"])
            del article["_id"]
            
        # Format datetime to ISO string for JSON serialization
        if "created_at" in article and isinstance(article["created_at"], datetime):
            article["created_at"] = article["created_at"].isoformat()
            
        return article
        
    @staticmethod
    def get_trending_articles(collection: Collection, time_range: str = None, limit: int = 10) -> list:
        """
        Get recent articles based on time range
        
        Args:
            collection: MongoDB collection to query
            time_range: One of "24h", "7d", "30d" or None (for all)
            limit: Maximum number of articles to return (default 10)
        
        Returns:
            List of articles sorted by creation date (most recent first)
        """
        query = {}
        
        # Apply time filter if specified
        if time_range:
            current_time = datetime.utcnow()
            
            if time_range == "24h":
                since = current_time - timedelta(hours=24)
            elif time_range == "7d":
                since = current_time - timedelta(days=7)
            elif time_range == "30d":
                since = current_time - timedelta(days=30)
            else:
                since = None
                
            if since:
                query["created_at"] = {"$gte": since}
        
        # Execute query sorted by time (newest first) with limit
        return list(
            collection.find(query)
            .sort("created_at", DESCENDING)
            .limit(limit)
        )

# 用户分析次数限制模型
class UserLimitModel:
    """
    Class for handling user analysis limits
    """
    DAILY_LIMIT = 10  # 每日分析次数限制
    
    @staticmethod
    def check_and_update_limit(collection: Collection, user_id: str) -> tuple:
        """
        Check if the user has reached their daily analysis limit and update the counter
        
        Args:
            collection: MongoDB user_limits collection
            user_id: User ID
            
        Returns:
            Tuple of (can_analyze, remaining_analyses)
        """
        # 获取今天的日期（仅年月日)
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        # 查找用户当天的记录
        limit_record = collection.find_one({
            "user_id": user_id,
            "date": {"$gte": today, "$lt": tomorrow}
        })
        
        if not limit_record:
            # 如果没有记录，创建新记录
            limit_record = {
                "user_id": user_id,
                "date": today,
                "count": 1,
                "updated_at": datetime.utcnow()
            }
            collection.insert_one(limit_record)
            return True, UserLimitModel.DAILY_LIMIT - 1
        
        # 检查是否达到限制
        if limit_record["count"] >= UserLimitModel.DAILY_LIMIT:
            return False, 0
        
        # 更新计数
        collection.update_one(
            {"_id": limit_record["_id"]},
            {
                "$inc": {"count": 1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        remaining = UserLimitModel.DAILY_LIMIT - (limit_record["count"] + 1)
        return True, remaining
    
    @staticmethod
    def get_remaining_analyses(collection: Collection, user_id: str) -> int:
        """
        Get the number of remaining analyses for a user today
        
        Args:
            collection: MongoDB user_limits collection
            user_id: User ID
            
        Returns:
            Number of remaining analyses (0 if limit reached)
        """
        # 获取今天的日期（仅年月日)
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        # 查找用户当天的记录
        limit_record = collection.find_one({
            "user_id": user_id,
            "date": {"$gte": today, "$lt": tomorrow}
        })
        
        if not limit_record:
            # 如果没有记录，用户今天还没有进行分析
            return UserLimitModel.DAILY_LIMIT
        
        # 计算剩余次数
        remaining = max(0, UserLimitModel.DAILY_LIMIT - limit_record["count"])
        return remaining

# 用户模型和认证
class UserModel:
    """
    Class for handling user authentication and management
    """
    @staticmethod
    def hash_password(password: str, salt: str = None) -> tuple:
        """
        Hash a password with a random salt
        
        Args:
            password: Plain text password
            salt: Optional salt, if not provided a new one will be generated
            
        Returns:
            Tuple of (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)
            
        # Hash the password with the salt
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash, salt
    
    @staticmethod
    def create_user(collection: Collection, username: str, email: str, password: str) -> dict:
        """
        Create a new user
        
        Args:
            collection: MongoDB users collection
            username: Username
            email: Email address
            password: Plain text password
            
        Returns:
            New user document (without password)
        """
        # Check if username or email already exists
        if collection.find_one({"$or": [{"username": username}, {"email": email}]}):
            raise ValueError("Username or email already exists")
        
        # Hash password
        password_hash, salt = UserModel.hash_password(password)
        
        # Create user document
        user = {
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "salt": salt,
            "created_at": datetime.utcnow()
        }
        
        # Insert user
        result = collection.insert_one(user)
        user["_id"] = result.inserted_id
        
        # Don't return password hash in response
        user_response = user.copy()
        del user_response["password_hash"]
        del user_response["salt"]
        
        return user_response
    
    @staticmethod
    def authenticate_user(collection: Collection, username: str, password: str) -> dict:
        """
        Authenticate a user
        
        Args:
            collection: MongoDB users collection
            username: Username
            password: Plain text password
            
        Returns:
            User document if authentication successful, None otherwise
        """
        # Find user by username
        user = collection.find_one({"username": username})
        
        if not user:
            return None
        
        # Verify password
        password_hash, _ = UserModel.hash_password(password, user["salt"])
        
        if password_hash != user["password_hash"]:
            return None
        
        # Don't return password hash in response
        user_response = user.copy()
        del user_response["password_hash"]
        del user_response["salt"]
        
        return user_response
        
    @staticmethod
    def get_user_by_id(collection: Collection, user_id: str) -> dict:
        """
        Get user by ID
        
        Args:
            collection: MongoDB users collection
            user_id: User ID (string)
            
        Returns:
            User document
        """
        user = collection.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return None
        
        # Don't return password hash in response
        user_response = user.copy()
        del user_response["password_hash"]
        del user_response["salt"]
        
        return user_response