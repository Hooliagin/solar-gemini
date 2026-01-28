import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    # Cron API Key (for external cron services)
    CRON_API_KEY = os.getenv("CRON_API_KEY")

    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    AUDIO_DIR = os.path.join(BASE_DIR, "data", "audio")
    AUDIO_DIR = os.path.join(BASE_DIR, "data", "audio")
    
    # Database
    # Render provides postgres:// but SQLAlchemy needs postgresql://
    _db_url = os.getenv("DATABASE_URL", "sqlite:///./backend.db")
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    
    # Debug: Print DB Host to verify connectivity (without password)
    try:
        if "@" in _db_url:
            db_host_port = _db_url.split("@")[1]
            print(f"Connecting to DB Host: {db_host_port}")
            if "supabase.co" in db_host_port and ":5432" in db_host_port and "pooler" not in db_host_port:
                print("WARNING: It looks like you are using the Supabase Direct Connection (port 5432).")
                print("Render's free tier often requires the Transaction Pooler (port 6543) for IPv4 support.")
                print("If you see 'Network is unreachable', update DATABASE_URL to use port 6543.")
    except Exception as e:
        print(f"Error parsing DB URL for debug logging: {e}")

    DB_PATH = _db_url

    # Scheduling
    BRIEFING_TIME_HOUR = 5
    BRIEFING_TIME_MINUTE = 50

settings = Settings()

# Ensure data directories exist
os.makedirs(settings.AUDIO_DIR, exist_ok=True)
