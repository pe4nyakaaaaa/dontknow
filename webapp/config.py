import os

SECRET_KEY = os.getenv("SITE_SECRET_KEY", "change-me-in-production-super-secret-key-2024")
DATABASE_URL = os.getenv("SITE_DATABASE_URL", "sqlite+aiosqlite:///./site_data.db")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
ALGORITHM = "HS256"
