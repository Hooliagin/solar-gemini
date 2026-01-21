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
    DB_PATH = "sqlite:///./backend.db"

    # Scheduling
    BRIEFING_TIME_HOUR = 5
    BRIEFING_TIME_MINUTE = 50

settings = Settings()

# Ensure data directories exist
os.makedirs(settings.AUDIO_DIR, exist_ok=True)
