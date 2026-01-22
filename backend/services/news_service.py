import google.generativeai as genai
from config import settings
import logging

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.GOOGLE_API_KEY)

def fetch_ai_news_summary(topics: list[str] = None):
    """
    Uses Gemini with Google Search Grounding to generate a summary of news.
    If topics are provided, it focuses on those. Otherwise, defaults to AI/Tech.
    """
    try:
        # Use a model that supports search grounding (Gemini 1.5 usually recommended)
        # We try to use the 'tools' for google search if the API key supports it.
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        search_query = "AI and Tech"
        if topics and len(topics) > 0:
            search_query = ", ".join(topics)
            
        prompt = (
            f"You are a news assistant. Search for the latest news and updates regarding: {search_query}. "
            "Provide a short, distinct, spoken-word style summary of 3 key stories found. "
            "Focus on what's new today/yesterday. "
            "Keep it brief (3-4 sentences per story) and interesting for a morning briefing."
        )
        
        # Enable Google Search tool
        tools = [{'google_search_retrieval': {
            'dynamic_retrieval_config': {
                'mode': 'dynamic',
                'dynamic_threshold': 0.3,
            }
        }}]
        
        try:
            response = model.generate_content(prompt, tools=tools)
            # Check if we got a valid text response
            if response.text:
                return response.text
        except Exception as tool_error:
            logger.warning(f"Gemini with Search Tool failed ({tool_error}), falling back to standard generation.")
            # Fallback to standard generation without specific tools if search fails (e.g. API tier)
            model_fallback = genai.GenerativeModel('gemini-2.0-flash')
            fallback_prompt = (
               f"You are a news assistant. Provide a short, bulleted summary of 3 key trends or concepts "
               f"related to: {search_query}. "
               "Since you might not have real-time web access, focus on general knowledge or recent major context you know."
            )
            response = model_fallback.generate_content(fallback_prompt)
            return response.text

    except Exception as e:
        logger.error(f"Gemini News Error: {e}")
        return "Could not fetch specific news updates at this time, but I hope you have a great day!"
