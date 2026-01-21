import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    AUDIO_DIR = os.path.join(BASE_DIR, "data", "audio")
    AUDIO_DIR = os.path.join(BASE_DIR, "data", "audio")
    
    # Database
    # Render provides postgres:// but SQLAlchemy needs postgresql://
    _db_url = os.getenv("DATABASE_URL", "sqlite:///./backend.db")
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    DB_PATH = _db_url

    # Scheduling
    BRIEFING_TIME_HOUR = 5
    BRIEFING_TIME_MINUTE = 50

settings = Settings()

# Ensure data directories exist
os.makedirs(settings.AUDIO_DIR, exist_ok=True)
