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
def trigger_morning_briefings(
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
    import sys
    print("=" * 50, flush=True)
    print("CRON ENDPOINT CALLED", flush=True)
    print("=" * 50, flush=True)
    
    # Verify API key
    expected_key = settings.CRON_API_KEY if hasattr(settings, 'CRON_API_KEY') else None
    
    print(f"API Key received: {x_api_key is not None}", flush=True)
    print(f"Expected key configured: {expected_key is not None}", flush=True)
    
    if not expected_key:
        print("ERROR: CRON_API_KEY not configured!", flush=True)
        raise HTTPException(
            status_code=500, 
            detail="CRON_API_KEY not configured on server"
        )
    
    if x_api_key != expected_key:
        print("ERROR: API key mismatch!", flush=True)
        logger.warning("Unauthorized cron request with invalid API key")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    print("Authentication successful!", flush=True)
    logger.info("Cron trigger received - running morning briefing job")
    
    try:
        print("About to call scheduled_briefing_job()...", flush=True)
        # Run the scheduler job synchronously
        scheduled_briefing_job()
        print("scheduled_briefing_job() completed!", flush=True)
        return {
            "status": "success",
            "message": "Morning briefing job completed"
        }
    except Exception as e:
        print(f"ERROR in scheduled_briefing_job: {e}", flush=True)
        import traceback
        traceback.print_exc()
        logger.error(f"Cron job failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Job failed: {str(e)}"
        )

@router.get("/health")
async def cron_health():
    """Health check endpoint for cron services."""
    return {"status": "ok", "message": "Cron service is healthy"}
