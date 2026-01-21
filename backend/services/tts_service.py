from openai import OpenAI
from config import settings
import logging

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def generate_speech(text: str, output_path: str):
    """
    Generates audio from text using OpenAI TTS model.
    """
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        
        response.stream_to_file(output_path)
        logger.info(f"Audio saved to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        raise e
