from fastapi import FastAPI
import os
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from services.scheduler import start_scheduler
from database import create_db_and_tables

# Global scheduler instance
scheduler = None

def should_run_scheduler():
    """
    Only run scheduler on one worker to prevent duplicate briefings.
    In production (gunicorn), only the first worker should run it.
    Check if we're worker 1 or in development mode.
    """
    # Check for gunicorn worker ID
    worker_id = os.environ.get("GUNICORN_WORKER_ID")
    if worker_id and worker_id != "1":
        return False
    
    # For render.com with multiple workers, use a file lock approach
    lock_file = "/tmp/scheduler_lock"
    try:
        if os.path.exists(lock_file):
            # Check if lock is stale (older than 5 minutes)
            import time
            if time.time() - os.path.getmtime(lock_file) < 300:
                return False
        # Create lock file
        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))
        return True
    except Exception:
        return True  # Default to running if we can't check

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_db_and_tables()
    
    # Start the briefing scheduler (per-user briefing times)
    global scheduler
    if should_run_scheduler():
        scheduler = start_scheduler()
        print("Briefing scheduler started - checking every minute for scheduled briefings.")
    else:
        print("Scheduler skipped on this worker (another worker is handling it).")
    
    print("App started. Use /generate in Telegram for manual briefings.")
    
    yield
    
    # Shutdown
    if scheduler:
        scheduler.shutdown(wait=False)
    print("App shutdown.")

app = FastAPI(lifespan=lifespan, title="Audio Daily Manager")

from routers import entries
from routers import briefings

app.include_router(entries.router)
app.include_router(briefings.router)
from routers import interests
app.include_router(interests.router)
from routers import settings
app.include_router(settings.router)
from routers import google_auth
app.include_router(google_auth.router)
from routers import telegram_bot
app.include_router(telegram_bot.router)
from routers import cron
app.include_router(cron.router)
# Parse origins and ensure they have a scheme (https://) if provided by Render
origins_raw = os.getenv("ALLOWED_ORIGINS", "*").split(",")
origins = []
for origin in origins_raw:
    origin = origin.strip()
    if origin == "*":
        origins.append("*")
        continue
    
    if not origin.startswith("http"):
        # Add https prefix
        base_origin = f"https://{origin}"
        origins.append(base_origin)
        
        # If it looks like an internal render hostname (no dots), add .onrender.com variant
        if "." not in origin:
            origins.append(f"https://{origin}.onrender.com")
    else:
        origins.append(origin)

# Add local development origins for safety
origins.extend([
    "http://localhost:5173", 
    "http://localhost:3000",
    "http://127.0.0.1:5173", 
    "http://127.0.0.1:3000"
])

print(f"Allowed CORS Origins: {origins}")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Audio Daily Manager Backend Running"}
