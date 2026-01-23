"""
Cron endpoints for external scheduling services (e.g., cron-job.org)
These endpoints can be called by free cron services to trigger scheduled tasks.
"""
from fastapi import APIRouter, Header, HTTPException
from config import settings
from services.scheduler import scheduled_briefing_job
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cron", tags=["cron"])

@router.post("/morning-briefings")
async def trigger_morning_briefings(
    x_api_key: str = Header(None, alias="X-API-Key")
):
    """
    Endpoint to be called by external cron services (e.g., cron-job.org).
    Triggers the morning briefing generation for all eligible users.
    
    Requires X-API-Key header for authentication.
    Set CRON_API_KEY in environment variables.
    
    Example cron-job.org setup:
    - URL: https://your-app.onrender.com/cron/morning-briefings
    - Schedule: Every day at 07:00
    - Custom header: X-API-Key: your-secret-key
    """
    # Verify API key
    expected_key = settings.CRON_API_KEY if hasattr(settings, 'CRON_API_KEY') else None
    
    if not expected_key:
        raise HTTPException(
            status_code=500, 
            detail="CRON_API_KEY not configured on server"
        )
    
    if x_api_key != expected_key:
        logger.warning("Unauthorized cron request with invalid API key")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    logger.info("Cron trigger received - running morning briefing job")
    
    try:
        # Run the scheduler job synchronously
        scheduled_briefing_job()
        return {
            "status": "success",
            "message": "Morning briefing job completed"
        }
    except Exception as e:
        logger.error(f"Cron job failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Job failed: {str(e)}"
        )

@router.get("/health")
async def cron_health():
    """Health check endpoint for cron services."""
    return {"status": "ok", "message": "Cron service is healthy"}
