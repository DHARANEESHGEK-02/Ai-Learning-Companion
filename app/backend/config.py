import os

DATABASE_URL = os.getenv("DATABASE_URL", "")
SECRET_KEY = os.getenv("SESSION_SECRET", "fallback_secret_key_change_in_production")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
BACKEND_URL = "http://localhost:8000"
UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)
