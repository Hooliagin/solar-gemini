from fastapi import FastAPI
import os
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from services.scheduler import start_scheduler
from database import create_db_and_tables

# Global scheduler instance
scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_db_and_tables()
    global scheduler
    scheduler = start_scheduler()
    print("Scheduler started.")
    yield
    # Shutdown
    if scheduler:
        scheduler.shutdown()
    print("Scheduler shutdown.")

app = FastAPI(lifespan=lifespan, title="Audio Daily Manager")

from routers import entries
from routers import briefings

app.include_router(entries.router)
app.include_router(briefings.router)

# Parse origins and ensure they have a scheme (https://) if provided by Render
origins_raw = os.getenv("ALLOWED_ORIGINS", "*").split(",")
origins = []
for origin in origins_raw:
    origin = origin.strip()
    if origin == "*":
        origins.append("*")
    elif not origin.startswith("http"):
        origins.append(f"https://{origin}")
    else:
        origins.append(origin)

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
