from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from auth import get_current_user_id
from services.tts_service import generate_speech
from config import settings
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audio", tags=["audio"])

@router.get("/preview/{voice_id}")
def get_voice_preview(
    voice_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Generates a short preview audio for the selected voice.
    """
    try:
        # Define a short text for the preview
        preview_text = "Hallo! Dies ist eine kurze Vorschau meiner Stimme. Ich hoffe, ich gefalle dir."
        
        # Temp file for preview
        preview_filename = f"preview_{voice_id}.mp3"
        os.makedirs(settings.AUDIO_DIR, exist_ok=True)
        preview_path = os.path.join(settings.AUDIO_DIR, preview_filename)
        
        # Check if exists AND is not empty
        if os.path.exists(preview_path):
            if os.path.getsize(preview_path) == 0:
                 logger.warning(f"Preview file {preview_filename} was empty. Deleting.")
                 try:
                     os.remove(preview_path)
                 except: 
                     pass
        
        if not os.path.exists(preview_path):
            try:
                generate_speech(
                    text=preview_text,
                    output_path=preview_path,
                    language="de",
                    voice_override=voice_id
                )
            except Exception as e:
                logger.error(f"Failed to generate speech: {e}")
                # Ensure we don't return partial junk
                if os.path.exists(preview_path):
                     os.remove(preview_path)
                raise HTTPException(status_code=500, detail=str(e))
            
        # Verify size again
        if not os.path.exists(preview_path) or os.path.getsize(preview_path) == 0:
             raise HTTPException(status_code=500, detail="Generated audio file is empty")

        # Explicitly set headers to avoid "not suitable" error
        return FileResponse(
            preview_path, 
            media_type="audio/mpeg", 
            headers={"Accept-Ranges": "bytes"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate preview")
