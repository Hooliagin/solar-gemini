from fastapi import FastAPI
import os
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import create_db_and_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run Migrations (Add missing columns if any)
    from migrations import run_migrations
    run_migrations()

    # Startup
    create_db_and_tables()
    
    # Initialize Scheduler
    from apscheduler.schedulers.background import BackgroundScheduler
    from services.scheduler import run_scheduler_checks
    
    scheduler = BackgroundScheduler()
    # Run every minute
    scheduler.add_job(run_scheduler_checks, 'interval', minutes=1)
    scheduler.start()
    
    print("App started. Scheduler running (Interval: 1 min).")
    
    yield
    
    # Shutdown
    scheduler.shutdown()
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
from routers import audio
app.include_router(audio.router)
from routers import debug
app.include_router(debug.router)
from routers import habits
app.include_router(habits.router)
from routers import admin
app.include_router(admin.router)
from routers import notion
app.include_router(notion.router)
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

@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    return {"status": "ok", "message": "Audio Daily Manager Backend Running"}
