from google import genai
from google.genai import types
from config import settings
import logging
import os
import base64

logger = logging.getLogger(__name__)

# Initialize Gemini Client
client = genai.Client(api_key=settings.GOOGLE_API_KEY)

# Map OpenAI voice IDs (frontend) to Gemini Voice Names
# We choose Gemini voices that match the "Vibe" of the original ID
VOICE_MAPPING = {
    "alloy": "Zephyr",   # Neutral -> Bright/Even
    "echo": "Fenrir",    # Warm -> Excitable (Good for News)
    "fable": "Puck",     # Storyteller -> Upbeat
    "onyx": "Kore",      # Deep -> Firm
    "nova": "Leda",      # Friendly -> Youthful
    "shimmer": "Aoede",  # Clear -> Breezy
    "default": "Zephyr"
}

def generate_speech(text: str, output_path: str, language: str = "de", voice_override: str = None):
    """
    Generates audio using Gemini 2.5 Flash Native TTS.
    Leverages the 32k token context window (no chunking needed usually).
    """
    try:
        # Determine Voice
        # If voice_override is a Gemini name (starts with capital usually), use it.
        # If it's an OpenAI id (lowercase), map it.
        if voice_override and voice_override in VOICE_MAPPING:
             gemini_voice = VOICE_MAPPING[voice_override]
        elif voice_override:
             gemini_voice = voice_override # Assume direct Gemini name if not in map
        else:
             gemini_voice = VOICE_MAPPING["default"]

        logger.info(f"TTS: Generating speech with Voice='{gemini_voice}' (mapped from '{voice_override}')")

        # Construct Director's Prompt for Podcast Style
        prompt = (
            "### AUDIO PROFILE: Dein Daily Host\n"
            "## THE SCENE: Ein gemütliches Podcast-Studio\n"
            "Der Sprecher sitzt entspannt vor dem Mikrofon und spricht direkt zu einem guten Freund.\n\n"
            "### DIRECTOR'S NOTES\n"
            "Style: Warm, persönlich, nahbar und locker (Conversational Podcast Style). "
            "Nicht abgelesen oder steif. Wie ein interessantes Gespräch. "
            "Nutze 'Du'-Ansprache. Variiere das Tempo für Spannung.\n"
            "CRITICAL INSTRUCTION: Generate ONLY the spoken voice. Do NOT add background music, sound effects, or silence at the end. STOP immediately after the text.\n"
            "Accent: Klares, natürliches Hochdeutsch.\n\n"
            "### TRANSCRIPT\n"
            f"{text}"
        )

        # Retry logic for TTS generation
        import time
        max_retries = 3
        response = None
        last_exception = None

        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash-preview-tts",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=gemini_voice,
                                )
                            )
                        ),
                    )
                )
                break # Success
            except Exception as e:
                last_exception = e
                error_str = str(e)
                # Check for 500 or 503 errors which are retriable
                if ("500" in error_str or "INTERNAL" in error_str or "503" in error_str) and attempt < max_retries - 1:
                    wait_time = 2 * (attempt + 1)
                    logger.warning(f"TTS API Error ({error_str}) on attempt {attempt+1}/{max_retries}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    # Non-retriable error or max retries reached
                    raise e
        
        if response is None and last_exception:
            raise last_exception

        # Extract Audio Data
        # Extract Audio Data
        # Response structure: candidates[0].content.parts[0].inline_data.data (already raw bytes in Python SDK)
        if not response.candidates or not response.candidates[0].content.parts:
            raise Exception("No audio content returned from Gemini API")
            
        # The Python SDK handles base64 decoding automatically for us. 
        # This is already raw PCM data (bytes).
        audio_bytes = response.candidates[0].content.parts[0].inline_data.data
        
        # Gemini returns raw PCM (24kHz, 1 channel, 16-bit usually).
        # We must package this as a WAV file so browsers accept it.
        # MP3 conversion requires ffmpeg which might be missing on Render.
        import wave
        
        try:
            with wave.open(output_path, "wb") as wav_file:
                wav_file.setnchannels(1)       # Mono
                wav_file.setsampwidth(2)       # 16-bit
                wav_file.setframerate(24000)   # 24kHz
                wav_file.writeframes(audio_bytes)
                
            logger.info(f"Audio saved to {output_path} (WAV format)")
        except Exception as e:
            logger.error(f"Failed to write WAV file: {e}")
            raise e
            
        return output_path

    except Exception as e:
        logger.error(f"TTS Error: {e}")
        print(f"DEBUG: TTS GENERATION FAILED: {e}", flush=True)
        # Cleanup if partial
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        raise e
