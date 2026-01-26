from google import genai
from google.genai import types
from config import settings
import logging

logger = logging.getLogger(__name__)
client = genai.Client(api_key=settings.GOOGLE_API_KEY)

def perform_research_grounding(query: str) -> str:
    """
    Uses Gemini with Google Search Grounding to find an answer to the user's query.
    Returns a concise summary.
    """
    try:
        logger.info(f"Researching: {query}")
        
        prompt = f"""
        Research this topic thoroughly and provide a concise, factual summary suitable for a morning briefing.
        Query: {query}
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_mime_type="text/plain"
            )
        )
        
        # Extract grounding metadata if needed, but for now we just want the text answer
        # The model will incorporate the search results into its response automatically.
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"Error during research: {e}")
        return "Unable to perform research at this time."
