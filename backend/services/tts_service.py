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

        # Construct Director's Prompt
        # This is where the magic happens for the "German News Anchor" style.
        prompt = (
            "### DIRECTOR'S NOTES\n"
            "Style: Professional, energetic, and engaging German News Anchor. "
            "Confidence is high but approachable. Clear 'Hochdeutsch' pronunciation. "
            "No American accent.\n\n"
            "### TRANSCRIPT\n"
            f"{text}"
        )

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

        # Extract Audio Data
        # Response structure: candidates[0].content.parts[0].inline_data.data (base64 string)
        if not response.candidates or not response.candidates[0].content.parts:
            raise Exception("No audio content returned from Gemini API")
            
        audio_data_b64 = response.candidates[0].content.parts[0].inline_data.data
        audio_bytes = base64.b64decode(audio_data_b64)
        
        # Gemini returns raw PCM (24kHz, 1 channel, 16-bit usually).
        # We must convert this to MP3 for the browser/Telegram to understand it.
        try:
            audio_segment = AudioSegment(
                data=audio_bytes,
                sample_width=2,  # 16-bit
                frame_rate=24000, # 24kHz
                channels=1
            )
            audio_segment.export(output_path, format="mp3")
            logger.info(f"Audio converted and saved to {output_path}")
        except Exception as conversion_error:
            logger.error(f"Failed to convert PCM to MP3: {conversion_error}")
            # Fallback: Just save bytes (might be broken but better than crash)
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            
        return output_path

    except Exception as e:
        logger.error(f"TTS Error: {e}")
        # Cleanup if partial
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        raise e
