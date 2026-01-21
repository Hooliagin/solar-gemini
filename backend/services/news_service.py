import google.generativeai as genai
from config import settings
import logging

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.GOOGLE_API_KEY)

def fetch_ai_news_summary():
    """
    Uses Gemini to generate a summary of recent AI news or general relevant topics.
    Since we don't have a direct 'Google Search' tool enabled in the library without configuration,
    we rely on the model's knowledge or grounding if available. 
    A better approach if grounding isn't available is to use a specific news API, 
    but for this prototype we'll ask Gemini what it knows or to simulate a briefing style.
    """
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        # We can prompt it to act as a news aggregator if it has access to fresh info (Gemini often does).
        # Or we use it to structure "What is generally important right now".
        # Note: Standard Gemini API might not have real-time web access enabled by default without "Tools".
        # For now, we simulate a "Tech Briefing" style generation.
        
        prompt = (
            "You are a news assistant. Provide a short, bulleted summary of 3 key hypothetical or real trends "
            "in Artificial Intelligence and Tech that a developer should know about today. "
            "Keep it brief and interesting."
        )
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini News Error: {e}")
        return "Could not fetch news updates at this time."
