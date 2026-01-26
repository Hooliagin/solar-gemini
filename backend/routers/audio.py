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
        
        # Check if already exists to cache it implicitly (optional, but good for speed)
        # For now, we regenerate to allow easy testing of voice changes if params change
        # But actually, voice previews are static per voice_id + generic text.
        if not os.path.exists(preview_path):
            generate_speech(
                text=preview_text,
                output_path=preview_path,
                language="de",
                voice_override=voice_id
            )
            
        return FileResponse(preview_path, media_type="audio/mpeg")
        
    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate preview")
