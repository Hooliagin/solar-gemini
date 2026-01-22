from openai import OpenAI
from config import settings
import logging

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Voice recommendations per language
# OpenAI voices: alloy, echo, fable, onyx, nova, shimmer
LANGUAGE_VOICES = {
    "de": "onyx",     # Deeper voice works well for German
    "en": "alloy",    # Default English voice
    "default": "alloy"
}

def generate_speech(text: str, output_path: str, language: str = "de", voice_override: str = None):
    """
    Generates audio from text using OpenAI TTS model.
    Selects voice based on language unless overridden.
    """
    try:
        # Select voice based on language or use override
        voice = voice_override if voice_override else LANGUAGE_VOICES.get(language, LANGUAGE_VOICES["default"])
        
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        
        response.stream_to_file(output_path)
        logger.info(f"Audio saved to {output_path} (voice: {voice}, lang: {language})")
        return output_path
        
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        raise e
