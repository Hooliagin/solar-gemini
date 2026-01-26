from openai import OpenAI
from config import settings
import logging
import os
from pydub import AudioSegment
import tempfile

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Voice recommendations per language
LANGUAGE_VOICES = {
    "de": "onyx",
    "en": "alloy",
    "default": "alloy"
}

MAX_TTS_LENGTH = 4000  # OpenAI limit is 4096, leave margin

def split_text_for_tts(text: str) -> list[str]:
    """
    Split long text into chunks suitable for TTS (max 4000 chars each).
    Tries to split at sentence boundaries for natural speech.
    """
    if len(text) <= MAX_TTS_LENGTH:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by sentences (periods, exclamation marks, question marks)
    sentences = []
    current_sentence = ""
    for char in text:
        current_sentence += char
        if char in '.!?' and len(current_sentence.strip()) > 0:
            sentences.append(current_sentence)
            current_sentence = ""
    if current_sentence.strip():
        sentences.append(current_sentence)
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= MAX_TTS_LENGTH:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # If single sentence is too long, split by words
            if len(sentence) > MAX_TTS_LENGTH:
                words = sentence.split()
                current_chunk = ""
                for word in words:
                    if len(current_chunk) + len(word) + 1 <= MAX_TTS_LENGTH:
                        current_chunk += word + " "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = word + " "
            else:
                current_chunk = sentence
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def generate_speech(text: str, output_path: str, language: str = "de", voice_override: str = None):
    """
    Generates audio from text using OpenAI TTS model.
    Handles long texts by splitting and concatenating audio chunks.
    """
    try:
        voice = voice_override if voice_override else LANGUAGE_VOICES.get(language, LANGUAGE_VOICES["default"])
        
        chunks = split_text_for_tts(text)
        logger.info(f"TTS: Processing {len(chunks)} chunk(s)")
        
        if len(chunks) == 1:
            # Single chunk, simple case
            response = client.audio.speech.create(
                model="tts-1-hd",
                voice=voice,
                input=chunks[0]
            )
            response.stream_to_file(output_path)
        else:
            # Multiple chunks - generate each and concatenate
            temp_files = []
            try:
                for i, chunk in enumerate(chunks):
                    temp_path = os.path.join(tempfile.gettempdir(), f"tts_chunk_{i}.mp3")
                    response = client.audio.speech.create(
                        model="tts-1",
                        voice=voice,
                        input=chunk
                    )
                    response.stream_to_file(temp_path)
                    temp_files.append(temp_path)
                    logger.info(f"TTS: Chunk {i+1}/{len(chunks)} generated")
                
                # Concatenate all chunks
                combined = AudioSegment.empty()
                for temp_file in temp_files:
                    audio_segment = AudioSegment.from_mp3(temp_file)
                    combined += audio_segment
                
                combined.export(output_path, format="mp3")
                
            finally:
                # Cleanup temp files
                for temp_file in temp_files:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
        
        logger.info(f"Audio saved to {output_path} (voice: {voice}, lang: {language}, chunks: {len(chunks)})")
        return output_path
        
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        raise e
