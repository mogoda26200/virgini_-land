import os
from dotenv import load_dotenv
load_dotenv()
class Config:
    SECRET_KEY = os.environ["SECRET_KEY"]
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///goldtrack.db")
    GOLD_API_KEY = os.getenv("GOLD_API_KEY", "")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5000").split(",")
    UPDATE_MINUTES = int(os.getenv("UPDATE_MINUTES", "5"))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
